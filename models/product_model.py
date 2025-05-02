# models/product_model.py

from models.base_model import BaseModel

class ProductModel(BaseModel):
    
    async def bulk_insert_products(self, products):
        """
        Insert multiple products into the database
        
        Args:
            products (list): List of product dictionaries with listing_id, name, and url
        """
        if not products:
            return
            
        query = """
        INSERT INTO products (listing_id, name, url)
        VALUES (%s, %s, %s)
        ON CONFLICT (listing_id) DO UPDATE
        SET name = EXCLUDED.name, url = EXCLUDED.url
        """
        
        try:
            params_list = [(product['listing_id'], product['name'], product['url']) for product in products]
            await self.execute_batch(query, params_list)
            print(f"Bulk inserted {len(products)} products successfully.")
        except Exception as e:
            print(f"Database Error during bulk insert: {e}")
            
    async def get_products_by_status(self, status):
        """
        Get products with a specific status
        
        Args:
            status (str): Status to filter by
            
        Returns:
            list: List of tuples containing product id, name, and url
        """
        rows = await self.execute_query(
            "SELECT id, name, url FROM products WHERE status = %s", 
            (status,)
        )
        return rows

    async def update_product_status(self, product_id, status, error_msg=None):
        """
        Update the status of a product
        
        Args:
            product_id (int): Product ID
            status (str): New status
            error_msg (str, optional): Error message if any
        """
        if error_msg:
            await self.execute_query(
                "UPDATE products SET status = %s, error_message = %s, updated_at = NOW() WHERE id = %s",
                (status, error_msg, product_id), 
                fetch=False
            )
        else:
            await self.execute_query(
                "UPDATE products SET status = %s, updated_at = NOW() WHERE id = %s", 
                (status, product_id), 
                fetch=False
            )

    async def update_product(self, product_id, product_data):
        """
        Update product details
        
        Args:
            product_id (int): Product ID
            product_data (dict): Product data to update
        """
        try:
            await self.execute_query("""
                UPDATE products
                SET price = %s, product_location = %s, description = %s, 
                    last_updated = %s, status = 'SCRAPED', seller_id = %s, updated_at = NOW()
                WHERE id = %s;
                """, 
                (
                    product_data['price'], 
                    product_data['product_location'], 
                    product_data['description'], 
                    product_data['last_updated'], 
                    product_data['seller_id'], 
                    product_id
                ),
                fetch=False
            )
        except Exception as e:
            print(f"Database Error: {e}")

    async def insert_product_categories(self, product_id, category_ids):
        """
        Insert product category associations
        
        Args:
            product_id (int): Product ID
            category_ids (list): List of category IDs
        """
        if not category_ids:
            return
            
        query = """
            INSERT INTO product_categories (product_id, category_id)
            VALUES (%s, %s) ON CONFLICT DO NOTHING;
        """
        
        try:
            params_list = [(product_id, category_id) for category_id in category_ids]
            await self.execute_batch(query, params_list)
        except Exception as e:
            print(f"Database Error during bulk category insert: {e}")

    async def insert_product_images(self, product_id, image_urls):
        """
        Insert product images
        
        Args:
            product_id (int): Product ID
            image_urls (list): List of image URLs
        """
        if not image_urls:
            return
            
        query = """
            INSERT INTO product_images (product_id, image_url)
            VALUES (%s, %s) ON CONFLICT DO NOTHING;
        """
        
        try:
            params_list = [(product_id, image_url) for image_url in image_urls]
            await self.execute_batch(query, params_list)
        except Exception as e:
            print(f"Database Error during bulk image insert: {e}")

    async def insert_product_info_bulk(self, product_id, product_info):
        """
        Insert product information items in bulk
        
        Args:
            product_id (int): Product ID
            product_info (list): List of product info dictionaries
        """
        if not product_info:
            return
            
        query = """
            INSERT INTO product_info (product_id, info_key, info_value)
            VALUES (%s, %s, %s) ON CONFLICT DO NOTHING;
        """
        
        try:
            params_list = [
                (product_id, key, value)
                for info_item in product_info
                for key, value in info_item.items()
            ]
            await self.execute_batch(query, params_list)
        except Exception as e:
            print(f"Database Error during bulk info insert: {e}")
    
    async def get_latest_listing_id(self):
        """
        Get the highest listing ID in the database
        
        Returns:
            int: Highest listing ID or 0 if none found
        """
        result = await self.execute_query("SELECT MAX(listing_id) FROM products")
        return result[0][0] if result and result[0][0] is not None else 0