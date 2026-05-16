"""
Origo.hu article scraper
Collects articles from /kereses search results (2021-12-01 to 2022-04-03).
Outputs semicolon-separated CSV (Excel-friendly, UTF-8 BOM).

Article DOM structure (per page inspection):
  origo-article-card.article-card
    div.article-card-content
      div.tag-with-date
        a.article-card-tag  -> category (links to /cimke/...)
        span.article-card-publish-date -> date "2021. 12. 01."
      a.article-card-link -> actual article URL (/section/YYYY/MM/slug)
        h2 / span.article-card-title -> title
        span / p (lead) -> short description
"""

import asyncio
import csv
import re
from playwright.async_api import async_playwright

# ─── Config ───────────────────────────────────────────────────────────────────

OUTPUT_FILE = "origo_articles_2021_2022.csv"

BASE_URL = (
    "https://www.origo.hu/kereses"
    "?publishDate_order%5B%5D=asc"
    "&from_date=2021-12-01"
    "&to_date=2022-04-03"
)

# Article URL path segments that mean we should skip the article
EXCLUDED_SECTIONS = {
    "sport", "kulfold", "kulpol", "nagyvilag",
    "konyv", "utazas", "teve", "auto", "horoszkop",
    "elet-stilus", "ezoteria",
}

# Also skip if the title mentions these (belt-and-suspenders for sports etc.)
EXCLUDED_TITLE_KEYWORDS = []  # leave empty – rely on URL section instead

# ─── Helpers ──────────────────────────────────────────────────────────────────

DATE_RE = re.compile(r'\d{4}\.\s*\d{2}\.\s*\d{2}\.')

def section_from_href(href: str) -> str:
    """Extract the first path segment (section) from an article href."""
    return href.strip("/").split("/")[0].lower() if href else ""

def is_excluded(href: str) -> bool:
    return section_from_href(href) in EXCLUDED_SECTIONS

# ─── Per-page scraper ─────────────────────────────────────────────────────────

async def scrape_page(page, page_num: int) -> list[dict]:
    url = BASE_URL + (f"&page={page_num}" if page_num > 1 else "")
    print(f"[Page {page_num:4d}] fetching …", end=" ", flush=True)

    await page.goto(url, wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(1200)   # let Angular finish painting dates

    # Each search result is an <origo-article-card> custom element
    cards = await page.locator("origo-article-card").all()

    results = []
    for card in cards:
        try:
            # ── Date ────────────────────────────────────────────────────────
            date_el = card.locator("span.article-card-publish-date")
            if await date_el.count() == 0:
                continue                       # no date → sidebar card, skip
            date_str = (await date_el.first.inner_text()).strip()
            if not DATE_RE.search(date_str):
                continue                       # not a real date → skip

            # ── Category tag ────────────────────────────────────────────────
            tag_el = card.locator("a.article-card-tag")
            category = (await tag_el.first.inner_text()).strip() if await tag_el.count() > 0 else ""

            # ── Article link ─────────────────────────────────────────────────
            link_el = card.locator("a.article-card-link")
            if await link_el.count() == 0:
                continue
            href = (await link_el.first.get_attribute("href")) or ""
            full_link = f"https://www.origo.hu{href}" if href.startswith("/") else href

            # ── Section filter ───────────────────────────────────────────────
            if is_excluded(href):
                continue

            # ── Title ────────────────────────────────────────────────────────
            title = ""
            for sel in ["h2", "h3", ".article-card-title", "span.article-card-title"]:
                el = link_el.locator(sel)
                if await el.count() > 0:
                    title = (await el.first.inner_text()).strip()
                    if title:
                        break

            # ── Lead / short description ──────────────────────────────────────
            lead = ""
            for sel in [".article-card-lead", ".lead", "p"]:
                el = link_el.locator(sel)
                if await el.count() > 0:
                    lead = (await el.first.inner_text()).strip()
                    if lead:
                        break

            results.append({
                "Cikk neve":    title,
                "Dátum":        date_str,
                "Rövid leírás": lead,
                "Kategória":    category,
                "Cikk linkje":  full_link,
            })

        except Exception as exc:
            print(f"\n  ⚠ card error: {exc}")

    print(f"{len(results)} valid articles")
    return results

# ─── Main ─────────────────────────────────────────────────────────────────────

async def main():
    all_articles: list[dict] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        pg = await ctx.new_page()

        # ── Detect total pages ────────────────────────────────────────────
        print("Detecting total page count …")
        await pg.goto(BASE_URL, wait_until="networkidle", timeout=30000)
        await pg.wait_for_timeout(1200)

        max_page = 1
        for lnk in await pg.locator("a[href*='page=']").all():
            href = (await lnk.get_attribute("href")) or ""
            m = re.search(r"page=(\d+)", href)
            if m:
                n = int(m.group(1))
                if n > max_page:
                    max_page = n
        print(f"Total pages detected: {max_page}\n")

        # ── Scrape ───────────────────────────────────────────────────────
        for page_num in range(1, max_page + 1):
            articles = await scrape_page(pg, page_num)
            all_articles.extend(articles)
            if page_num % 50 == 0:
                print(f"  ── Progress: page {page_num}/{max_page}, "
                      f"articles so far: {len(all_articles)} ──")
            await pg.wait_for_timeout(700)   # polite delay

        await browser.close()

    print(f"\n✅  Done! Collected {len(all_articles)} articles.")

    # ── Write CSV ─────────────────────────────────────────────────────────
    FIELDS = ["Cikk neve", "Dátum", "Rövid leírás", "Kategória", "Cikk linkje"]
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, delimiter=";")
        writer.writeheader()
        writer.writerows(all_articles)
    print(f"📄  Saved → {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
