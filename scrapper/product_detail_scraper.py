import json
import os
import re
import time
import sys
from bs4 import BeautifulSoup
import requests
from config import HEADERS, BASE_URL, RED_COLOR, RESET_COLOR

class ProductDetailScraper:
    def __init__(self, input_folder, output_folder):
        self.input_folder = input_folder
        self.output_folder = output_folder

    def get_product_details(self, url, product_name):
        try:
            response = requests.get(url, headers=HEADERS, allow_redirects=False)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # If a product is not found or response code is 404, 301 then skip with values nullified
            product_name_element = soup.select_one('.iw-details-heading > h5')
            if not product_name_element or response.status_code == 301 or response.status_code == 404:
                print(f"Product name not found for {url}. Skipping...")
                print("\n")
                
                product_details = {
                    "product_name": product_name,
                    "product_price": None,
                    "product_images": [],
                    "product_location": None,
                    "product_condition": None,
                    "product_brand": None,
                    "product_info": [],
                    "product_description": None,
                    "product_url": url,
                    "favourite_count": None,
                    "seller_number": None,
                    "seller_url": None,
                    "seller_name": None,
                    "listing_id": int(re.search(r'-o(\d+)\.html', url).group(1)),
                    "last_updated": None
                }
                return product_details
        
            product_details = {}

            # Extract product name
            try:
                product_details['product_name'] = product_name_element.text.strip()
            except AttributeError:
                product_details['product_name'] = None
            
            # Extract product price
            try:
                product_details['product_price'] = soup.select_one('.details-page_product-info .price').text.strip()
            except AttributeError:
                product_details['product_price'] = None
            
            # Extract product images in an array
            try:
                product_details['product_images'] = [img['src'] for img in soup.select('#fullscreen-viewer img')]
            except AttributeError:
                product_details['product_images'] = []

            # Extract product infos, if product has location add it to product_location else add everything else to product_info 
            product_details['product_info'] = []
            item_info_table_rows = soup.select('.item-info-table > table > tbody > tr')
            for row in item_info_table_rows:
                header_element = row.select_one('td:nth-child(1)')
                value_element = row.select_one('td:nth-child(2)')
                if header_element is not None and value_element is not None:
                    header = header_element.text.strip()
                    value = value_element.text.strip()
                    if header == 'Location':
                        product_details['product_location'] = value
                    else:
                        # For any additional attributes in the table, add them to product_info array
                        product_details['product_info'].append({header: value})
                
                # Extract product description
                try:
                    product_details['product_description'] = soup.select_one('.iw-description-div').get_text()
                except AttributeError:
                    product_details['product_description'] = None

                product_details['product_url'] = url

                # Extract favourite count
                try:
                    product_details['favourite_count'] = soup.select_one('.no-favorites > span').text
                except AttributeError:
                    product_details['favourite_count'] = 0

                # Check if the seller number element exists
                try:
                    product_details['seller_number'] = soup.select_one('.i-detail-des-n').text
                except AttributeError:
                    product_details['seller_number'] = None

                # Check if the seller URL element exists
                try:
                    product_details['seller_url'] = f"{BASE_URL}/" + soup.select_one('.iw-user-name')['href']
                except AttributeError:
                    product_details['seller_url'] = None

                try:
                    product_details['seller_name'] = soup.select_one('.iw-user-name > b').text
                except AttributeError:
                    product_details['seller_name'] = None

                # Extract the listing ID from the URL
                try:
                    product_details['listing_id'] = int(re.search(r'-o(\d+)\.html', url).group(1))
                except AttributeError:
                    product_details['listing_id'] = None

                # Extract the last updated date from the page content
                last_updated_element = soup.find('div', string=re.compile('Last Updated : '))
                if last_updated_element:
                    last_updated_text = last_updated_element.text
                    last_updated_date = re.search(r'Last Updated : (\d{1,2}-[A-Za-z]{3}-\d{4})', last_updated_text)
                    if last_updated_date:
                        product_details['last_updated'] = last_updated_date.group(1)
                    else:
                        product_details['last_updated'] = None
                else:
                    product_details['last_updated'] = None
            return product_details

        except Exception as e:
            print(f"Error occurred while processing {url}: {e}")
            sys.exit(1)

    def run(self):
        start_time = time.time()
        os.makedirs(self.output_folder, exist_ok=True)
        input_files = [f for f in os.listdir(self.input_folder) if f.endswith('.json')]

        for input_file in input_files:
            input_file_path = os.path.join(self.input_folder, input_file)
            try:
                with open(input_file_path, 'r') as json_file:
                    data = json.load(json_file)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                print(f"Error while reading {input_file}: {e}")
                continue

            all_categories_data = []
            total_products = sum(len(category['products']) for category in data)

            current_category = 0
            current_product = 0

            for category in data:
                category_id = category['category_id']
                category_name = category['category_name']
                products = category['products']
                print(f"\nFetching details for Category ID: {category_id} - Category Name: {category_name}")

                category_data = {
                    "category_id": category_id,
                    "category_name": category_name,
                    "products": []
                }

                for product in products:
                    current_category += 1
                    current_product += 1

                    product_url = product['product_url']
                    product_name = product['product_name']
                    print(f"Fetching details for {product_url}")
                    product_fetch_time = time.time()
                    product_details = self.get_product_details(product_url, product_name)

                    if product_details:
                        category_data['products'].append(product_details)
                        print(f"\rProcessed Product {current_product}/{total_products} - Category {category_id}", end="")
                        product_fetch_time_diff = time.time() - product_fetch_time
                        print(f'{RED_COLOR} | Time Elapsed: %.2f seconds.{RESET_COLOR}' % product_fetch_time_diff)
                        print("\n")
                    else:
                        print(f"\rFailed to fetch details for Product {current_product}/{total_products} - Category {category_id}", end="")
                        print("\n")
                        sys.exit(1)

                all_categories_data.append(category_data)

            output_file_name = input_file.split('.')[0] + ".json"
            output_file_path = os.path.join(self.output_folder, output_file_name)

            with open(output_file_path, "w") as output_file:
                json.dump(all_categories_data, output_file, indent=4)

            os.remove(input_file_path)
            print(f"Deleted file: {input_file}")

            time_difference = time.time() - start_time
            print(f'{RED_COLOR}Category Scraping time: %.2f seconds.{RESET_COLOR}' % time_difference)
