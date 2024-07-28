import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed, wait
from models.product_model import ProductModel
import os

class ProductUpdater:
    def __init__(self):
        self.product_model = ProductModel()
        self.headers = {"User-Agent": os.getenv('USER_AGENT')}
        self.base_url = os.getenv('BASE_URL', 'https://ibay.com.mv')
        self.max_workers = 15
        self.session = self._create_session()

    def _create_session(self):
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        session.headers.update(self.headers)
        return session

    def _build_search_url(self, category_id, days, page):
        url = f"{self.base_url}/index.php?page=search&s_res=GO&lite=0"
        if category_id:
            url += f"&cid={category_id}"
        if days:
            url += f"&hw_timeframe={days}"
        url += f"&hw_num=100&off={page}"
        return url

    def scrape_page(self, url, page):
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'lxml')
            product_items = soup.find_all(class_='bg-light latest-list-item')
            
            if not product_items:
                return (page, None)

            products = [
                {
                    'listing_id': int(item.find('div', class_='col m7 s8').h5.a['href'].split('-o')[-1].split('.html')[0]),
                    'name': item.find('div', class_='col m7 s8').h5.a.text.strip(),
                    'url': self.base_url + "/" + item.find('div', class_='col m7 s8').h5.a['href']
                }
                for item in product_items
            ]
            return (page, products)
        except requests.HTTPError as e:
            print(f"HTTP error {e.response.status_code} for {url}")
        except requests.RequestException as e:
            print(f"Request error: {e} for {url}")
        return (page, None)

    def process_products(self, category_id=None, days=None):
        page_count = 0
        total_products = 0
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            stop_page = 0

            while stop_page == 0:
                if page_count in futures:
                    # Wait for the current page to complete
                    done, _ = wait([futures[page_count]], return_when="FIRST_COMPLETED")
                    future = done.pop()
                    page, products = future.result()

                    if products is None:
                        print(f"No products found for Category ID: {category_id}, Days: {days}, Page: {page}")
                        stop_page = page
                        break

                    self.product_model.bulk_insert_products(products)
                    total_products += len(products)
                    print(f"Scraped {len(products)} products for Category ID: {category_id}, Days: {days}, Page: {page}")

                    # Remove the completed future
                    del futures[page_count]

                
                for i in range(page_count, page_count + self.max_workers):
                    if i not in futures:
                        futures[i] = executor.submit(self.scrape_page, self._build_search_url(category_id, days, i), i)

                page_count += 1

        print(f"Completed updating product links. Total products processed: {total_products}")

    def run(self, category_id=None, days=None):
        if category_id or days:
            self.process_products(category_id, days)
        else:
            print("No Category ID or Days provided. Exiting.")

    def close(self):
        self.product_model.close()
        self.session.close()