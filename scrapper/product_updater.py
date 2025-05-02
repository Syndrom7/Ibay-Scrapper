# scrapper/product_updater.py

import aiohttp
import os
import asyncio
from bs4 import BeautifulSoup
from models.product_model import ProductModel

class ProductUpdater:
    def __init__(self):
        self.product_model = ProductModel()
        self.headers = {"User-Agent": os.getenv('USER_AGENT')}
        self.base_url = os.getenv('BASE_URL', 'https://ibay.com.mv')
        self.session = None
        self.semaphore = asyncio.Semaphore(15)  # Limit concurrent requests to 15
        
    async def init_session(self):
        """Initialize aiohttp session"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(headers=self.headers, timeout=timeout)
        return self.session

    def _build_search_url(self, category_id, days, page):
        """
        Build the search URL based on parameters
        
        Args:
            category_id (int, optional): Category ID to filter by
            days (int, optional): Number of days to filter by
            page (int): Page number
            
        Returns:
            str: Search URL
        """
        url = f"{self.base_url}/index.php?page=search&s_res=GO&lite=0"
        if category_id:
            url += f"&cid={category_id}"
        if days:
            url += f"&hw_timeframe={days}"
        url += f"&hw_num=100&off={page}"
        return url

    async def scrape_page(self, url, page):
        """
        Scrape a single page of product links
        
        Args:
            url (str): URL to scrape
            page (int): Page number
            
        Returns:
            tuple: Page number and list of product dictionaries or None if no products
        """
        session = await self.init_session()
        
        # Use semaphore to limit concurrent requests
        async with self.semaphore:
            try:
                async with session.get(url, timeout=30) as response:
                    if response.status != 200:
                        print(f"HTTP error {response.status} for {url}")
                        return (page, None)
                    
                    content = await response.text()
                    soup = BeautifulSoup(content, 'lxml')
                    product_items = soup.find_all(class_='bg-light latest-list-item')
                    
                    if not product_items:
                        return (page, None)

                    products = [
                        {
                            'listing_id': int(item.find('div', class_='col m7 s8').h5.a['href'].split('-o')[-1].split('.html')[0]),
                            'name': item.find('div', class_='col m7 s8').h5.a.text.strip(),
                            'url': self.base_url + "/" + item.find('div', class_='col m7 s8').h5.a['href']
                        }
                        for item in product_items
                    ]
                    return (page, products)
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                print(f"Request error: {e} for {url}")
            except Exception as e:
                print(f"Unexpected error: {e} for {url}")
                
            return (page, None)

    async def process_products(self, category_id=None, days=None):
        """
        Process products based on category and days filter
        
        Args:
            category_id (int, optional): Category ID to filter by
            days (int, optional): Number of days to filter by
        """
        page_count = 0
        total_products = 0
        
        # Use a queue to manage page processing
        queue = asyncio.Queue()
        # Add the first page to the queue
        await queue.put(page_count)
        
        # List to keep track of active tasks
        tasks = []
        # Set to track pages in progress
        in_progress = set()
        # Flag to indicate when to stop processing
        stop_processing = False
        
        # Create worker tasks
        num_workers = 15
        for _ in range(num_workers):
            task = asyncio.create_task(self._worker(queue, category_id, days, in_progress))
            tasks.append(task)
        
        # Process pages until no more products are found
        while not stop_processing:
            # Wait for a result (page processed)
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            
            for task in done:
                page, products = task.result()
                in_progress.remove(page)
                
                if products is None:
                    # No products found on this page, stop processing
                    stop_processing = True
                    break
                    
                await self.product_model.bulk_insert_products(products)
                total_products += len(products)
                print(f"Scraped {len(products)} products for Category ID: {category_id}, Days: {days}, Page: {page}")
                
                # Add next page to the queue if we're still processing
                if not stop_processing:
                    page_count += 1
                    await queue.put(page_count)
                    
                # Create a new worker task to replace the completed one
                new_task = asyncio.create_task(self._worker(queue, category_id, days, in_progress))
                tasks.remove(task)
                tasks.append(new_task)
                
        # Cancel remaining tasks
        for task in tasks:
            task.cancel()
            
        print(f"Completed updating product links. Total products processed: {total_products}")

    async def _worker(self, queue, category_id, days, in_progress):
        """
        Worker function to process pages from the queue
        
        Args:
            queue (asyncio.Queue): Queue of pages to process
            category_id (int, optional): Category ID to filter by
            days (int, optional): Number of days to filter by
            in_progress (set): Set of pages currently being processed
            
        Returns:
            tuple: Page number and list of product dictionaries or None if no products
        """
        # Get a page from the queue
        page = await queue.get()
        in_progress.add(page)
        
        try:
            # Build the URL and scrape the page
            url = self._build_search_url(category_id, days, page)
            result = await self.scrape_page(url, page)
            return result
        finally:
            # Mark the task as done
            queue.task_done()

    async def run(self, category_id=None, days=None):
        """
        Run the product updater
        
        Args:
            category_id (int, optional): Category ID to filter by
            days (int, optional): Number of days to filter by
        """
        if category_id or days:
            await self.process_products(category_id, days)
        else:
            print("No Category ID or Days provided. Exiting.")

    async def close(self):
        """Close connections and resources"""
        if self.session:
            await self.session.close()
        await self.product_model.close()