import requests
from bs4 import BeautifulSoup
import json
from config import HEADERS, BASE_URL, GREEN_COLOR, RESET_COLOR

class CategoryProductLinkScraper:
    def __init__(self, input_file, output_file):
        self.input_file = input_file
        self.output_file = output_file


    def scrape_page(self, id, name):

        products_data = []
        page_count = 0
        while True:
            current_url = f"{BASE_URL}/other-b{id}_{page_count}.html"
            response = requests.get(current_url, headers=HEADERS)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                product_items = soup.find_all(class_='bg-light latest-list-item')

                if not product_items:
                    break

                for item in product_items:
                    product_name = item.find('div', class_='col m7 s8').h5.a.text.strip()
                    product_url = item.find('div', class_='col m7 s8').h5.a['href']
                    product_data = {
                        "product_name": product_name,
                        "product_url": self.base_url + product_url
                    }
                    products_data.append(product_data)
                    print(f"Fetching: {product_name}")

                page_count += 1
            else:
                print(f"Failed to retrieve the page for ID {id}. Status code: {response.status_code}")
                break

        return {
            "category_id": id,
            "category_name": name,
            "products": products_data
        }

    def run(self):
        with open(self.input_file, "r") as json_file:
            data = json.load(json_file)

        all_categories_data = []

        for item in data:
            id = item["id"]
            name = item["name"]
            print(f"{GREEN_COLOR}Category ID: {id} - Category Name: {name}{RESET_COLOR}")

            category_data = self.scrape_page(id, name)
            all_categories_data.append(category_data)

        with open(self.output_file, "w") as output_file:
            json.dump(all_categories_data, output_file, indent=4)
