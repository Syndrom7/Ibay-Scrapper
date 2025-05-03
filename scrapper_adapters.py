# scrapper_adapters.py
import asyncio
import sys
import io
from typing import Dict, List, Optional, Any, Callable
import logging
import time
import traceback

from api_models import ScraperType

# Import original scrapers
from scrapper.category_scrapper import CategoryScraper
from scrapper.product_count_scraper import ProductCountScraper
from scrapper.category_product_link_scrapper import CategoryProductLinkScraper
from scrapper.product_detail_scraper import ProductDetailScraper
from scrapper.seller_scraper import SellerScraper
from scrapper.product_updater import ProductUpdater
from scrapper.stale_product_updater import StaleProductUpdater

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseScraperAdapter:
    """Base adapter for all scrapers to handle logging and progress updates"""
    
    def __init__(self, task_logger=None, stop_event=None, pause_event=None, resume_event=None):
        self.task_logger = task_logger
        self.stop_event = stop_event or asyncio.Event()
        self.pause_event = pause_event or asyncio.Event()
        self.resume_event = resume_event or asyncio.Event()
        # Initially not paused, so resume is set
        if not resume_event:
            self.resume_event.set()
        self.scraper = None
        self.total_items = 0
        self.processed_items = 0
        
    async def log(self, message, level="INFO"):
        """Log a message to the task logger"""
        if self.task_logger:
            await self.task_logger.log(message, level)
        else:
            if level == "ERROR":
                logger.error(message)
            elif level == "WARNING":
                logger.warning(message)
            else:
                logger.info(message)
    
    async def update_progress(self, current, total, message=None):
        """Update progress percentage"""
        if total > 0:
            progress = (current / total) * 100
        else:
            progress = 0
        
        if self.task_logger:
            await self.task_logger.update_progress(progress, message)
    
    async def check_stop(self):
        """Check if the task should be stopped"""
        if self.stop_event.is_set():
            await self.log("Stop requested, shutting down...")
            return True
        return False
        
    async def check_pause(self):
        """Check if the task should be paused and wait for resume if needed"""
        if self.pause_event.is_set():
            # Check with the task logger to update status
            if self.task_logger and hasattr(self.task_logger, 'check_pause'):
                if await self.task_logger.check_pause():
                    # If stop was requested while paused, return True
                    return True
            else:
                await self.log("Task paused, waiting for resume...")
                
                # Wait for resume event
                await self.resume_event.wait()
                
                # If stop was requested while paused, return True
                if await self.check_stop():
                    return True
                    
                await self.log("Task resumed")
                
        return False
        
    async def pause_or_stop_check(self):
        """Check for both pause and stop conditions"""
        # First check for stop
        if await self.check_stop():
            return True
            
        # Then check for pause
        if await self.check_pause():
            return True
            
        return False
    
    async def run(self, **kwargs):
        """Run the scraper with parameters"""
        raise NotImplementedError("Subclasses must implement this method")
    
    async def close(self):
        """Close the scraper and release resources"""
        if self.scraper and hasattr(self.scraper, 'close'):
            try:
                await self.scraper.close()
            except Exception as e:
                logger.error(f"Error closing scraper: {e}")

