# scrapper/category_product_link_scrapper.py

import aiohttp
import os
import asyncio
from bs4 import BeautifulSoup
from models.category_model import CategoryModel
from models.product_model import ProductModel

class CategoryProductLinkScraper:
    def __init__(self):
        self.category_model = CategoryModel()
        self.product_model = ProductModel()
        self.base_url = os.getenv('BASE_URL')
        self.headers = {"User-Agent": os.getenv('USER_AGENT')}
        self.session = None
        self.semaphore = asyncio.Semaphore(10)  # Limit concurrent requests
        
    async def init_session(self):
        """Initialize aiohttp session"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(headers=self.headers, timeout=timeout)
        return self.session

    async def scrape_page(self, id, page_count):
        """
        Scrape a single page of product links
        
        Args:
            id (int): Category ID
            page_count (int): Page number
            
        Returns:
            tuple: Page number and list of product dictionaries or None if no products
        """
        session = await self.init_session()
        current_url = f"{self.base_url}?page=search&s_res=GO&lite=0&cid={id}&hw_num=100&off={page_count}"
        
        # Use semaphore to limit concurrent requests
        async with self.semaphore:
            try:
                async with session.get(current_url) as response:
                    if response.status != 200:
                        print(f"HTTP error {response.status} for {current_url}")
                        return (page_count, None)
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'lxml')
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
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                print(f"Request error: {e} for {current_url}")
            except Exception as e:
                print(f"Unexpected error: {e} for {current_url}")
            
            return (page_count, None)

    async def process_category(self, category):
        """
        Process all pages for a category
        
        Args:
            category (dict): Category information with id and name
        """
        id, name = category['id'], category['name']
        page_count = 0
        total_products = 0
        
        # Continue scraping pages until no more products are found
        while True:
            page, products = await self.scrape_page(id, page_count)
            
            if products is None:
                print(f"No more products found for Category ID: {id}, Name: {name}, Page: {page_count}. Ending scrape.")
                break
                
            await self.product_model.bulk_insert_products(products)
            total_products += len(products)
            print(f"Scraped {len(products)} products for Category ID: {id}, Name: {name}, Page: {page_count}")
            
            page_count += 1
            
            # Small delay to avoid overwhelming the server
            await asyncio.sleep(0.2)
            
        print(f"Completed scraping for Category ID: {id}, Name: {name}. Total products processed: {total_products}")

    async def run(self):
        """Run the category product link scraper"""
        print("Starting the scraping process...")
        parent_categories = await self.category_model.get_parent_categories()
        
        # Process categories in parallel but limit concurrency to avoid overwhelming the server
        tasks = []
        for category in parent_categories:
            task = asyncio.create_task(self.process_category(category))
            tasks.append(task)
            # Start 3 categories at a time
            if len(tasks) >= 3:
                await asyncio.gather(*tasks)
                tasks = []
                
        # Process any remaining categories
        if tasks:
            await asyncio.gather(*tasks)
            
        print("All parent categories processed. Scraping complete.")

    async def close(self):
        """Close connections and resources"""
        if self.session:
            await self.session.close()
        await self.category_model.close()
        await self.product_model.close()