from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import csv

import requests

from getpass import getpass

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


# API TOKEN 


def get_credentials():
    print("Please login to OLX:")
    username = input("Username (email): ")
    password = input("Password: ")
    return username, password

def login_to_olx(username, password, device_name="integration"):
    try:
        # API endpoint
        url = "https://api.olx.ba/auth/login"
        
        # Request payload
        data = {
            "username": username,
            "password": password,
            "device_name": device_name
        }
        
        # Add headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # Send POST request
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        
        # Parse response
        json_response = response.json()
        return json_response.get('token')
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            print("Access forbidden. Please check your credentials.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {str(e)}")
        return None
    
def get_categories(token):
    try:
        url = "https://api.olx.ba/categories"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 403:
            print(f"Authorization failed. Response: {response.text}")
            return None
            
        response.raise_for_status()
        
        categories = response.json().get('data', [])
        return [{
            'id': category['id'],
            'name': category['name']
        } for category in categories]
        
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch categories: {str(e)}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        return None



def display_categories_and_get_selection(categories):
    print("\nAvailable categories:")
    for category in categories:
        print(f"- {category['name']}")
    
    while True:
        selection = input("\nEnter category name: ")
        for category in categories:
            if selection.lower() in category['name'].lower():
                return category['id']
        print("Category not found. Please try again.")

def construct_url(categories):
    # Get search input
    search_text = input("Enter search text: ")
    
    # Get category selection
    category_id = display_categories_and_get_selection(categories)
    
    # Construct URL with parameters
    base = "https://olx.ba/pretraga"
    params = {
        'attr': '',
        'attr_encoded': '1',
        'q': search_text.replace(' ', '+'),
        'category_id': category_id
    }
    
    # Build URL string
    param_string = '&'.join(f"{k}={v}" for k, v in params.items())
    return f"{base}?{param_string}"



if __name__ == "__main__":
    # Get user credentials
    username, password = get_credentials()
    
    # Attempt login
    token = login_to_olx(username, password)

    if token:
        print("Successfully logged in!")
        # Fetch categories
        categories = get_categories(token)
        if categories:
            # Construct search URL based on user input
            base_url = construct_url(categories)
            
            # Get number of pages to scrape
            while True:
                try:
                    max_pages = int(input("\nHow many pages to scrape (default 10): ") or 10)
                    if max_pages > 0:
                        break
                    print("Please enter a positive number")
                except ValueError:
                    print("Please enter a valid number")

            input("\nPress Enter to start scraping...")
            print("\nStarting scrape...")
            
            # Scrape pages
            titles, prices = scrape_all_pages(base_url, max_pages=max_pages)
            save_to_csv(titles, prices)
            print(f"Total items scraped: {len(titles)}")
    else:
        print("Login failed!")
        exit(1)