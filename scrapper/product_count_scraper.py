# scrapper/product_count_scraper.py

import aiohttp
import os
import asyncio
import re
from bs4 import BeautifulSoup
from models.category_model import CategoryModel

class ProductCountScraper:
    def __init__(self):
        self.category_model = CategoryModel()
        self.base_url = os.getenv('BASE_URL')
        self.headers = {"User-Agent": os.getenv('USER_AGENT')}
        self.session = None
        self.semaphore = asyncio.Semaphore(20)  # Limit concurrent requests
        
    async def init_session(self):
        """Initialize aiohttp session"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(headers=self.headers, timeout=timeout)
        return self.session

    async def fetch(self, url):
        """
        Fetch a URL with rate limiting
        
        Args:
            url (str): URL to fetch
            
        Returns:
            str or None: HTML content or None if error
        """
        session = await self.init_session()
        
        # Use semaphore to limit concurrent requests
        async with self.semaphore:
            try:
                async with session.get(url) as response:
                    if response.status != 200:
                        print(f"Failed to retrieve {url}: Status {response.status}")
                        return None
                    return await response.text()
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                print(f"Failed to retrieve {url}: {e}")
                return None
            except Exception as e:
                print(f"Unexpected error fetching {url}: {e}")
                return None

    async def process_page(self, category):
        """
        Process a category page to extract product count
        
        Args:
            category (dict): Category information with id and name
        """
        id, name = category['id'], category['name']
        url = f"{self.base_url}/processor-b{id}_0.html"
        html = await self.fetch(url)
        
        if html:
            soup = BeautifulSoup(html, 'lxml')
            view_switch_element = soup.find('span', class_='view-switch', string=re.compile(r'\d+\s+listings'))
            
            if view_switch_element:
                numbers = int(''.join(re.findall(r'\d+', view_switch_element.text.replace(',', '')))) or 0
                await self.category_model.update_product_count(int(id), numbers)
                print(f"Processed ID {id} - {name}: Products found: {numbers}")
            else:
                print(f"No listings found for ID {id}, {name}.")

    async def run(self):
        """Run the product count scraper"""
        categories = await self.category_model.get_all_categories()
        
        # Create tasks for processing each category
        tasks = [self.process_page(category) for category in categories]
        
        # Run tasks in batches to avoid too many concurrent connections
        batch_size = 20
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            await asyncio.gather(*batch)

    async def close(self):
        """Close connections and resources"""
        if self.session:
            await self.session.close()
        await self.category_model.close()