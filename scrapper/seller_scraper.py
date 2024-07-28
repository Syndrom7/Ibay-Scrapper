import requests
import os
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import sys
from models.seller_model import SellerModel 
from concurrent.futures import ThreadPoolExecutor, as_completed

class SellerScraper:
    def __init__(self):
        self.seller_model = SellerModel()
        self.base_url = os.getenv('BASE_URL')
        self.headers = {"User-Agent": os.getenv('USER_AGENT')}
        self.session = self._create_session()

    def _create_session(self):
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        session.headers.update(self.headers)
        return session
    
    def extract_seller_info(self, seller_id):
        try: 
            print(f"Fetching Seller id: {seller_id}")
            url = f"{self.base_url}/index.php?page=profile&id={seller_id}"
            response = self.session.get(url, timeout=10)

            if response.status_code != 200:
                print(f"Failed to fetch seller {seller_id}, status code: {response.status_code}")
                return None

            soup = BeautifulSoup(response.content, 'lxml')
            
            seller_info = {
                "id": seller_id,
                "image_src": "https://" + (soup.select_one('.bg-light .col.s6.l2 img[src]')['src'] if soup.select_one('.bg-light .col.s6.l2 img[src]') else ''),
                "is_premium": bool(soup.select_one('.bg-light .col.s6.l4 img[alt="Premium Seller"]')),
                "description": soup.select_one('.bg-light .col.s12.l6 p').get_text() if soup.select_one('.bg-light .col.s12.l6 p') else None,
                "location": soup.select_one('.bg-light .col.s12.l6 p b:nth-child(1)').get_text() if soup.select_one('.bg-light .col.s12.l6 p b:nth-child(1)') else None,
                "member_since": soup.select_one('.bg-light .col.s12.l6 p b:nth-child(2)').get_text() if soup.select_one('.bg-light .col.s12.l6 p b:nth-child(2)') else None,
                "last_login": soup.select_one('.bg-light .col.s12.l6 p:nth-of-type(3) b').next_sibling.strip() if soup.select_one('.bg-light .col.s12.l6 p:nth-of-type(3) b') else None
            }

            self.seller_model.update_seller(seller_info)
            return seller_info

        except requests.RequestException as e:
            print(f"Error occurred while processing seller ID {seller_id}: {e}")
            return None

    def run(self):
        seller_ids = self.seller_model.fetch_seller_ids()
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(self.extract_seller_info, sid) for sid in seller_ids]
            for future in as_completed(futures):
                future.result()

        print("Completed updating all sellers.")

    def close(self):
        self.seller_model.close()
        self.session.close()