class CategoryScraperAdapter(BaseScraperAdapter):
    """Adapter for the CategoryScraper"""
    
    async def run(self, **kwargs):
        await self.log("Initializing Category Scraper")
        self.scraper = CategoryScraper()
        
        # Monkey patch the original scrape_categories method to add progress tracking
        original_scrape_categories = self.scraper.scrape_categories
        
        async def patched_scrape_categories(category_id, parent_id=None, level=0):
            # Check if stop requested
            if await self.check_stop():
                return
                
            session = await self.scraper.init_session()
            url = self.scraper.base_url + str(category_id)
            
            try:
                async with session.get(url) as response:
                    if response.status != 200:
                        await self.log(f"Error fetching {url}: Status {response.status}")
                        return
                    
                    # Get response as text first
                    text = await response.text()
                    
                    # Try to parse as JSON
                    try:
                        import json
                        categories = json.loads(text)
                    except json.JSONDecodeError:
                        await self.log(f"Error decoding JSON from {url}")
                        await self.log(f"Content-Type: {response.headers.get('Content-Type')}")
                        await self.log(f"First 100 chars of response: {text[:100]}...")
                        return
                    
                    if not categories:
                        return

                    # Process each category in parallel
                    tasks = []
                    for category in categories:
                        category_id, category_name = list(category.items())[0]
                        await self.log(f"{'  ' * level}{category_name} (ID: {category_id})")
                        await self.scraper.category_model.insert_category(category_id, category_name, parent_id)
                        
                        # Increment processed items
                        self.processed_items += 1
                        await self.update_progress(
                            self.processed_items, 
                            self.total_items or 100,  # Use placeholder if total unknown
                            f"Processed category: {category_name}"
                        )
                        
                        # Check stop before creating new task
                        if await self.check_stop():
                            return
                            
                        # Create a task for each subcategory
                        task = asyncio.create_task(
                            patched_scrape_categories(category_id, category_id, level + 1)
                        )
                        tasks.append(task)
                    
                    # Wait for all subcategory scraping tasks to complete
                    if tasks:
                        await asyncio.gather(*tasks)
                        
            except Exception as e:
                await self.log(f"Error fetching {url}: {e}")
                
        # Replace the original method
        self.scraper.scrape_categories = patched_scrape_categories
        
        try:
            await self.log("Starting to scrape categories...")
            await self.scraper.scrape_categories(0)
            
            if not await self.check_stop():
                await self.log("Scraping complete! Categories saved to the database.")
                await self.update_progress(100, 100, "Categories scraping completed")
                
            return {"message": "Category scraping completed"}
        except Exception as e:
            error_details = traceback.format_exc()
            await self.log(f"Error in category scraper: {str(e)}")
            await self.log(f"Error details: {error_details}")
            raise
        finally:
            await self.close()

class ProductCountScraperAdapter(BaseScraperAdapter):
    """Adapter for the ProductCountScraper"""
    
    async def run(self, **kwargs):
        await self.log("Initializing Product Count Scraper")
        self.scraper = ProductCountScraper()
        
        try:
            # Get categories first to calculate total items
            categories = await self.scraper.category_model.get_all_categories()
            self.total_items = len(categories)
            await self.log(f"Found {self.total_items} categories to process")
            
            # Monkey patch the process_page method
            original_process_page = self.scraper.process_page
            
            async def patched_process_page(category):
                # Check if stop requested
                if await self.check_stop():
                    return
                    
                id, name = category['id'], category['name']
                url = f"{self.scraper.base_url}/processor-b{id}_0.html"
                html = await self.scraper.fetch(url)
                
                if html:
                    import re
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(html, 'lxml')
                    view_switch_element = soup.find('span', class_='view-switch', string=re.compile(r'\d+\s+listings'))
                    
                    if view_switch_element:
                        numbers = int(''.join(re.findall(r'\d+', view_switch_element.text.replace(',', '')))) or 0
                        await self.scraper.category_model.update_product_count(int(id), numbers)
                        await self.log(f"Processed ID {id} - {name}: Products found: {numbers}")
                    else:
                        await self.log(f"No listings found for ID {id}, {name}.")
                
                # Increment processed items and update progress
                self.processed_items += 1
                await self.update_progress(
                    self.processed_items, 
                    self.total_items,
                    f"Processed category {name} ({self.processed_items}/{self.total_items})"
                )
            
            # Replace the original method
            self.scraper.process_page = patched_process_page
            
            # Monkey patch the run method
            async def patched_run():
                categories = await self.scraper.category_model.get_all_categories()
                
                # Create tasks for processing each category
                tasks = []
                for category in categories:
                    # Check stop before adding more tasks
                    if await self.check_stop():
                        break
                        
                    tasks.append(self.scraper.process_page(category))
                
                # Run tasks in batches to avoid too many concurrent connections
                batch_size = 20
                for i in range(0, len(tasks), batch_size):
                    # Check stop before processing batch
                    if await self.check_stop():
                        break
                        
                    batch = tasks[i:i + batch_size]
                    await asyncio.gather(*batch)
            
            # Replace the original run method
            self.scraper.run = patched_run
            
            # Run the scraper
            await self.scraper.run()
            
            if not await self.check_stop():
                await self.log("Product count scraping completed!")
                await self.update_progress(100, 100, "Product count scraping completed")
                
            return {"message": "Product count scraping completed", "processed_items": self.processed_items}
        except Exception as e:
            error_details = traceback.format_exc()
            await self.log(f"Error in product count scraper: {str(e)}")
            await self.log(f"Error details: {error_details}")
            raise
        finally:
            await self.close()

