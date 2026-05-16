import requests
from bs4 import BeautifulSoup
import csv
import time
import re

START_LIMIT = "2021. 12. 01."
END_LIMIT = "2022. 04. 04. 23:59"
CSV_FILE = "24hu_articles.csv"

def get_articles_from_page(page_num):
    url = f"https://24.hu/belfold/page/{page_num}/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching page {page_num}: {e}")
        return None
        
    soup = BeautifulSoup(response.content, 'html.parser')
    articles = soup.find_all('article')
    parsed_articles = []
    
    for article in articles:
        if article.find_parent('aside'):
            continue
            
        title_tag = article.select_one('.m-articleWidget__title a, h3 a, h2 a')
        if not title_tag: continue
        title = title_tag.text.strip()
        link = title_tag.get('href', '')
        
        desc_tag = article.select_one('.m-articleWidget__lead, .m-articleWidget__catch')
        desc = desc_tag.text.strip() if desc_tag else ""
        
        date_tag = article.select_one('span.a-date, .m-author__date')
        date_str = date_tag.text.strip() if date_tag else ""
        
        if not date_str:
            continue
            
        category = "Belföld"
        parsed_articles.append({
            "title": title,
            "desc": desc,
            "date": date_str,
            "category": category,
            "link": link
        })
        
    return parsed_articles

def run_scraper():
    current_page = 2229
    total_saved = 0
    done = False
    
    with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Cím", "Leírás", "Dátum", "Kategória", "Link"])

        while not done:
            print(f"Fetching page {current_page}...")
            articles = get_articles_from_page(current_page)
            
            if articles is None:
                time.sleep(2)
                articles = get_articles_from_page(current_page)
                if articles is None:
                    print("Failed twice, continuing to next...")
                    current_page -= 1
                    continue
            
            if not articles:
                print("No articles found on page.")
                break
                
            all_too_new = True
            
            for art in articles:
                date_str = art['date']
                
                # Using simple string compare as 24.hu format is YYYY. MM. DD. hh:mm
                if date_str > END_LIMIT:
                    # It's too new, we skip but keep checking others
                    continue
                    
                if date_str < START_LIMIT:
                    # It's too old
                    continue
                    
                # If we reach here, it's within range
                all_too_new = False
                writer.writerow([
                    art['title'],
                    art['desc'],
                    art['date'],
                    art['category'],
                    art['link']
                ])
                total_saved += 1
                
            # If every article on this page is newer than the end limit,
            # we can safely stop because later pages will be even newer.
            if all_too_new and articles and articles[-1]['date'] > END_LIMIT:
                print(f"Reached page where all articles are past {END_LIMIT}. Stopping.")
                done = True
                break
                
            if not done:
                current_page -= 1
                time.sleep(1)
                
            if current_page <= 0:
                break

    print(f"Scraping completed. Saved {total_saved} articles.")

if __name__ == "__main__":
    run_scraper()
