"""
444.hu cikk gyűjtő script
Összegyűjti a 444.hu cikkeit egy megadott időszakra,
kiszűri a külföldi cikkeket, és CSV-be menti.
"""

import urllib.parse
import urllib.request
import json
import csv
import time
import sys

# --- Beállítások ---
DATE_FROM = "2022-04-03T00:00:00.000Z"
DATE_TO = "2022-04-04T00:00:00.000Z"
OUTPUT_FILE = "444_cikkek.csv"
DELAY_BETWEEN_REQUESTS = 0.5  # másodperc várakozás kérések között

# Külföldi kategória slug-ok, amiket kiszűrünk
EXCLUDED_CATEGORY_SLUGS = {"kulfold"}

BASE_URL = "https://gateway.ipa.444.hu/api/graphql"
SHA256_HASH = "be3de27c86c3c998c0d220b4bbd548dc6a53cf77bb4e0df8963f4a5930119597"


def build_url(after_cursor=None):
    """Összeállítja a GraphQL API URL-t a megadott cursor-ral."""
    variables = {
        "buckets": {
            "column": "SLUG",
            "operator": "IN",
            "value": ["444"]
        },
        "categories": None,
        "tags": None,
        "partners": None,
        "authors": None,
        "date": {
            "column": "PUBLISHED_AT",
            "operator": "BETWEEN",
            "value": [DATE_FROM, DATE_TO]
        },
        "types": ["ARTICLE", "LIVE_ARTICLE"],
        "formats": None,
        "before": None,
        "after": after_cursor
    }

    extensions = {
        "persistedQuery": {
            "version": 1,
            "sha256Hash": SHA256_HASH
        }
    }

    params = {
        "operationName": "fetchContents",
        "variables": json.dumps(variables),
        "extensions": json.dumps(extensions)
    }

    return BASE_URL + "?" + urllib.parse.urlencode(params)


def fetch_page(after_cursor=None):
    """Lekér egy oldalnyi cikket az API-ból."""
    url = build_url(after_cursor)
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://444.hu/"
    })

    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))


def is_foreign(node):
    """Megvizsgálja, hogy a cikk külföldi kategóriájú-e."""
    categories = node.get("categories", [])
    for cat in categories:
        if isinstance(cat, dict) and cat.get("slug") in EXCLUDED_CATEGORY_SLUGS:
            return True
    return False


def extract_article(node):
    """Kinyeri a szükséges adatokat egy cikkből."""
    title = node.get("title", "").strip()
    published_at = node.get("publishedAt", "")
    excerpt = node.get("excerpt", "").strip()
    url = node.get("url", "")

    # Kategória nevek összegyűjtése
    categories = node.get("categories", [])
    cat_names = ", ".join(
        cat.get("name", "") for cat in categories if isinstance(cat, dict)
    )

    return {
        "cim": title,
        "datum": published_at,
        "leiras": excerpt,
        "kategoria": cat_names,
        "url": url
    }


def main():
    all_articles = []
    cursor = None
    page = 0

    print(f"444.hu cikkek gyűjtése: {DATE_FROM[:10]} - {DATE_TO[:10]}")
    print(f"Külföldi cikkek kiszűrése: {EXCLUDED_CATEGORY_SLUGS}")
    print("-" * 60)

    while True:
        page += 1
        try:
            data = fetch_page(cursor)
        except Exception as e:
            print(f"\n[HIBA] API kérés sikertelen (oldal {page}): {e}")
            print("Újrapróbálás 5 másodperc múlva...")
            time.sleep(5)
            try:
                data = fetch_page(cursor)
            except Exception as e2:
                print(f"[HIBA] Újrapróbálás is sikertelen: {e2}")
                break

        contents = data.get("data", {}).get("contents", {})
        edges = contents.get("edges", [])
        page_info = contents.get("pageInfo", {})

        if not edges:
            print(f"\nNincs több cikk (oldal {page}).")
            break

        # Cikkek feldolgozása
        page_count = 0
        skipped_foreign = 0
        for edge in edges:
            node = edge.get("node", {})
            if is_foreign(node):
                skipped_foreign += 1
                continue
            article = extract_article(node)
            all_articles.append(article)
            page_count += 1

        total = len(all_articles)
        first_date = edges[0]["node"].get("publishedAt", "")[:10] if edges else ""
        last_date = edges[-1]["node"].get("publishedAt", "")[:10] if edges else ""

        sys.stdout.write(
            f"\rOldal {page}: +{page_count} cikk (külföldi kiszűrve: {skipped_foreign}) | "
            f"Összesen: {total} | {first_date} - {last_date}"
        )
        sys.stdout.flush()

        # Van-e következő oldal?
        has_next = page_info.get("hasNextPage", False)
        if not has_next:
            print(f"\n\nMinden oldal feldolgozva.")
            break

        # Következő oldal cursor
        cursor = page_info.get("endCursor")
        if not cursor:
            print(f"\n\nNincs endCursor, leállás.")
            break

        time.sleep(DELAY_BETWEEN_REQUESTS)

    # CSV mentés
    print(f"\n{'=' * 60}")
    print(f"Összesen {len(all_articles)} cikk (külföldi nélkül)")
    print(f"Mentés: {OUTPUT_FILE}")

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["cim", "datum", "leiras", "kategoria", "url"],
                                delimiter=";", quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(all_articles)

    print(f"Kész! {OUTPUT_FILE} sikeresen mentve.")


if __name__ == "__main__":
    main()
