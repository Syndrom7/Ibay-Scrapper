import requests
import os
from models.category_model import CategoryModel

class CategoryScraper:
    
    def __init__(self):
        self.category_model = CategoryModel()
        self.base_url = f"{os.getenv('BASE_URL')}/index.php?page=cat_ajax&id="
        self.headers = { "User-Agent": os.getenv('USER_AGENT') }

    # Recursively scrape categories using their ID, parent ID and level of depth
    def scrape_categories(self, category_id, parent_id=None, level=0):
        url = self.base_url + str(category_id)
        response = requests.get(url, headers=self.headers)
        categories = response.json()

        if not categories:
            return

        for category in categories:
            category_id, category_name = list(category.items())[0]
            print(f"{'  ' * level}{category_name} (ID: {category_id})")
            self.category_model.insert_category(category_id, category_name, parent_id)
            self.scrape_categories(category_id, category_id, level + 1) 

    def run(self):
        print("Starting to scrape categories...")
        self.scrape_categories(0)
        print("Scraping complete! Categories saved to the database.")

    def close(self):
        self.category_model.close()

