import requests
import os
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import re
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from models.category_model import CategoryModel

class ProductCountScraper:
    def __init__(self):
        self.category_model = CategoryModel()
        self.base_url = os.getenv('BASE_URL')
        self.headers = { "User-Agent": os.getenv('USER_AGENT') }
        self.session = self.create_session()

    def create_session(self):
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        session.headers.update(self.headers)
        return session

    def fetch(self, url):
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Failed to retrieve {url}: {e}")
            return None

    def process_page(self, category):
        # Process a category page to extract product count
        id, name = category['id'], category['name']
        url = f"{self.base_url}/processor-b{id}_0.html"
        html = self.fetch(url)
        if html:
            soup = BeautifulSoup(html, 'lxml')
            view_switch_element = soup.find('span', class_='view-switch', string=re.compile(r'\d+\s+listings'))
            if view_switch_element:
                numbers = int(''.join(re.findall(r'\d+', view_switch_element.text.replace(',', '')))) or 0
                self.category_model.update_product_count(int(id), numbers)
                print(f"Processed ID {id} - {name}: Products found: {numbers}")
            else:
                print(f"No listings found for ID {id}, {name}.")

    def run(self):
        categories = self.category_model.get_all_categories()
        with ThreadPoolExecutor(max_workers=20) as executor:
            list(executor.map(self.process_page, categories))

    def close(self):
        self.category_model.close()
        self.session.close()