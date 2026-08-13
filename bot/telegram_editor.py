import os
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from openai import AsyncOpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TELEGRAM_BOT_TOKEN = os.environ["EDITOR_TELEGRAM_BOT_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
ALLOWED_USER_ID = int(os.environ["ALLOWED_TELEGRAM_USER_ID"])

ai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

EDITOR_PROMPT = """
Anda adalah editor berita lokal untuk InfoCileungsi.web.

Berdasarkan bahan sumber, hasilkan draft artikel berita berbahasa Indonesia
yang orisinal untuk dikirim ke editor melalui Telegram.

Aturan:
- Gunakan sumber sebagai bahan riset, bukan teks yang diparafrasekan kalimat demi kalimat.
- Jangan menyalin judul, lead, heading, struktur paragraf, tabel, atau kalimat khas sumber.
- Buat tulisan baru dengan struktur, pembukaan, dan penutup sendiri.
- Pertahankan fakta penting: nama, tanggal, lokasi, angka, serta kutipan.
- Jangan menambahkan fakta, kutipan, angka, atau keterkaitan dengan Cileungsi yang tidak tersedia.
- Bila tidak ada hubungan nyata dengan Cileungsi, gunakan kategori Nasional atau Jawa Barat.
- Gunakan gaya berita netral, jelas, ringkas, dan mudah dipahami.
- Tulis sekitar 500–700 kata.
- Tambahkan bagian "FAKTA PERLU DICEK" jika ada klaim yang hanya berasal dari satu sumber
  atau tidak memiliki detail cukup.
- Cantumkan URL sumber pada bagian akhir.
- Hasil adalah DRAFT untuk editor, bukan artikel yang langsung diterbitkan.

Format:
JUDUL:
META DESCRIPTION:
KATEGORI:
SLUG:
ISI ARTIKEL:
FAKTA PERLU DICEK:
SUMBER:
"""

def allowed(update: Update) -> bool:
    return bool(
        update.effective_user
        and update.effective_user.id == ALLOWED_USER_ID
    )

def public_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()

    blocked_hosts = {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "::1",
    }

    return (
        parsed.scheme in {"http", "https"}
        and bool(host)
        and host not in blocked_hosts
        and not host.endswith(".local")
    )

async def get_article_text(url: str) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; InfoCileungsiEditorBot/1.0; "
            "+https://infocileungsi.web)"
        )
    }

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=20,
        headers=headers
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type:
            raise ValueError("URL bukan halaman artikel HTML.")

        html = response.text[:2_000_000]

    soup = BeautifulSoup(html, "html.parser")

    for element in soup([
        "script", "style", "noscript", "nav", "footer", "header",
        "aside", "form", "iframe", "svg"
    ]):
        element.decompose()

    content = soup.find("article") or soup.find("main") or soup.body

    if not content:
        raise ValueError("Isi artikel tidak ditemukan.")

    text = " ".join(content.get_text(" ", strip=True).split())

    if len(text) < 300:
        raise ValueError("Teks sumber terlalu pendek untuk diproses.")

    return text[:20_000]

def split_telegram_message(text: str, max_length: int = 3500) -> list[str]:
    result = []
    remaining = text.strip()

    while len(remaining) > max_length:
        cut = remaining.rfind("\n", 0, max_length)

        if cut < max_length // 2:
            cut = remaining.rfind(" ", 0, max_length)

        if cut < 1:
            cut = max_length

        result.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()

    if remaining:
        result.append(remaining)

    return result

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not allowed(update):
        return

    await update.message.reply_text(
        "Kirim perintah berikut:\n\n"
        "/olah https://url-artikel-sumber.com\n\n"
        "Bot akan mengirim draft artikel InfoCileungsi untuk Anda review."
    )

async def olah(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not allowed(update):
        return

    if not context.args:
        await update.message.reply_text(
            "Format:\n/olah https://url-artikel-sumber.com"
        )
        return

    source_url = context.args[0].strip()

    if not public_url(source_url):
        await update.message.reply_text("URL tidak valid atau tidak diizinkan.")
        return

    await update.message.reply_text(
        "Sedang membaca sumber dan menyusun draft artikel..."
    )

    try:
        source_text = await get_article_text(source_url)

        response = await ai_client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {
                    "role": "system",
                    "content": EDITOR_PROMPT
                },
                {
                    "role": "user",
                    "content": (
                        f"URL sumber: {source_url}\n\n"
                        f"Materi sumber:\n{source_text}"
                    )
                }
            ]
        )

        draft = response.output_text.strip()

        if not draft:
            raise ValueError("Draft tidak berhasil dibuat.")

        for message_part in split_telegram_message(draft):
            await update.message.reply_text(message_part)

    except Exception as error:
        await update.message.reply_text(
            f"Gagal memproses sumber: {str(error)[:250]}"
        )

def main() -> None:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("olah", olah))

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
