from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import csv
from openai import OpenAI
import requests
import time 
from getpass import getpass
from dotenv import load_dotenv
import os


def extract_data(url, token):
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            page.goto(url, wait_until="networkidle", timeout=30000)
            
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')

            hrefs = soup.select('a[href^="/artikal/"]')  
            ids = []
            prices = []
            titles = []
            api_logs = []  # New list to track API calls

            for href in hrefs:
                article_id = href['href'].split('/artikal/')[1].split('/')[0]
                ids.append(article_id)

            headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {token}',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'application/json'
    }

            for article_id in ids:
                start_time = time.time()
                try:
                    response = requests.get(
                        f'https://api.olx.ba/listings/{article_id}',
                        headers=headers,
                        timeout=10  # Added timeout
                    )
                    
                    # Log API call details
                    call_log = {
                        'article_id': article_id,
                        'status_code': response.status_code,
                        'response_time': f"{(time.time() - start_time):.2f}s",
                        'url': f'https://api.olx.ba/listings/{article_id}',
                        'headers': headers,
                    }

                    if response.status_code == 200:
                        data = response.json()
                        prices.append(data['display_price'])
                        titles.append(data['title'])
                        call_log['success'] = True
                        call_log['data'] = {'price': data['display_price'], 'title': data['title']}
                    else:
                        print(f"API Error: Status {response.status_code} for ID {article_id}")
                        call_log['success'] = False
                        call_log['error'] = response.text

                except requests.exceptions.RequestException as e:
                    print(f"Request failed for ID {article_id}: {str(e)}")
                    call_log = {
                        'article_id': article_id,
                        'success': False,
                        'error': str(e)
                    }

                api_logs.append(call_log)

            return {
                'prices': prices,
                'titles': titles,
                'hrefs': [f"https://olx.ba{h['href']}" for h in hrefs],
                'no_results': len(prices) == 0,
                'api_logs': api_logs  # Include API logs in return
            }
        finally:
            browser.close()




def save_to_csv(items_dict, filename='results.csv'):
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['ID', 'Title', 'Price','URL'])  # Updated headers
        
        # Write rows from dictionary
        for item_id, item_data in items_dict.items():
            writer.writerow([
                item_id,
                item_data['title'],
                item_data['price'],
                item_data['url']  # Add URL to output
            ])
def scrape_all_pages(base_url,token, max_pages=10, ):
    all_titles = []
    all_prices = []
    all_hrefs = []
    page = 1

    while page <= max_pages:
        current_url = f"{base_url}&page={page}"
        print(f"Scraping page {page}...")
        
        results = extract_data(current_url, token)
        
        if results['no_results']:
            print("No more results found.")
            break
            
        all_titles.extend(results['titles'])
        all_prices.extend(results['prices'])
        all_hrefs.extend(results['hrefs'])
        
        if page == max_pages:
            print(f"Reached maximum page limit: {max_pages}")
            break
            
        page += 1
        
    return all_titles, all_prices, all_hrefs


# API TOKEN 

def get_api_key():
    # Load environment variables
    load_dotenv()
    
    # Try to get API key from environment
    api_key = os.getenv('OPEN_AI_API')
    
    # Check if API key exists and is not empty
    if not api_key or api_key.strip() == "":
        print("\nNo stored API key found.")
        response = input("Enter API key or press Enter to skip: ").strip()
        
        if response:
            save = input("Save API key for next time? (y/n): ").lower()
            if save == 'y':
                with open('.env', 'a') as f:
                    f.write(f'\nOPEN_AI_API={response}\n')
                print("API key saved!")
            return response
        return None
    
    print("Using stored API key")
    return api_key





def get_credentials():
    # Load environment variables
    load_dotenv()
    
    # Get credentials from environment
    username = os.getenv('OLX_USERNAME')
    password = os.getenv('OLX_PASSWORD')
    
    # Check if credentials exist and are not empty
    if not username or not password or username.strip() == "" or password.strip() == "":
        print("No stored credentials found. Please login to OLX:")
        username = input("Username (email): ")
        password = input("Password: ")
        
        # Ask if user wants to save credentials
        save = input("Save credentials for next time? (y/n): ").lower()
        if save == 'y':
            with open('.env', 'w') as f:
                f.write(f'OLX_USERNAME={username}\n')
                f.write(f'OLX_PASSWORD={password}\n')
            print("Credentials saved!")
    else:
        print("Using stored credentials")
    
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
            titles, prices,hrefs = scrape_all_pages(base_url,token, max_pages=max_pages, )
            
            print(f"Total items scraped: {len(titles)}")
            items_dict = {}
            for index, (title, price,href) in enumerate(zip(titles, prices,hrefs)):
                indexPlus = index+1
                items_dict[indexPlus] = {
                    'title': title,
                    'price': price,
                    'url' : href,
                    'ID':indexPlus,
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