class CategoryProductLinkScraperAdapter(BaseScraperAdapter):
    """Adapter for the CategoryProductLinkScraper"""
    
    async def run(self, **kwargs):
        await self.log("Initializing Category Product Link Scraper")
        self.scraper = CategoryProductLinkScraper()
        
        try:
            # Monkey patch the scrape_page method
            original_scrape_page = self.scraper.scrape_page
            
            async def patched_scrape_page(id, page_count):
                # Check if stop requested
                if await self.check_stop():
                    return (page_count, None)
                    
                result = await original_scrape_page(id, page_count)
                return result
            
            # Replace the original method
            self.scraper.scrape_page = patched_scrape_page
            
            # Monkey patch the process_category method
            original_process_category = self.scraper.process_category
            
            async def patched_process_category(category):
                id, name = category['id'], category['name']
                page_count = 0
                total_products = 0
                
                # Continue scraping pages until no more products are found
                while True:
                    # Check if stop requested before fetching next page
                    if await self.check_stop():
                        break
                        
                    page, products = await self.scraper.scrape_page(id, page_count)
                    
                    if products is None:
                        await self.log(f"No more products found for Category ID: {id}, Name: {name}, Page: {page_count}. Ending scrape.")
                        break
                        
                    await self.scraper.product_model.bulk_insert_products(products)
                    total_products += len(products)
                    await self.log(f"Scraped {len(products)} products for Category ID: {id}, Name: {name}, Page: {page_count}")
                    
                    page_count += 1
                    
                    # Update progress - using page count as a proxy for progress
                    await self.update_progress(
                        page_count, 
                        page_count + 5,  # Estimate a few more pages to avoid reaching 100% too early
                        f"Processing {name}: {total_products} products found"
                    )
                    
                    # Small delay to avoid overwhelming the server
                    await asyncio.sleep(0.2)
                    
                await self.log(f"Completed scraping for Category ID: {id}, Name: {name}. Total products processed: {total_products}")
                
                # Update total processed items
                self.processed_items += total_products
            
            # Replace the original method
            self.scraper.process_category = patched_process_category
            
            # Get parent categories
            parent_categories = await self.scraper.category_model.get_parent_categories()
            self.total_items = len(parent_categories)
            await self.log(f"Found {self.total_items} parent categories to process")
            
            # Process categories in parallel but limit concurrency
            tasks = []
            completed_categories = 0
            
            for category in parent_categories:
                # Check stop before adding more tasks
                if await self.check_stop():
                    break
                    
                task = asyncio.create_task(self.scraper.process_category(category))
                tasks.append(task)
                
                # Start 3 categories at a time
                if len(tasks) >= 3:
                    await asyncio.gather(*tasks)
                    tasks = []
                    
                    # Update progress based on completed categories
                    completed_categories += 3
                    await self.update_progress(
                        completed_categories, 
                        self.total_items,
                        f"Completed {completed_categories}/{self.total_items} categories"
                    )
                    
            # Process any remaining categories
            if tasks and not await self.check_stop():
                await asyncio.gather(*tasks)
                completed_categories += len(tasks)
                await self.update_progress(
                    completed_categories, 
                    self.total_items,
                    f"Completed {completed_categories}/{self.total_items} categories"
                )
                
            if not await self.check_stop():
                await self.log("All parent categories processed. Scraping complete.")
                await self.update_progress(100, 100, "Category product link scraping completed")
                
            return {
                "message": "Category product link scraping completed",
                "categories_processed": completed_categories,
                "total_products": self.processed_items
            }
        except Exception as e:
            error_details = traceback.format_exc()
            await self.log(f"Error in category product link scraper: {str(e)}")
            await self.log(f"Error details: {error_details}")
            raise
        finally:
            await self.close()

