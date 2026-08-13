import json
import os
from pathlib import Path
from urllib.parse import quote_plus

import feedparser
import requests

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
STATE_FILE = Path("bot/sent_articles.json")
MAX_ALERTS_PER_RUN = 8

TOPICS = [
    ("📍 Cileungsi & Bogor", '"Cileungsi" OR "Gunung Putri" OR "Jonggol" OR "Klapanunggal" OR "Citeureup"'),
    ("🏠 Properti", '"rumah dijual Cileungsi" OR "rumah subsidi Cileungsi" OR "harga rumah Cileungsi"'),
    ("💼 Loker & usaha", '"loker Cileungsi" OR "lowongan kerja Bogor" OR "UMKM Bogor" OR "usaha rumahan"'),
    ("🤖 AI & teknologi", '"manfaat AI" OR "AI untuk UMKM" OR "AI untuk kerja"'),
    ("💡 Peluang digital", '"cara menghasilkan uang internet" OR "freelance Indonesia" OR "affiliate marketing Indonesia"'),
]


def load_sent():
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return set(data if isinstance(data, list) else [])
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_sent(sent):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(list(sent)[-600:], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def google_news_feed(query):
    url = "https://news.google.com/rss/search?q=" + quote_plus(query) + "&hl=id&gl=ID&ceid=ID:id"
    return feedparser.parse(url)


def clean(text):
    return " ".join((text or "").split())


def collect_articles(sent):
    found = []
    seen_now = set()

    for category, query in TOPICS:
        feed = google_news_feed(query)
        for entry in feed.entries[:10]:
            link = clean(entry.get("link"))
            title = clean(entry.get("title"))
            source = clean(entry.get("source", {}).get("title", "Sumber berita"))
            published = clean(entry.get("published", ""))

            if not link or not title or link in sent or link in seen_now:
                continue

            seen_now.add(link)
            found.append({
                "category": category,
                "title": title,
                "source": source,
                "published": published,
                "link": link,
            })

    return found[:MAX_ALERTS_PER_RUN]


def send_message(text):
    response = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": text,
            "disable_web_page_preview": True,
        },
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()
    print(f"Pesan Telegram berhasil dikirim. Message ID: {result['result']['message_id']}")


def main():
    sent = load_sent()
    articles = collect_articles(sent)
print(f"Jumlah artikel baru ditemukan: {len(articles)}")
    if not articles:
        send_message("✅ Info Cileungsi Monitor aktif. Tidak ada rekomendasi baru pada pengecekan ini.")
        return

    for article in articles:
        message = (
            f"{article['category']}\\n\\n"
            f"📰 {article['title']}\\n"
            f"Sumber: {article['source']}\\n"
            f"Waktu: {article['published'] or '-'}\\n\\n"
            f"🔗 {article['link']}\\n\\n"
            "Catatan: cek sumber dan tulis ulang dengan sudut pandang original sebelum dipublikasikan."
        )
        send_message(message)
        sent.add(article["link"])

    save_sent(sent)


if __name__ == "__main__":
    main()
