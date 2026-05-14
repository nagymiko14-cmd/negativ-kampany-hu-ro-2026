import asyncio
import aiohttp
from bs4 import BeautifulSoup
import csv
from datetime import datetime
import re
import sys

POLITICAL_KEYWORDS = [
    "alegeri", "alegeri prezidențiale", "prezidențiale", "alegeri parlamentare", "parlamentare", 
    "campanie electorală", "campanie", "turul I", "turul al doilea", "primul tur", "al doilea tur", 
    "vot", "ziua votului", "urne", "secții de vot", "exit-poll", "sondaj", "candidat", "CCR", "BEC", "AEP",
    "Marcel Ciolacu", "Nicolae Ciucă", "Elena Lasconi", "George Simion", "Mircea Geoană", 
    "Călin Georgescu", "Kelemen Hunor", "USR", "PSD", "PNL", "AUR", "SOS România", "POT", 
    "guvern", "coaliție", "opoziție"
]

CATEGORIES = {
    "Interne": {
        "url_base": "https://adevarul.ro/stiri-interne/?page={page}",
        "url_base_old": "https://adevarul.ro/stiri-interne/{page}.html",
        "start_page": 410, "end_page": 469,
        "keywords": "Cătălin Predoiu;Ministerul Afacerilor Interne;MAI;Poliția Română;Jandarmeria;IGPR;DSU;Raed Arafat;siguranță publică;ordine publică;trafic de droguri;clanuri interlope;infracționalitate;ședință de guvern;Palatul Victoria;Guvernul României;ordonanță de urgență;OUG;hotărâre de guvern;HG;Marcel Boloș;Ministerul Finanțelor;buget de stat;deficit bugetar;ANAF;Alina Gorghiu;Ministerul Justiției;magistrați;pensii speciale;salariul minim;asistență socială;administrație publică;primării;prefecturi;securitate națională;SRI;servicii secrete;stabilitate politică;motiune de cenzura;coaliție;opoziție;Marcel Ciolacu;Nicolae Ciucă".split(';')
    },
    "Externe": {
        "url_base": "https://adevarul.ro/stiri-externe/?page={page}",
        "url_base_old": "https://adevarul.ro/stiri-externe/{page}.html",
        "start_page": 620, "end_page": 716,
        "keywords": "Luminița Odobescu;Odobescu;ministrul de externe;ministrul Afacerilor Externe;MAE;Klaus Iohannis;Iohannis;vizită oficială;vizită de stat;întâlnire bilaterală;parteneri strategici;lideri europeni;Pedro Sánchez;Sanchez;premierul Spaniei;Schengen;Spațiul Schengen;aderarea la Schengen;frontiere terestre;Austria;Gerhard Karner;Karl Nehammer;veto;Consiliul JAI;Ucraina;războiul din Ucraina;Zelenski;Zelenskyy;Rusia;Putin;ajutor militar;sistemul Patriot;Patriot;donare Patriot;securitate la Marea Neagră;Marea Neagră;NATO;Mark Rutte;Rutte;flancul estic;baza Mihail Kogălniceanu;Republica Moldova;Maia Sandu;integrare europeană;referendum Moldova;Ursula von der Leyen;Comisia Europeană;Bruxelles;Vize SUA;Visa Waiver;ambasada SUA;parteneriat strategic".split(';')
    },
    "Economie": {
        "url_base": "https://adevarul.ro/economie/?page={page}",
        "url_base_old": "https://adevarul.ro/economie/{page}.html",
        "start_page": 139, "end_page": 170,
        "keywords": "Ștefan-Radu Oprea;Marcel Boloș;Claudiu Năsui;Iancu Guda;Adrian Negrescu;Cristian Păun;Mugur Isărescu;BNR;PIB;creștere economică;inflație;putere de cumpărare;deficit bugetar;măsuri fiscale;taxe și impozite;TVA;cotă unică;impozit progresiv;salariul minim;pensii;ajutoare sociale;investiții străine;PNRR;absorbție fonduri europene;băieții deștepți;clientelă politică;contracte cu statul;achiziții publice;energie;prețuri;scumpiri;datoria publică;rating de țară;fonduri de investiții;mediul de afaceri;IMM;antreprenori;evaziune fiscală;privatizare;ajutor de stat".split(';')
    }
}

