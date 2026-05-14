import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import random

def parse_date(date_str):
    if not date_str:
        return None
    try:
        # e.g., "2024-12-20 05:09:00"
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    return None

def main():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }
    
    tasks = [
        ("Educatie", "https://stirileprotv.ro/educatie/?page={}", 15, 16),
        ("Actualitate", "https://stirileprotv.ro/stiri/actualitate/?page={}", 301, 363),
        ("Politic", "https://stirileprotv.ro/stiri/politic/?page={}", 70, 76),
        ("Externe", "https://stirileprotv.ro/stiri/international/?page={}", 362, 428),
        ("Economie", "https://stirileprotv.ro/stiri/financiar/?page={}", 41, 46),
        ("Social", "https://stirileprotv.ro/stiri/social/?page={}", 22, 26)
    ]
    
    start_date = datetime(2024, 9, 1)
    end_date = datetime(2024, 12, 6, 23, 59, 59)
    
    urls_to_fetch = []
    for cat, url_template, start_p, end_p in tasks:
        # ensure min and max are correct
        if start_p > end_p:
            start_p, end_p = end_p, start_p
        for p in range(start_p, end_p + 1):
            urls_to_fetch.append((url_template.format(p), cat))
            
    print(f"Total pages to fetch: {len(urls_to_fetch)}")
    
    articles_data = []
    failed_urls = []
    
    for i, (url, cat) in enumerate(urls_to_fetch, 1):
        html = ""
        for attempt in range(3):
            try:
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code == 200:
                    html = response.text
                    break
                elif response.status_code == 404:
                    html = ""
                    break
            except Exception as e:
                pass
            time.sleep(random.uniform(1, 3))
            
        if not html:
            print(f"Failed to fetch {url}")
            failed_urls.append(url)
            time.sleep(2)
            continue
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # Check for sidebar elements and filter them out
        articles = soup.find_all('article')
        for art in articles:
            # Skip if in sidebar
            in_sidebar = art.find_parent(class_=lambda c: c and ('sidebar' in c.lower() or 'cele-mai-noi' in c.lower() or 'widget' in c.lower() or 'right-col' in c.lower() or 'right' in c.lower()))
            if in_sidebar:
                continue
                
            title_div = art.find(class_='article-title') or art.find('h3') or art.find('h2')
            title = title_div.text.strip() if title_div else ""
            if not title:
                continue
                
            link_tag = art.find('a')
            link = link_tag['href'] if link_tag and 'href' in link_tag.attrs else ""
            if link and not link.startswith('http'):
                link = "https://stirileprotv.ro" + link
                
            desc_div = art.find(class_='article-lead')
            desc = desc_div.text.strip() if desc_div else "N/A"
            
            date_div = art.find(class_='article-date')
            date_str = date_div['data-utc-date'] if date_div and 'data-utc-date' in date_div.attrs else ""
            
            parsed_dt = parse_date(date_str)
            
            if parsed_dt and start_date <= parsed_dt <= end_date:
                articles_data.append({
                    "cikk neve": title,
                    "cikk leírása": desc,
                    "cikk kategória": cat,
                    "cikk dátuma": parsed_dt.strftime("%Y-%m-%d"),
                    "cikk linkje": link
                })
                
        if i % 10 == 0:
            print(f"Processed {i}/{len(urls_to_fetch)} pages... found {len(articles_data)} articles so far.")
            
        time.sleep(random.uniform(0.5, 1.5))

    df = pd.DataFrame(articles_data)
    if not df.empty:
        df.drop_duplicates(subset=['cikk linkje'], inplace=True)
    
    csv_path = "protv_cikkek.csv"
    if df.empty:
        # Create empty csv with headers
        df = pd.DataFrame(columns=["cikk neve", "cikk leírása", "cikk kategória", "cikk dátuma", "cikk linkje"])
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"Done! Saved {len(df)} articles to {csv_path}")
    print(f"Failed URLs: {len(failed_urls)}")

if __name__ == "__main__":
    main()