class ProductDetailScraperAdapter(BaseScraperAdapter):
    """Adapter for the ProductDetailScraper"""
    
    async def run(self, **kwargs):
        await self.log("Initializing Product Detail Scraper")
        self.scraper = ProductDetailScraper()
        
        try:
            # Get products to process
            products = await self.scraper.product_model.get_products_by_status('NOT_SCRAPED')
            self.total_items = len(products)
            await self.log(f"Found {self.total_items} products to process")
            
            if self.total_items == 0:
                await self.log("No products found with status 'NOT_SCRAPED'")
                await self.update_progress(100, 100, "No products to process")
                return {"message": "No products to process"}
            
            # Monkey patch the get_product_details method
            original_get_product_details = self.scraper.get_product_details
            
            async def patched_get_product_details(product_id, product_name, url):
                # Check if stop requested
                if await self.check_stop():
                    return None
                    
                result = await original_get_product_details(product_id, product_name, url)
                
                # Increment processed items and update progress
                self.processed_items += 1
                await self.update_progress(
                    self.processed_items, 
                    self.total_items,
                    f"Processed product: {product_name} ({self.processed_items}/{self.total_items})"
                )
                
                return result
            
            # Replace the original method
            self.scraper.get_product_details = patched_get_product_details
            
            # Process products in batches
            batch_size = 20
            for i in range(0, len(products), batch_size):
                # Check stop before processing batch
                if await self.check_stop():
                    break
                    
                batch = products[i:i + batch_size]
                tasks = [
                    self.scraper.get_product_details(product[0], product[1], product[2]) 
                    for product in batch
                ]
                
                await self.log(f"Processing batch {i//batch_size + 1}/{(len(products) + batch_size - 1)//batch_size}")
                await asyncio.gather(*tasks)
                
                # Small delay between batches
                await asyncio.sleep(1)
            
            if not await self.check_stop():
                await self.log("Product detail scraping completed!")
                await self.update_progress(100, 100, "Product detail scraping completed")
                
            return {
                "message": "Product detail scraping completed",
                "products_processed": self.processed_items,
                "total_products": self.total_items
            }
        except Exception as e:
            error_details = traceback.format_exc()
            await self.log(f"Error in product detail scraper: {str(e)}")
            await self.log(f"Error details: {error_details}")
            raise
        finally:
            await self.close()

class SellerScraperAdapter(BaseScraperAdapter):
    """Adapter for the SellerScraper"""
    
    async def run(self, **kwargs):
        await self.log("Initializing Seller Scraper")
        self.scraper = SellerScraper()
        
        try:
            # Get seller IDs to process
            seller_ids = await self.scraper.seller_model.fetch_seller_ids()
            self.total_items = len(seller_ids)
            await self.log(f"Found {self.total_items} sellers to process")
            
            if self.total_items == 0:
                await self.log("No sellers found to process")
                await self.update_progress(100, 100, "No sellers to process")
                return {"message": "No sellers to process"}
            
            # Monkey patch the extract_seller_info method
            original_extract_seller_info = self.scraper.extract_seller_info
            
            async def patched_extract_seller_info(seller_id):
                # Check if stop requested
                if await self.check_stop():
                    return None
                    
                await self.log(f"Fetching Seller id: {seller_id}")
                result = await original_extract_seller_info(seller_id)
                
                # Increment processed items and update progress
                self.processed_items += 1
                await self.update_progress(
                    self.processed_items, 
                    self.total_items,
                    f"Processed seller: {seller_id} ({self.processed_items}/{self.total_items})"
                )
                
                return result
            
            # Replace the original method
            self.scraper.extract_seller_info = patched_extract_seller_info
            
            # Process sellers in batches
            batch_size = 100
            for i in range(0, len(seller_ids), batch_size):
                # Check stop before processing batch
                if await self.check_stop():
                    break
                    
                batch = seller_ids[i:i + batch_size]
                tasks = [self.scraper.extract_seller_info(sid) for sid in batch]
                
                await self.log(f"Processing batch {i//batch_size + 1}/{(len(seller_ids) + batch_size - 1)//batch_size}")
                await asyncio.gather(*tasks)
                
                # Small delay between batches
                await asyncio.sleep(1)
            
            if not await self.check_stop():
                await self.log("Completed updating all sellers.")
                await self.update_progress(100, 100, "Seller scraping completed")
                
            return {
                "message": "Seller scraping completed",
                "sellers_processed": self.processed_items,
                "total_sellers": self.total_items
            }
        except Exception as e:
            error_details = traceback.format_exc()
            await self.log(f"Error in seller scraper: {str(e)}")
            await self.log(f"Error details: {error_details}")
            raise
        finally:
            await self.close()

