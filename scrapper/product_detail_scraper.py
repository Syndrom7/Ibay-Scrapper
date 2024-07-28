import re
import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from models.category_model import CategoryModel 
from models.product_model import ProductModel 
from models.seller_model import SellerModel 
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys

class ProductDetailScraper:
    def __init__(self):
        self.category_model = CategoryModel()
        self.product_model = ProductModel()
        self.seller_model = SellerModel()
        self.headers = {"User-Agent": os.getenv('USER_AGENT')}
        self.session = self.create_session()

    def create_session(self):
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        session.headers.update(self.headers)
        return session

    # Extract seller ID from the seller URL
    def extract_seller_id(self, seller_url):
        # Example URL: https://ibay.com.mv/index.php?page=profile&id=76650
        match = re.search(r'id=(\d+)', seller_url)
        return int(match.group(1)) if match else None
    
    # Product price extraction
    def extract_price(self, soup):
        product_price_element  = soup.select_one('.details-page_product-info .price')
        return float(re.sub(r'[^\d.]+', '', product_price_element.text.strip())) if product_price_element else None
    
    # Product description extraction
    def extract_description(self, soup):
        product_desc_element = soup.select_one('.iw-description-div')
        return product_desc_element.get_text().strip() if product_desc_element else None
    
    # Product images extraction
    def extract_product_images(self, soup):
        image_elements = soup.select('#fullscreen-viewer img')
        return [img['src'] for img in image_elements] if image_elements else []
    
    # Product last update extraction
    def extract_last_updated(self, soup):
        last_updated_element = soup.find('div', string=re.compile('Last Updated : '))
        if last_updated_element:
            last_updated_text = last_updated_element.text
            last_updated_date_match = re.search(r'Last Updated : (\d{1,2}-[A-Za-z]{3}-\d{4})', last_updated_text)
            return last_updated_date_match.group(1) if last_updated_date_match else None
        return None
    
    # Product info extraction
    def extract_product_info(self, soup):
        product_info = []
        location = None
        item_info_table_rows = soup.select('.item-info-table > table > tbody > tr')
        for row in item_info_table_rows:
            key_element = row.select_one('td:nth-child(1)')
            value_element = row.select_one('td:nth-child(2)')
            if key_element and value_element:
                key = key_element.text.strip()
                value = value_element.text.strip()
                if key == 'Location':
                    location = value
                else:
                    product_info.append({key: value})
        return product_info, location
    
    # Product categories extraction
    def extract_categories(self, soup):
        breadcrumb_elements = soup.select('div a.breadcrumb.dark[href*="b"]')
        return [int(match.group(1)) for element in breadcrumb_elements 
                if (match := re.search(r'b(\d+)', element['href']))]
    
    def get_product_details(self, product_id, product_name, url):
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code in [301, 404]:
                self.product_model.update_product_status(product_id, 'ERROR', response.status_code)
                return None

            soup = BeautifulSoup(response.content, 'lxml')

            # Check if the listing is disabled
            if soup.find('font', class_='pagetitle', text='Listing disabled') or soup.find('p', class_='pagetitle', text='Listing not found'):
                self.product_model.update_product_status(product_id, 'ERROR', 'Listing disabled or not found')
                print(f"Listing for {product_id} is not available. Skipping...")
                return None

            # Seller info extraction
            seller_url = soup.select_one('.iw-user-name')['href']
            seller_id = self.extract_seller_id(seller_url)
            seller_name = soup.select_one('.iw-user-name > b').text.strip() if soup.select_one('.iw-user-name > b') else None
            contact_number = soup.select_one('.i-detail-des-n').text.strip() if soup.select_one('.i-detail-des-n') else None

            seller_details = {
                'id': seller_id,
                'name': seller_name,
                'contact_number': contact_number
            }

            self.seller_model.insert_seller(seller_details)

            # Extract product details
            info, location = self.extract_product_info(soup)
            product_details = {
                'price': self.extract_price(soup),
                'description': self.extract_description(soup),
                'images': self.extract_product_images(soup),
                'product_info': info,
                'product_location': location,
                'last_updated': self.extract_last_updated(soup),
                'seller_id': seller_id
            }

            # Update product table with details
            self.product_model.update_product(product_id, product_details)

            # Insert product categories
            product_categories = self.extract_categories(soup)
            self.product_model.insert_product_categories(product_id, product_categories)

            # Insert product images
            self.product_model.insert_product_images(product_id, product_details['images'])

            # Insert product information key-value pairs
            self.product_model.insert_product_info_bulk(product_id, product_details['product_info'])

            # If all goes well, update the product status to 'SCRAPED'
            self.product_model.update_product_status(product_id, 'SCRAPED')

            print(f"Scraped: {product_name}")
            return product_details

        except Exception as e:
            print(f"Error occurred while processing {url}: {e}")
            self.product_model.update_product_status(product_id, 'ERROR', str(e))
            sys.exit(1)

    def run(self):
        products = self.product_model.get_products_by_status('NOT_SCRAPED')

        with ThreadPoolExecutor(max_workers=12) as executor:
            futures = [executor.submit(self.get_product_details, product[0], product[1], product[2]) for product in products]
            for future in futures:
                future.result()

    def close(self):
        self.category_model.close()
        self.product_model.close()
        self.seller_model.close()
