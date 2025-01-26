from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import csv
from openai import OpenAI
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




def save_to_csv(items_dict, filename='results.csv'):
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['ID', 'Title', 'Price'])  # Updated headers
        
        # Write rows from dictionary
        for item_id, item_data in items_dict.items():
            writer.writerow([
                item_id,
                item_data['title'],
                item_data['price']
            ])

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

def get_api_key():
    print("\nDo you have an API key? (Optional)")
    response = input("Enter API key or press Enter to skip: ").strip()
    return response if response else None





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
    selected_category = next(cat['name'] for cat in categories if cat['id'] == category_id)
    
    # Return both URL and metadata
    return {
        'url': f"https://olx.ba/pretraga?attr=&attr_encoded=1&q={search_text.replace(' ', '+')}&category_id={category_id}",
        'category': selected_category,
        'search': search_text
    }
    


def remove_outliers_using_gpt(items, api_key, category, search):
    API_KEY = api_key
    
    # Format data for GPT
    sending_to_gpt = {
        item_id: {
            'ID': item_data['ID'],
            'Title': item_data['title']
        }
        for item_id, item_data in items.items()
    }

    # Construct prompt
    prompt = f"""
    Review these items and identify IDs of listings that don't match the search context.
    
    Category: {category}
    Search Term: {search}
    
    Items to review:
    {sending_to_gpt}
    
    Return only the IDs of items that don't fit the search context.
    For example, if searching for "golf 2" in Vehicles category, exclude parts listings and only keep actual cars.
    Another example: I searched for a phone, and the title is referencing to Phone chargers

    Return format: List of IDs only, comma separated
    """

    client = OpenAI(api_key=API_KEY)
    completion = client.chat.completions.create(
        model="gpt-4",
        messages=[{
            "role": "user",
            "content": prompt
        }]
    )
    
    # Print GPT's response for testing
    print("GPT Response:")
    response = completion.choices[0].message.content
    print(response)
    
    ids_to_remove = [int(id.strip()) for id in response.split(',') if id.strip().isdigit()]
    
    # Remove items with matching IDs
    filtered_items = {k: v for k, v in items.items() if k not in ids_to_remove}
    
    return filtered_items




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
            url_data = construct_url(categories) 
            base_url = url_data['url']
            
            # Get number of pages to scrape
            while True:
                try:
                    max_pages = int(input("\nHow many pages to scrape (default 10): ") or 10)
                    if max_pages > 0:
                        break
                    print("Please enter a positive number")
                except ValueError:
                    print("Please enter a valid number")



            api_key = get_api_key()

            input("\nPress Enter to start scraping...")
            print("\nStarting scrape...")
            
            # Scrape pages
            titles, prices = scrape_all_pages(base_url, max_pages=max_pages)
            
            print(f"Total items scraped: {len(titles)}")
            items_dict = {}
            for index, (title, price) in enumerate(zip(titles, prices)):
                indexPlus = index+1
                items_dict[indexPlus] = {
                    'title': title,
                    'price': price,
                    'ID':indexPlus
                }
           
             
            if api_key:

                items_dict = remove_outliers_using_gpt(
                items_dict,
                api_key,
                url_data['category'],
                url_data['search']
            )
            save_to_csv(items_dict)

    else:
        print("Login failed!")
        exit(1)