class ProductUpdaterAdapter(BaseScraperAdapter):
    """Adapter for the ProductUpdater"""
    
    async def run(self, days=3, category_id=None, **kwargs):
        await self.log(f"Initializing Product Updater with days={days}, category_id={category_id}")
        self.scraper = ProductUpdater()
        
        try:
            if not days and not category_id:
                await self.log("No days or category_id provided. Using default values.")
                days = 3
            
            # Convert category_id to int if provided
            if category_id and not isinstance(category_id, int):
                try:
                    category_id = int(category_id)
                except ValueError:
                    await self.log(f"Invalid category_id: {category_id}. Must be an integer.")
                    category_id = None
            
            # Monkey patch the scrape_page method
            original_scrape_page = self.scraper.scrape_page
            
            async def patched_scrape_page(url, page):
                # Check if stop requested
                if await self.check_stop():
                    return (page, None)
                    
                result = await original_scrape_page(url, page)
                return result
            
            # Replace the original method
            self.scraper.scrape_page = patched_scrape_page
            
            # Monkey patch the _worker method
            original_worker = self.scraper._worker
            
            async def patched_worker(queue, category_id, days, in_progress):
                # Check if stop requested
                if await self.check_stop():
                    return (0, None)
                    
                # Get a page from the queue
                page = await queue.get()
                in_progress.add(page)
                
                try:
                    # Build the URL and scrape the page
                    url = self.scraper._build_search_url(category_id, days, page)
                    result = await self.scraper.scrape_page(url, page)
                    return result
                finally:
                    # Mark the task as done
                    queue.task_done()
            
            # Replace the original method
            self.scraper._worker = patched_worker
            
            # Monkey patch the process_products method
            original_process_products = self.scraper.process_products
            
            async def patched_process_products(category_id=None, days=None):
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
                    task = asyncio.create_task(self.scraper._worker(queue, category_id, days, in_progress))
                    tasks.append(task)
                
                # Process pages until no more products are found
                while not stop_processing:
                    # Check if stop requested
                    if await self.check_stop():
                        stop_processing = True
                        break
                        
                    # Wait for a result (page processed)
                    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                    
                    for task in done:
                        page, products = task.result()
                        in_progress.remove(page)
                        
                        if products is None:
                            # No products found on this page, stop processing
                            stop_processing = True
                            break
                            
                        await self.scraper.product_model.bulk_insert_products(products)
                        total_products += len(products)
                        await self.log(f"Scraped {len(products)} products for Category ID: {category_id}, Days: {days}, Page: {page}")
                        
                        # Update progress - using page count as a proxy for progress
                        await self.update_progress(
                            page_count, 
                            page_count + 10,  # Estimate more pages to avoid reaching 100% too early
                            f"Processing page {page_count}: {total_products} products found"
                        )
                        
                        # Add next page to the queue if we're still processing
                        if not stop_processing:
                            page_count += 1
                            await queue.put(page_count)
                            
                        # Create a new worker task to replace the completed one
                        new_task = asyncio.create_task(self.scraper._worker(queue, category_id, days, in_progress))
                        tasks.remove(task)
                        tasks.append(new_task)
                        
                # Cancel remaining tasks
                for task in tasks:
                    task.cancel()
                    
                await self.log(f"Completed updating product links. Total products processed: {total_products}")
                
                # Update total processed items
                self.processed_items += total_products
                
                # Final progress update
                await self.update_progress(
                    100, 
                    100,
                    f"Completed processing: {total_products} products found"
                )
            
            # Replace the original method
            self.scraper.process_products = patched_process_products
            
            # Run the scraper
            await self.scraper.run(category_id=category_id, days=days)
            
            if not await self.check_stop():
                await self.log("Product updating completed!")
                await self.update_progress(100, 100, "Product updating completed")
                
            return {
                "message": "Product updating completed",
                "total_products": self.processed_items,
                "days": days,
                "category_id": category_id
            }
        except Exception as e:
            error_details = traceback.format_exc()
            await self.log(f"Error in product updater: {str(e)}")
            await self.log(f"Error details: {error_details}")
            raise
        finally:
            await self.close()