START_DATE = datetime(2024, 9, 1)
END_DATE = datetime(2024, 12, 6)

def parse_date(date_str):
    if not date_str: return None
    try:
         clean_str = date_str[:10]
         if re.match(r'^\d{4}-\d{2}-\d{2}$', clean_str):
             return datetime.strptime(clean_str, '%Y-%m-%d')
    except: pass
    return None

def text_contains_keywords(title, intro, text, keywords):
    if not keywords: return False
    combined_lower = f"{title} {intro} {text}".lower()
    for kw in keywords:
         if kw.lower() in combined_lower:
             return True
    return False

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

output_data = []
seen_articles = set()

async def fetch_article(session, href, cat_name, info):
    try:
        async with session.get(href, timeout=15) as resp:
            if resp.status != 200: return
            content = await resp.read()
            art_soup = BeautifulSoup(content, 'html.parser')
            
            meta_date = art_soup.find('meta', property='article:published_time')
            d_str = meta_date['content'] if meta_date else ""
            if not d_str:
                time_tag = art_soup.find('time')
                d_str = time_tag.get('datetime') if time_tag else ""
                
            article_date = parse_date(d_str)
            if not article_date: return
                
            if START_DATE <= article_date <= END_DATE:
                h1 = art_soup.find('h1')
                title = h1.text.strip() if h1 else ""
                if not title: return

                intro_tag = art_soup.find('p', class_='lead') or art_soup.find('meta', attrs={'name': 'description'})
                intro = intro_tag.text.strip() if intro_tag and intro_tag.name == 'p' else (intro_tag['content'] if intro_tag else "")
                
                art_content = art_soup.find('div', class_=lambda c: c and ('article-body' in c.lower() or 'content' in c.lower()))
                full_text = art_content.text.strip() if art_content else ""
                
                combined_keywords = POLITICAL_KEYWORDS + info.get("keywords", [])
                
                if text_contains_keywords(title, intro, full_text, combined_keywords):
                    output_data.append([
                        title, intro, cat_name, article_date.strftime('%Y-%m-%d'), href
                    ])
                    print(f"    [MATCH] {cat_name}: {title[:60]}...", flush=True)
    except Exception as e:
        pass

async def process_page(session, page_url, cat_name, info, sem):
    async with sem:
        try:
            async with session.get(page_url, timeout=15) as resp:
                if resp.status != 200:
                    print(f"Failed page {page_url} with status {resp.status}", flush=True)
                    return
                content = await resp.read()
                soup = BeautifulSoup(content, 'html.parser')
                
                container = soup.find('div', class_='layout-container') # The main content is usually here
                if not container: container = soup
                
                news_links = container.find_all('a', href=lambda h: h and h.endswith('.html') and '-pagina-' not in h and not h.split('/')[-1].isdigit() and 'facebook.com' not in h)
                
                article_tasks = []
                for link_tag in news_links:
                    href = link_tag['href']
                    if href.startswith('/'): href = "https://adevarul.ro" + href
                    if href in seen_articles: continue
                    seen_articles.add(href)
                    
                    cat_slug = info["url_base_old"].split('adevarul.ro/')[1].split('/')[0]
                    if cat_slug not in href:
                        continue 
                        
                    article_tasks.append(fetch_article(session, href, cat_name, info))
                
                if article_tasks:
                    await asyncio.gather(*article_tasks)
        except Exception as e:
            print(f"Error on page {page_url}: {e}", flush=True)

async def main():
    print("Starting AIO Adevarul scrape...", flush=True)
    sem = asyncio.Semaphore(20) # 20 concurrent pages
    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = []
        for cat_name, info in CATEGORIES.items():
            start_p = info["start_page"]
            end_p = info["end_page"]
            for page in range(start_p, end_p + 1):
                page_url = info["url_base_old"].format(page=page)
                tasks.append(process_page(session, page_url, cat_name, info, sem))
        
        await asyncio.gather(*tasks)

    # Save to CSV
    csv_filename = "C:\\Users\\móni\\.gemini\\antigravity\\scratch\\adevarul_articles.csv"
    print(f"\nWriting {len(output_data)} articles to {csv_filename}...", flush=True)

    with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(["Cikk Neve", "Cikk Leírása", "Kategória", "Dátum", "Link"])
        writer.writerows(output_data)

    print("Finished Adevarul AIO!", flush=True)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
