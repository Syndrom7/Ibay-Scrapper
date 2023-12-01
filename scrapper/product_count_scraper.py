import re
import json
import requests
from bs4 import BeautifulSoup
from config import HEADERS, BASE_URL

class ProductCountScraper:
    def __init__(self, input_file, output_file):
        self.input_file = input_file
        self.output_file = output_file
        self.results = [] 

    def process_page(self, url, id, name):
        # Send a GET request to the URL
        response = requests.get(url, headers=HEADERS)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            view_switch_elements = soup.find_all(class_='view-switch')
            
            # Extract the numbers using regex and remove commas
            numbers = [int(num.replace(",", "")) for element in view_switch_elements for num in re.findall(r'\d{1,3}(?:,\d{3})*', element.text)]
            
            self.results.append({
                "id": int(id),
                "name": name,
                "product_count": numbers[0] if numbers else 0
            })
            print(f"Processed ID {id} - Products found: {numbers}")
        else:
            print(f"Failed to retrieve the page for ID {id}. Status code: {response.status_code}")


    def run(self):
        with open(self.input_file, "r") as json_file:
            data = json.load(json_file)

        for item in data:
            id = item["id"]
            name = item["name"]
            url = f"{BASE_URL}/processor-b{id}_0.html"
            self.process_page(url, id, name)

        with open(self.output_file, "w") as output_file:
            json.dump(self.results, output_file, indent=4)