class StaleProductUpdaterAdapter(BaseScraperAdapter):
    """Adapter for the StaleProductUpdater"""
    
    async def run(self, days=30, category_id=None, status=None, limit=None, **kwargs):
        await self.log(f"Initializing Stale Product Updater with days={days}, category_id={category_id}, status={status}, limit={limit}")
        self.scraper = StaleProductUpdater()
        
        try:
            # Convert parameters to correct types
            if category_id and not isinstance(category_id, int):
                try:
                    category_id = int(category_id)
                except ValueError:
                    await self.log(f"Invalid category_id: {category_id}. Must be an integer.")
                    category_id = None
            
            if limit and not isinstance(limit, int):
                try:
                    limit = int(limit)
                except ValueError:
                    await self.log(f"Invalid limit: {limit}. Must be an integer.")
                    limit = None
            
            # Monkey patch the update_product method
            original_update_product = self.scraper.update_product
            
            async def patched_update_product(product):
                # Check if stop requested
                if await self.check_stop():
                    return {
                        'product_id': product[0],
                        'name': product[1],
                        'status': 'STOPPED',
                        'message': 'Task was stopped'
                    }
                    
                result = await original_update_product(product)
                
                # Increment processed items and update progress
                self.processed_items += 1
                await self.update_progress(
                    self.processed_items, 
                    self.total_items,
                    f"Processed product: {product[1]} ({self.processed_items}/{self.total_items})"
                )
                
                # Log the result
                if result['status'] == 'UPDATED':
                    await self.log(f"Updated {result['name']} (ID: {result['product_id']}): {', '.join(result['changes'])}")
                elif result['status'] == 'FAILED':
                    await self.log(f"Failed to update {result['name']} (ID: {result['product_id']}): {result['message']}")
                
                return result
            
            # Replace the original method
            self.scraper.update_product = patched_update_product
            
            # Reset stats
            self.scraper.stats = {key: 0 for key in self.scraper.stats}
            
            # Get stale products
            stale_products = await self.scraper.get_stale_products(days, category_id, status, limit)
            self.total_items = len(stale_products)
            
            if not stale_products:
                await self.log(f"No stale products found with the specified criteria (days={days}, category_id={category_id}, status={status})")
                await self.update_progress(100, 100, "No stale products to update")
                return {"message": "No stale products to update"}
            
            await self.log(f"Found {len(stale_products)} stale products. Starting update process...")
            
            # Update products in batches
            batch_size = 10
            for i in range(0, len(stale_products), batch_size):
                # Check stop before processing batch
                if await self.check_stop():
                    break
                    
                batch = stale_products[i:i + batch_size]
                tasks = [self.scraper.update_product(product) for product in batch]
                
                await self.log(f"Processing batch {i//batch_size + 1}/{(len(stale_products) + batch_size - 1)//batch_size}")
                results = await asyncio.gather(*tasks)
                
                # Small delay between batches
                await asyncio.sleep(1)
            
            # Print statistics
            await self.log("\nUpdate Statistics:")
            await self.log(f"Total products processed: {self.scraper.stats['total_products']}")
            await self.log(f"Products updated: {self.scraper.stats['updated_products']}")
            await self.log(f"Products unchanged: {self.scraper.stats['unchanged_products']}")
            await self.log(f"Products failed: {self.scraper.stats['failed_products']}")
            await self.log("\nChanges detected:")
            await self.log(f"Price changes: {self.scraper.stats['price_changes']}")
            await self.log(f"Description changes: {self.scraper.stats['description_changes']}")
            await self.log(f"Image changes: {self.scraper.stats['image_changes']}")
            await self.log(f"Status changes: {self.scraper.stats['status_changes']}")
            
            if not await self.check_stop():
                await self.log("Stale product updating completed!")
                await self.update_progress(100, 100, "Stale product updating completed")
                
            return {
                "message": "Stale product updating completed",
                "total_products": self.total_items,
                "processed_products": self.processed_items,
                "updated_products": self.scraper.stats['updated_products'],
                "unchanged_products": self.scraper.stats['unchanged_products'],
                "failed_products": self.scraper.stats['failed_products'],
                "stats": self.scraper.stats
            }
        except Exception as e:
            error_details = traceback.format_exc()
            await self.log(f"Error in stale product updater: {str(e)}")
            await self.log(f"Error details: {error_details}")
            raise
        finally:
            await self.close()

def get_scraper_by_type(scraper_type, task_logger=None, stop_event=None, pause_event=None, resume_event=None):
    """Factory function to get a scraper adapter by type"""
    adapters = {
        ScraperType.CATEGORY: CategoryScraperAdapter,
        ScraperType.PRODUCT_COUNT: ProductCountScraperAdapter,
        ScraperType.CATEGORY_PRODUCT_LINK: CategoryProductLinkScraperAdapter,
        ScraperType.PRODUCT_DETAIL: ProductDetailScraperAdapter,
        ScraperType.SELLER: SellerScraperAdapter,
        ScraperType.PRODUCT_UPDATER: ProductUpdaterAdapter,
        ScraperType.STALE_PRODUCT_UPDATER: StaleProductUpdaterAdapter
    }
    
    adapter_class = adapters.get(scraper_type)
    if not adapter_class:
        return None
        
    return adapter_class(
        task_logger=task_logger, 
        stop_event=stop_event,
        pause_event=pause_event,
        resume_event=resume_event
    )