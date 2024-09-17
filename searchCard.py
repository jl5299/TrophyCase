import requests
from bs4 import BeautifulSoup
import json
import os
from urllib.parse import urljoin, quote_plus, urlencode
import re

def search_cards(query):
    base_url = "https://www.pricecharting.com/search-products"
    params = {
        "type": "prices",
        "q": query,
        "go": "Go"
    }
    url = f"{base_url}?{urlencode(params)}"
    print(f"Debug: Generated search URL: {url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.pricecharting.com/",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        results = soup.select('td.title a')
        
        if results:
            return [{'name': result.text.strip(), 'url': urljoin("https://www.pricecharting.com", result['href'])} for result in results[:5]]
        else:
            print("No results found.")
            return None
    
    except requests.exceptions.RequestException as e:
        print(f"Failed to retrieve search results: {e}")
        return None

def scrape_card_data(url):
    print(f"Debug: Scraping card data from URL: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        card_name = None
        name_candidates = [
            soup.find('h1', class_='product-title'),
            soup.select_one('h1[itemprop="name"]'),
            soup.find('h1'),
            soup.find('title')
        ]
        for candidate in name_candidates:
            if candidate:
                card_name = candidate.text.strip()
                break
        
        if not card_name:
            print("Debug: Could not find card name")
            card_name = "Unknown Card"
        else:
            print(f"Debug: Found card name: {card_name}")
        
        psa_prices = {}
        for grade in [8, 9, 10]:
            psa_row = soup.find('td', text=f'PSA {grade}')
            psa_prices[f'psa_{grade}'] = psa_row.find_next_sibling('td').text.strip() if psa_row else 'N/A'
            print(f"Debug: Found PSA {grade} price: {psa_prices[f'psa_{grade}']}")
        
        # Find image URLs
        image_urls = []
        classes = []
        for element in soup.find_all('img',class_=True):
            classes.extend(element["class"])
            print(element)
        print(classes)
        img_tags = soup.find_all('img', class_=['js-show-dialog'])
        for img in img_tags:
            src = img.get('src') or img.get('data-src')
            print(src)
            print("ll")
            if src:
                # Ensure the URL is absolute
                full_url = urljoin(url, src)
                # Remove any size parameters from the URL
                clean_url = re.sub(r'\?.*$', '', full_url)
                image_urls.append(clean_url)
        
        print(f"Debug: Found image URLs: {image_urls}")
        
        return {
            'name': card_name,
            'prices': psa_prices,
            'image_urls': image_urls
        }
    except requests.exceptions.RequestException as e:
        print(f"Failed to retrieve card data: {e}")
        return None

def download_images(urls, base_filename):
    if not os.path.exists('assets'):
        os.makedirs('assets')
    
    downloaded_files = []
    for i, url in enumerate(urls):
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            content_type = response.headers.get('content-type')
            if 'image' not in content_type:
                print(f"Warning: URL does not point to an image: {url}")
                continue
            
            file_extension = content_type.split('/')[-1]
            filename = f"assets/{base_filename}_{i+1}.{file_extension}"
            
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(8192):
                    f.write(chunk)
            
            print(f"Debug: Image successfully downloaded and saved as: {filename}")
            downloaded_files.append(filename)
        except requests.exceptions.RequestException as e:
            print(f"Failed to download image from {url}: {e}")
    
    return downloaded_files

def main():
    search_query = input("Enter the Pokemon card name to search: ")
    search_results = search_cards(search_query)
    
    if not search_results:
        print("No results found.")
        return

    for i, result in enumerate(search_results, 1):
        card_data = scrape_card_data(result['url'])
        if not card_data:
            print(f"Failed to retrieve card data for result {i}.")
            continue

        json_output = {
            'name': card_data['name'],
            'prices': card_data['prices']
        }

        print(f"\nCard details for result {i}:")
        print(json.dumps(json_output, indent=2))

        if i == 1:
            confirmation = input("Is this the correct card? (yes/no): ").lower()
            if confirmation == 'yes':
                base_filename = quote_plus(card_data['name'])
                downloaded_files = download_images(card_data['image_urls'], base_filename)
                if downloaded_files:
                    print("Images saved as:", ", ".join(downloaded_files))
                else:
                    print("Failed to download any images")
                json_output['image_files'] = downloaded_files
                print("Final JSON output:")
                print(json.dumps(json_output, indent=2))
                return
        
        if i == len(search_results):
            choice = input("Enter the number of the correct card (1-4), or 'none' if none are correct: ").lower()
            if choice == 'none':
                print("No correct card found. Exiting.")
                return
            elif choice.isdigit() and 1 <= int(choice) <= len(search_results):
                selected_card = search_results[int(choice) - 1]
                card_data = scrape_card_data(selected_card['url'])
                if card_data:
                    base_filename = quote_plus(card_data['name'])
                    downloaded_files = download_images(card_data['image_urls'], base_filename)
                    if downloaded_files:
                        print("Images saved as:", ", ".join(downloaded_files))
                    else:
                        print("Failed to download any images")
                    json_output = {
                        'name': card_data['name'],
                        'prices': card_data['prices'],
                        'image_files': downloaded_files
                    }
                    print("Final JSON output:")
                    print(json.dumps(json_output, indent=2))
                else:
                    print("Failed to retrieve data for the selected card.")
            else:
                print("Invalid choice. Exiting.")

if __name__ == "__main__":
    main()