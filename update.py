
import json
import os
import datetime
import calendar
from concurrent.futures import ThreadPoolExecutor

import requests
import feedparser

SITES = {
    "LaLiiga": "https://www.laliiga.com",
    "Valioliiga": "https://www.valioliiga.com",
    "SuomiFutis": "https://www.suomifutis.com",
    "SuomiKiekko": "https://www.suomikiekko.com",
    "Leijonat": "https://www.leijonat.com",
    "NHLSuomi": "https://www.nhlsuomi.com",
    "SuomiKoris": "https://www.suomikoris.com",
    "SuomiUrheilu": "https://www.suomiurheilu.com",
    "Bundesliiga": "https://www.bundesliiga.com",
    "SuomiTennis": "https://www.suomitennis.com",
    "Huuhkajat": "https://www.huuhkajat.com",
    "Susijengi": "https://www.susijengi.com"
}

HEADERS = {
    "User-Agent": "Uutisvahti/2.0"
}


def fetch(site):
    name, base = site

    for suffix in ("/feed/", "/feed", "/rss/"):
        try:
            response = requests.get(
                base + suffix,
                headers=HEADERS,
                timeout=15
            )
            response.raise_for_status()

            feed = feedparser.parse(response.content)

            if not feed.entries:
                continue

            articles = []

            for entry in feed.entries:
                published = (
                    entry.get("published_parsed")
                    or entry.get("updated_parsed")
                )

                timestamp = (
                    calendar.timegm(published)
                    if published else 0
                )

                if entry.get("title") and entry.get("link"):
                    articles.append({
                        "site": name,
                        "title": entry.title,
                        "url": entry.link,
                        "timestamp": timestamp
                    })

            if articles:
                return name, articles, None

        except Exception:
            continue

    return name, [], "RSS-syötettä ei voitu lukea"


def main():
    old_articles = []

    if os.path.exists("news.json"):
        try:
            with open("news.json", encoding="utf-8") as file:
                old_articles = json.load(file).get("articles", [])
        except Exception:
            pass

    articles_by_url = {
        article["url"]: article
        for article in old_articles
        if article.get("url")
    }

    statuses = {}

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = pool.map(fetch, SITES.items())

        for name, articles, error in results:
            statuses[name] = {
                "ok": error is None,
                "fetched": len(articles),
                "error": error
            }

            for article in articles:
                articles_by_url[article["url"]] = article

    articles = sorted(
        articles_by_url.values(),
        key=lambda article: article.get("timestamp", 0),
        reverse=True
    )[:2500]

    result = {
        "updated": datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),
        "statuses": statuses,
        "articles": articles
    }

    with open("news.json", "w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)

    print("Artikkeleita:", len(articles))
    print("Lähteiden tila:", statuses)


if __name__ == "__main__":
    main()
