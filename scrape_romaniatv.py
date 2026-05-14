import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import random
import re

POLITICAL_KEYWORDS = [
    "alegeri", "alegeri prezidențiale", "prezidențiale", "alegeri parlamentare", "parlamentare", 
    "campanie electorală", "campanie", "turul I", "turul al doilea", "primul tur", "al doilea tur", 
    "vot", "ziua votului", "urne", "secții de vot", "exit-poll", "sondaj", "candidat", "CCR", "BEC", "AEP",
    "Marcel Ciolacu", "Nicolae Ciucă", "Elena Lasconi", "George Simion", "Mircea Geoană", 
    "Călin Georgescu", "Kelemen Hunor", "USR", "PSD", "PNL", "AUR", "SOS România", "POT", 
    "guvern", "coaliție", "opoziție"
]

CATEGORIES = {
    "Politic": "https://www.romaniatv.net/politica",
    "Economie": "https://www.romaniatv.net/economie",
    "Actualitate": "https://www.romaniatv.net/actualitate",
    "Externe": "https://www.romaniatv.net/externe"
}

START_DATE = datetime(2024, 9, 1)
END_DATE = datetime(2024, 12, 6, 23, 59, 59)

def parse_date(date_str):
    if not date_str: return None
    try:
        clean_str = date_str[:10]
        if re.match(r'^\d{4}-\d{2}-\d{2}$', clean_str):
            return datetime.strptime(clean_str, '%Y-%m-%d')
    except Exception:
        pass
    return None

def text_contains_keywords(text, keywords):
    if not keywords or not text: return False
    text_lower = text.lower()
    for kw in keywords:
        if kw.lower() in text_lower:
            return True
    return False

def main():
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    
    # Increase this number for a full scrape
    PAGES_TO_SCRAPE = 50
    
    articles_data = []
    seen_urls = set()
    
    for cat_name, base_url in CATEGORIES.items():
        print(f"--- Scraping category: {cat_name} ---")
        for p in range(1, PAGES_TO_SCRAPE + 1):
            url = base_url if p == 1 else f"{base_url}/page/{p}"
            html = ""
            for attempt in range(3):
                try:
                    res = scraper.get(url, timeout=15)
                    if res.status_code == 200:
                        html = res.text
                        break
                    elif res.status_code == 404:
                        break
                except Exception:
                    pass
                time.sleep(random.uniform(2, 4))
                
            if not html:
                continue
                
            soup = BeautifulSoup(html, 'html.parser')
            articles = soup.find_all('article')
            
            if not articles:
                break
                
            for art in articles:
                link_tag = art.find('a')
                if not link_tag or 'href' not in link_tag.attrs:
                    continue
                href = link_tag['href']
                if not href.startswith('http'):
                    href = "https://www.romaniatv.net" + href
                    
                if href in seen_urls:
                    continue
                    
                title_tag = art.find('h2') or art.find('h3') or art.find(class_='title')
                title = title_tag.text.strip() if title_tag else ""
                
                # We fetch the article to get the exact date and full content for keyword search
                try:
                    art_res = scraper.get(href, timeout=10)
                    if art_res.status_code == 200:
                        art_soup = BeautifulSoup(art_res.text, 'html.parser')
                        
                        # Date
                        date_meta = art_soup.find('meta', property='article:published_time')
                        date_str = date_meta['content'] if date_meta else ""
                        parsed_dt = parse_date(date_str)
                        
                        if parsed_dt and START_DATE <= parsed_dt <= END_DATE:
                            # Content
                            content_div = art_soup.find(class_='article-content') or art_soup.find('div', class_='content')
                            full_text = content_div.text.strip() if content_div else ""
                            
                            desc_tag = art_soup.find('meta', attrs={'name': 'description'})
                            desc = desc_tag['content'] if desc_tag else ""
                            
                            combined_text = f"{title} {desc} {full_text}"
                            if text_contains_keywords(combined_text, POLITICAL_KEYWORDS):
                                seen_urls.add(href)
                                articles_data.append({
                                    "Cikk Neve": title,
                                    "Cikk Leírása": desc,
                                    "Cikk Kategória": cat_name,
                                    "Cikk Dátuma": parsed_dt.strftime("%Y-%m-%d"),
                                    "Cikk Linkje": href
                                })
                                print(f"  [MATCH] {title[:60]}...")
                except Exception:
                    pass
                
            time.sleep(random.uniform(1.5, 3))

    df = pd.DataFrame(articles_data)
    csv_path = "romaniatv_cikkek.csv"
    if df.empty:
        df = pd.DataFrame(columns=["Cikk Neve", "Cikk Leírása", "Cikk Kategória", "Cikk Dátuma", "Cikk Linkje"])
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"\nDone! Saved {len(df)} articles to {csv_path}")

if __name__ == "__main__":
    main()
