# scrapper/category_scrapper.py

import aiohttp
import os
import asyncio
import json
from models.category_model import CategoryModel

class CategoryScraper:
    
    def __init__(self):
        self.category_model = CategoryModel()
        self.base_url = f"{os.getenv('BASE_URL')}/index.php?page=cat_ajax&id="
        self.headers = {"User-Agent": os.getenv('USER_AGENT')}
        self.session = None
        
    async def init_session(self):
        """Initialize aiohttp session"""
        if self.session is None:
            self.session = aiohttp.ClientSession(headers=self.headers)
        return self.session
        
    async def scrape_categories(self, category_id, parent_id=None, level=0):
        """
        Recursively scrape categories using their ID, parent ID and level of depth
        
        Args:
            category_id (int): Category ID to scrape
            parent_id (int, optional): Parent category ID
            level (int, optional): Indentation level for pretty printing
        """
        session = await self.init_session()
        url = self.base_url + str(category_id)
        
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    print(f"Error fetching {url}: Status {response.status}")
                    return
                
                # Get response as text first
                text = await response.text()
                
                # Try to parse as JSON
                try:
                    categories = json.loads(text)
                except json.JSONDecodeError:
                    print(f"Error decoding JSON from {url}: Response is not valid JSON")
                    print(f"Content-Type: {response.headers.get('Content-Type')}")
                    print(f"First 100 chars of response: {text[:100]}...")
                    return
                
                if not categories:
                    return

                # Process each category in parallel
                tasks = []
                for category in categories:
                    category_id, category_name = list(category.items())[0]
                    print(f"{'  ' * level}{category_name} (ID: {category_id})")
                    await self.category_model.insert_category(category_id, category_name, parent_id)
                    # Create a task for each subcategory
                    task = asyncio.create_task(
                        self.scrape_categories(category_id, category_id, level + 1)
                    )
                    tasks.append(task)
                
                # Wait for all subcategory scraping tasks to complete
                if tasks:
                    await asyncio.gather(*tasks)
                    
        except aiohttp.ClientError as e:
            print(f"Error fetching {url}: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

    async def run(self):
        """Run the category scraper"""
        print("Starting to scrape categories...")
        await self.scrape_categories(0)
        print("Scraping complete! Categories saved to the database.")

    async def close(self):
        """Close connections and resources"""
        if self.session:
            await self.session.close()
        await self.category_model.close()