import json
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

SITE_URL = "https://www.infocileungsi.web.id/"
NEWS_FILE = Path("berita.json")
SITEMAP_FILE = Path("sitemap.xml")


def date_from_article(article):
    value = article.get("modifiedAt") or article.get("publishedAt")

    if not value:
        return datetime.now(timezone.utc).date().isoformat()

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        ).date().isoformat()
    except (TypeError, ValueError):
        return datetime.now(timezone.utc).date().isoformat()


def article_url(article):
    article_id = str(article.get("id", "")).strip()

    if not article_id:
        return None

    return f"{SITE_URL}?artikel={article_id}"


def url_entry(url, lastmod, changefreq, priority):
    return (
        "  <url>\n"
        f"    <loc>{escape(url)}</loc>\n"
        f"    <lastmod>{escape(lastmod)}</lastmod>\n"
        f"    <changefreq>{changefreq}</changefreq>\n"
        f"    <priority>{priority}</priority>\n"
        "  </url>"
    )


def main():
    with NEWS_FILE.open("r", encoding="utf-8") as file:
        articles = json.load(file)

    if not isinstance(articles, list):
        raise ValueError("berita.json harus berisi array JSON.")

    today = datetime.now(timezone.utc).date().isoformat()

    entries = [
        url_entry(
            SITE_URL,
            today,
            "daily",
            "1.0"
        )
    ]

    seen = set()

    for article in articles:
        if not isinstance(article, dict):
            continue

        url = article_url(article)

        if not url or url in seen:
            continue

        seen.add(url)

        entries.append(
            url_entry(
                url,
                date_from_article(article),
                "weekly",
                "0.8"
            )
        )

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += "\n".join(entries)
    xml += "\n</urlset>\n"

    SITEMAP_FILE.write_text(xml, encoding="utf-8")

    print(
        f"Sitemap diperbarui: {len(entries) - 1} artikel + homepage."
    )


if __name__ == "__main__":
    main()
