import requests
import time
import os
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from models.category_model import CategoryModel
from models.product_model import ProductModel
from concurrent.futures import ThreadPoolExecutor, as_completed, wait

class CategoryProductLinkScraper:
    def __init__(self):
        self.category_model = CategoryModel()
        self.product_model = ProductModel()
        self.base_url = os.getenv('BASE_URL')
        self.headers = {"User-Agent": os.getenv('USER_AGENT')}
        self.max_workers = 5
        self.session = self._create_session()

    def _create_session(self):
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        session.headers.update(self.headers)
        return session

    def scrape_page(self, id, page_count):
        current_url = f"{self.base_url}?page=search&s_res=GO&lite=0&cid={id}&hw_num=100&off={page_count}"
        
        try: 
            response = self.session.get(current_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            product_items = soup.find_all(class_='bg-light latest-list-item')
            
            if not product_items:
                return (page_count, None)

            products = [
                {
                    'listing_id': int(item.find('div', class_='col m7 s8').h5.a['href'].split('-o')[-1].split('.html')[0]),
                    'name': item.find('div', class_='col m7 s8').h5.a.text.strip(),
                    'url': self.base_url + "/" + item.find('div', class_='col m7 s8').h5.a['href']
                }
                for item in product_items
            ]
            return (page_count, products)
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                print(f"Page not found for Category ID: {id}, Page: {page_count}")
            else:
                print(f"HTTP error {e.response.status_code} for {current_url}")
        except requests.RequestException as e:
            print(f"Request error: {e} for {current_url}")
        return (page_count, None)


    def process_products(self, category):
        id, name = category['id'], category['name']
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
                        print(f"No more products found for Category ID: {id}, Name: {name}, Page: {page}. Ending scrape.")
                        stop_page = page
                        break

                    self.product_model.bulk_insert_products(products)
                    total_products += len(products)
                    print(f"Scraped {len(products)} products for Category ID: {id}, Name: {name}, Page: {page}")

                    # Remove the completed future
                    del futures[page_count]

                # Launch new workers for the next pages
                for i in range(page_count, page_count + self.max_workers):
                    if i not in futures:
                        futures[i] = executor.submit(self.scrape_page, id, i)

                page_count += 1

        print(f"Completed scraping for Category ID: {id}, Name: {name}. Total products processed: {total_products}")

    def run(self):
        print("Starting the scraping process...")
        try:
            parent_categories = self.category_model.get_parent_categories()
            for category in parent_categories:
                self.process_products(category)
        finally:
            self.close()
        print("All parent categories processed. Scraping complete.")

    def close(self):
        self.category_model.close()
        self.product_model.close()
        self.session.close()