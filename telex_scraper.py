import urllib.request
from bs4 import BeautifulSoup
import re
import csv
from datetime import datetime
import sys

start_page = 10385
end_date_str = "2022/04/03"
start_date_str = "2021/12/01"

def parse_date(date_string):
    try:
        return datetime.strptime(date_string, "%Y/%m/%d")
    except:
        return None

end_date = parse_date(end_date_str)
start_date = parse_date(start_date_str)

csv_filename = 'telex_articles.csv'

with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
    fieldnames = ['Title', 'Date', 'Description', 'Category', 'Link']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
    writer.writeheader()

    current_page = start_page
    stop_scraping = False
    
    while current_page > 0 and not stop_scraping:
        print(f"Scraping page {current_page}...", end='\r')
        url = f"https://telex.hu/archivum?oldal={current_page}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        try:
            with urllib.request.urlopen(req) as response:
                html = response.read().decode('utf-8')
                soup = BeautifulSoup(html, 'html.parser')
                
                articles = soup.find_all('div', class_=lambda x: x and 'list__item' in x)
                
                if not articles:
                    print(f"\nNo more articles found on page {current_page}, stopping.")
                    break
                
                page_oldest_date = None
                
                for art in articles:
                    title_elem = art.find('a', class_='list__item__title')
                    if not title_elem:
                        continue
                        
                    title = title_elem.text.strip()
                    href = title_elem.get('href', '')
                    
                    date_val = ""
                    match = re.search(r'/(\d{4}/\d{2}/\d{2})/', href)
                    if match:
                        date_val = match.group(1)
                    
                    if not date_val:
                        date_elem = art.find('div', class_='article_date')
                        if date_elem:
                            date_val = date_elem.text.strip()
                            
                    art_date = parse_date(date_val)
                    if not art_date:
                        continue
                        
                    page_oldest_date = art_date
                    
                    if art_date > end_date:
                        continue
                        
                    if art_date < start_date:
                        continue
                        
                    category = ""
                    cat_elem = art.find('a', class_='img_tag')
                    if cat_elem:
                        category = cat_elem.text.strip()
                    else:
                        cat_match = re.search(r'^/([^/]+)/', href)
                        if cat_match:
                            category = cat_match.group(1)
                            
                    if category.lower() == 'külföld':
                        continue
                        
                    desc_elem = art.find('div', class_=lambda x: x and 'list__item__lead' in x)
                    desc = desc_elem.text.strip() if desc_elem else ""
                    
                    link = f"https://telex.hu{href}" if href.startswith('/') else href
                    writer.writerow({
                        'Title': title,
                        'Date': date_val,
                        'Description': desc,
                        'Category': category,
                        'Link': link
                    })
                
                if page_oldest_date and page_oldest_date > end_date:
                    print(f"\nReached page where oldest article is {page_oldest_date.strftime('%Y/%m/%d')} > {end_date_str}. Stopping.")
                    stop_scraping = True
                    
        except Exception as e:
            print(f"\nError on page {current_page}: {e}")
            break
            
        current_page -= 1

print("\nScraping completed. File saved as telex_articles.csv")
