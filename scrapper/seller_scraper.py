import requests
from bs4 import BeautifulSoup
import json
import sys
import time
from config import HEADERS, BASE_URL, RED_COLOR, RESET_COLOR

class SellerScraper:
    def __init__(self, input_file, output_file):
        self.input_file = input_file
        self.output_file = output_file

    def extract_seller_info(self, seller_id):
        try:
            # Start time
            start_time = time.time()
            
            print("Fetching Seller id: " + str(seller_id))
            url = f"{BASE_URL}/index.php?page=profile&id={seller_id}"
            response = requests.get(url, headers=HEADERS)

            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extracting the seller's image
            image_element = soup.select_one('.bg-light .col.s6.l2 img[src]')
            image_src = image_element['src'] if image_element else None

            # Checking if the seller is premium
            is_premium_element = soup.select_one('.bg-light .col.s6.l4 img[alt="Premium Seller"]')
            is_premium = 1 if is_premium_element else 0

            # Extracting the seller description
            description_element = soup.select_one('.bg-light .col.s12.l6 p')
            seller_description = description_element.get_text() if description_element else None

            # Extracting the seller location
            location_element = soup.select_one('.bg-light .col.s12.l6 p b:nth-child(1)')
            seller_location = location_element.get_text() if location_element else None

            # Extracting the member since date
            member_since_element = soup.select_one('.bg-light .col.s12.l6 p b:nth-child(2)')
            member_since = member_since_element.get_text() if member_since_element else None

            # Extracting the last login date
            last_login_element = soup.select_one('.bg-light .col.s12.l6 p:nth-of-type(3) b')
            last_login = last_login_element.next_sibling.strip() if last_login_element else None
            
            # End time 
            time_difference = time.time() - start_time
            print(f'{RED_COLOR}Time Elapsed: %.2f seconds.{RESET_COLOR}' % time_difference)
            print("\n")

            return {
                "seller_id": seller_id,
                "image_src": "https://" + image_src,
                "isPremium": is_premium,
                "seller_description": seller_description,
                "seller_location": seller_location,
                "member_since": member_since,
                "last_login": last_login
            }
        except Exception as e:
            print(f"Error occurred while processing seller ID {seller_id}: {e}")
            sys.exit(1)

    def run(self):
        with open(self.input_file, 'r') as file:
            json_data = json.load(file)

        seller_info_list = []

        for item in json_data:
            seller_id = item['seller_id']
            seller_info = self.extract_seller_info(seller_id)
            if seller_info:
                seller_info_list.append(seller_info)

        with open(self.output_file, 'w') as file:
            json.dump(seller_info_list, file, indent=2)

        print("Seller information extracted and saved to " + self.output_file)

