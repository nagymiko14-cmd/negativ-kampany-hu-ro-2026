import requests
import json
import csv
import time

def scrape_index_articles():
    url = "https://index.hu/api/json/"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    base_data = {
        "datum": "2026-03-22",
        "rovat": "24ora/",
        "url_params[ig]": "2022-04-04",
        "url_params[pepe]": "1",
        "url_params[rovat]": "belfold",
        "url_params[s]": "",
        "url_params[tol]": "2021-12-01",
        "url_params[alllowRovatChoose]": "0",
        "url_params[profil]": "",
        "url_params[cimke]": "",
        "url_params[word]": "1",
    }
    
    csv_file = "index_articles_2021_12_01_2022_04_04.csv"
    
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["Cím", "Leírás", "Dátum", "Link"])
        
        page = 0
        total_articles = 0
        
        while True:
            data = base_data.copy()
            data["url_params[p]"] = str(page)
            
            print(f"Fetching page {page}...")
            
            try:
                response = requests.post(url, data=data, headers=headers)
                if response.status_code != 200:
                    print(f"Error: Status code {response.status_code}")
                    break
                
                json_data = response.json()
                items = json_data.get('list', [])
                
                if not items:
                    print("No more items found.")
                    break
                    
                if isinstance(items, str):
                    # sometimes API might return HTML if params are wrong or page is out of bounds
                    print("Unexpected response format (HTML string instead of JSON list). Breaking.")
                    break
                
                for item in items:
                    title = item.get("cim", "").strip()
                    desc = item.get("ajanlo", "").strip()
                    date = item.get("datum", "").strip()
                    link = item.get("url", "").strip()
                    
                    writer.writerow([title, desc, date, link])
                    total_articles += 1
                
                page += 1
                # Small delay to avoid overloading the server
                time.sleep(0.5)
                
            except Exception as e:
                print(f"Exception occurred: {e}")
                break
                
        print(f"Scraping completed! Total articles saved: {total_articles}")

if __name__ == "__main__":
    scrape_index_articles()
