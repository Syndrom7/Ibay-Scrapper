import requests
import json
import sys
from config import HEADERS, BASE_URL

class CategoryScraper:
    def __init__(self, output_file):
        self.base_url = f"{BASE_URL}/index.php?page=cat_ajax&id="
        self.output_file = output_file

    def scrape_categories(self, category_id, level=0):
        url = self.base_url + str(category_id)
        response = requests.get(url, headers=HEADERS)
        categories = response.json()

        if not categories:
            return []

        category_list = []

        for category in categories:
            category_id, category_name = list(category.items())[0]
            print(f"{'  ' * level}{category_name} (ID: {category_id})")
            subcategories = self.scrape_categories(category_id, level + 1)
            category_dict = {
                "id": category_id,
                "name": category_name,
                "subcategories": subcategories
            }
            category_list.append(category_dict)

        return category_list

    def run(self):
        print("Starting to scrape categories...\n")
        try:
            categories = self.scrape_categories(0)
            with open(self.output_file, "w") as file:
                json.dump(categories, file, indent=2)
            print("Scraping complete! Categories saved to:", self.output_file)
        except Exception as e:
            print(f"An error occurred during scraping: {e}")
            sys.exit(1)