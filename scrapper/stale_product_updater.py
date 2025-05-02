# scrapper/stale_product_updater.py

import aiohttp
import os
import asyncio
import datetime
from bs4 import BeautifulSoup
from models.product_model import ProductModel
from models.seller_model import SellerModel
from scrapper.product_detail_scraper import ProductDetailScraper

class StaleProductUpdater:
    def __init__(self):
        self.product_model = ProductModel()
        self.seller_model = SellerModel()
        self.product_detail_scraper = ProductDetailScraper()
        self.headers = {"User-Agent": os.getenv('USER_AGENT')}
        self.base_url = os.getenv('BASE_URL', 'https://ibay.com.mv')
        self.session = None
        self.semaphore = asyncio.Semaphore(10)  # Limit concurrent requests to 10
        self.stats = {
            'total_products': 0,
            'updated_products': 0,
            'failed_products': 0,
            'unchanged_products': 0,
            'price_changes': 0,
            'description_changes': 0,
            'status_changes': 0,
            'image_changes': 0
        }
        
    async def init_session(self):
        """Initialize aiohttp session"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(headers=self.headers, timeout=timeout)
        return self.session

    async def get_stale_products(self, days, category_id=None, status=None, limit=None):
        """
        Get products that haven't been updated in the specified number of days
        
        Args:
            days (int): Number of days since last update
            category_id (int, optional): Filter by category ID
            status (str, optional): Filter by product status
            limit (int, optional): Limit the number of products to process
            
        Returns:
            list: List of stale products
        """
        query = """
            SELECT p.id, p.name, p.url, p.listing_id, p.status, p.price, 
                   p.description, p.last_updated, p.updated_at
            FROM products p
        """
        
        params = []
        where_clauses = []
        
        # Add category filter if specified
        if category_id:
            query += " JOIN product_categories pc ON p.id = pc.product_id"
            where_clauses.append("pc.category_id = %s")
            params.append(category_id)
        
        # Add date filter
        cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
        where_clauses.append("p.updated_at < %s")
        params.append(cutoff_date)
        
        # Add status filter if specified
        if status:
            where_clauses.append("p.status = %s")
            params.append(status)
        else:
            # By default, only update products that were successfully scraped before
            where_clauses.append("p.status = 'SCRAPED'")
        
        # Add where clauses to query
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        # Add order and limit
        query += " ORDER BY p.updated_at ASC"
        if limit:
            query += " LIMIT %s"
            params.append(limit)
        
        return await self.product_model.execute_query(query, tuple(params))

    async def update_product(self, product):
        """
        Update a stale product
        
        Args:
            product (tuple): Product information from database
            
        Returns:
            dict: Result of the update operation
        """
        product_id, name, url, listing_id, status, old_price, old_description, _, _ = product
        
        # Get fresh product details
        updated_data = await self.product_detail_scraper.get_product_details(product_id, name, url)
        
        if not updated_data:
            self.stats['failed_products'] += 1
            return {
                'product_id': product_id,
                'name': name,
                'status': 'FAILED',
                'message': 'Failed to fetch updated data'
            }
        
        # Compare old and new data to track changes
        changes = []
        if old_price != updated_data['price']:
            changes.append(f"Price changed: {old_price} -> {updated_data['price']}")
            self.stats['price_changes'] += 1
        
        if old_description != updated_data['description']:
            changes.append("Description changed")
            self.stats['description_changes'] += 1
        
        # Update product_images table
        # First, get current images
        current_images_rows = await self.product_model.execute_query(
            "SELECT image_url FROM product_images WHERE product_id = %s", (product_id,)
        )
        current_images = [row[0] for row in current_images_rows] if current_images_rows else []
        
        # Check for image changes
        if set(current_images) != set(updated_data['images']):
            changes.append(f"Images changed: {len(current_images)} -> {len(updated_data['images'])}")
            self.stats['image_changes'] += 1
            
            # Delete old images and insert new ones
            await self.product_model.execute_query(
                "DELETE FROM product_images WHERE product_id = %s", (product_id,), fetch=False
            )
            await self.product_model.insert_product_images(product_id, updated_data['images'])
        
        # Update product_info table
        # First, get current info
        current_info_rows = await self.product_model.execute_query(
            "SELECT info_key, info_value FROM product_info WHERE product_id = %s", (product_id,)
        )
        current_info = {row[0]: row[1] for row in current_info_rows} if current_info_rows else {}
        
        # Check for info changes
        new_info = {key: value for info_item in updated_data['product_info'] for key, value in info_item.items()}
        if current_info != new_info:
            changes.append("Product information changed")
            
            # Delete old info and insert new ones
            await self.product_model.execute_query(
                "DELETE FROM product_info WHERE product_id = %s", (product_id,), fetch=False
            )
            await self.product_model.insert_product_info_bulk(product_id, updated_data['product_info'])
        
        # If there are changes, update the product
        if changes:
            self.stats['updated_products'] += 1
            return {
                'product_id': product_id,
                'name': name,
                'status': 'UPDATED',
                'changes': changes
            }
        else:
            self.stats['unchanged_products'] += 1
            return {
                'product_id': product_id,
                'name': name,
                'status': 'UNCHANGED',
                'message': 'No changes detected'
            }

    async def run(self, days=30, category_id=None, status=None, limit=None):
        """
        Run the stale product updater
        
        Args:
            days (int): Number of days to consider stale (default: 30)
            category_id (int, optional): Category ID to filter by
            status (str, optional): Product status to filter by (default: 'SCRAPED')
            limit (int, optional): Limit the number of products to update
        """
        # Reset stats
        self.stats = {key: 0 for key in self.stats}
        
        # Get stale products
        stale_products = await self.get_stale_products(days, category_id, status, limit)
        self.stats['total_products'] = len(stale_products)
        
        if not stale_products:
            print(f"No stale products found with the specified criteria (days={days}, category_id={category_id}, status={status})")
            return
        
        print(f"Found {len(stale_products)} stale products. Starting update process...")
        
        # Update products in batches to manage memory usage
        batch_size = 10
        for i in range(0, len(stale_products), batch_size):
            batch = stale_products[i:i + batch_size]
            tasks = [self.update_product(product) for product in batch]
            results = await asyncio.gather(*tasks)
            
            # Print update results
            for result in results:
                if result['status'] == 'UPDATED':
                    print(f"Updated {result['name']} (ID: {result['product_id']}): {', '.join(result['changes'])}")
                elif result['status'] == 'FAILED':
                    print(f"Failed to update {result['name']} (ID: {result['product_id']}): {result['message']}")
            
            # Small delay between batches
            await asyncio.sleep(1)
        
        # Print statistics
        print("\nUpdate Statistics:")
        print(f"Total products processed: {self.stats['total_products']}")
        print(f"Products updated: {self.stats['updated_products']}")
        print(f"Products unchanged: {self.stats['unchanged_products']}")
        print(f"Products failed: {self.stats['failed_products']}")
        print("\nChanges detected:")
        print(f"Price changes: {self.stats['price_changes']}")
        print(f"Description changes: {self.stats['description_changes']}")
        print(f"Image changes: {self.stats['image_changes']}")
        print(f"Status changes: {self.stats['status_changes']}")

    async def close(self):
        """Close connections and resources"""
        if self.session:
            await self.session.close()
        await self.product_model.close()
        await self.seller_model.close()
        await self.product_detail_scraper.close()