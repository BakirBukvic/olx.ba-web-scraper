from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import csv
def extract_data(url):
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            page.goto(url, wait_until="networkidle", timeout=30000)
            
            try:
                page.wait_for_selector('.price-wrap .smaller', timeout=10000)
            except:
                return {'prices': [], 'titles': [], 'no_results': True}
            
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            prices = soup.select('.price-wrap .smaller, .price-wrap span.smaller')
            titles = soup.select('.main-heading, article h1.main-heading')
            
            return {
                'prices': [p.text.strip() for p in prices],
                'titles': [t.text.strip() for t in titles],
                'no_results': len(prices) == 0
            }
        finally:
            browser.close()


            
def save_to_csv(titles, prices, filename='results.csv'):
    # Zip titles and prices together
    rows = list(zip(titles, prices))
    
    # Write to CSV
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Title', 'Price'])  # Headers
        writer.writerows(rows)

def scrape_all_pages(base_url, max_pages=10):
    all_titles = []
    all_prices = []
    page = 1

    while page <= max_pages:
        current_url = f"{base_url}&page={page}"
        print(f"Scraping page {page}...")
        
        results = extract_data(current_url)
        
        if results['no_results']:
            print("No more results found.")
            break
            
        all_titles.extend(results['titles'])
        all_prices.extend(results['prices'])
        
        if page == max_pages:
            print(f"Reached maximum page limit: {max_pages}")
            break
            
        page += 1
        
    return all_titles, all_prices

if __name__ == "__main__":
    base_url = "https://olx.ba/pretraga?q=golf+2"
    titles, prices = scrape_all_pages(base_url, max_pages=20)  # Increased max pages
    save_to_csv(titles, prices)
    print(f"Total items scraped: {len(titles)}")
    print(f"Data saved to results.csv")