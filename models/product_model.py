from models.base_model import BaseModel
from psycopg2.extras import execute_batch

class ProductModel(BaseModel):
    
    def update_product_count(self, id, product_count):
        try:
            self.execute_query("UPDATE categories SET product_count = %s, updated_at = NOW() WHERE id = %s", (product_count, id), commit=True)
        except Exception as e:
            print(f"Database Error: {e}")

    def bulk_insert_products(self, products):
        query = """
        INSERT INTO products (listing_id, name, url)
        VALUES (%s, %s, %s)
        ON CONFLICT (listing_id) DO UPDATE
        SET name = EXCLUDED.name, url = EXCLUDED.url
        """
        try:
            with self.conn.cursor() as cursor:
                execute_batch(cursor, query, [
                    (product['listing_id'], product['name'], product['url'])
                    for product in products
                ])
                self.conn.commit()
            print(f"Bulk inserted {len(products)} products successfully.")
        except Exception as e:
            self.conn.rollback()
            print(f"Database Error during bulk insert: {e}")
            
    def get_products_by_status(self, status):
        rows = self.execute_query("SELECT id, name, url FROM products WHERE status = %s", (status,))
        return rows

    def update_product_status(self, product_id, status, error_msg=None):
        if error_msg:
            self.execute_query("UPDATE products SET status = %s, error_message = %s, updated_at = NOW() WHERE id = %s",
                (status, error_msg, product_id), commit=True)
        else:
            self.execute_query("UPDATE products SET status = %s, updated_at = NOW() WHERE id = %s", (status, product_id), commit=True)

    def update_product(self, product_id, product_data):
        try:
            self.execute_query("""
                UPDATE products
                SET price = %s, product_location = %s, description = %s, 
                    last_updated = %s, status = 'SCRAPED', seller_id = %s, updated_at = NOW()
                WHERE id = %s;
                """, (product_data['price'], product_data['product_location'], product_data['description'], 
                      product_data['last_updated'], product_data['seller_id'], product_id), commit=True)
        except Exception as e:
            print(f"Database Error: {e}")

    def insert_product_categories(self, product_id, category_ids):
        query = """
            INSERT INTO product_categories (product_id, category_id)
            VALUES (%s, %s) ON CONFLICT DO NOTHING;
        """
        try:
            with self.conn.cursor() as cursor:
                execute_batch(cursor, query, [(product_id, category_id) for category_id in category_ids])
            self.conn.commit()
            # print(f"Bulk inserted {len(category_ids)} categories for product {product_id}")
        except Exception as e:
            self.conn.rollback()
            print(f"Database Error during bulk category insert: {e}")

    def insert_product_images(self, product_id, image_urls):
        query = """
            INSERT INTO product_images (product_id, image_url)
            VALUES (%s, %s) ON CONFLICT DO NOTHING;
        """
        try:
            with self.conn.cursor() as cursor:
                execute_batch(cursor, query, [(product_id, image_url) for image_url in image_urls])
            self.conn.commit()
            # print(f"Bulk inserted {len(image_urls)} images for product {product_id}")
        except Exception as e:
            self.conn.rollback()
            print(f"Database Error during bulk image insert: {e}")

    def insert_product_info_bulk(self, product_id, product_info):
        query = """
            INSERT INTO product_info (product_id, info_key, info_value)
            VALUES (%s, %s, %s) ON CONFLICT DO NOTHING;
        """
        try:
            with self.conn.cursor() as cursor:
                execute_batch(cursor, query, [
                    (product_id, key, value)
                    for info_item in product_info
                    for key, value in info_item.items()
                ])
            self.conn.commit()
            # print(f"Bulk inserted {len(product_info)} info items for product {product_id}")
        except Exception as e:
            self.conn.rollback()
            print(f"Database Error during bulk info insert: {e}")
    
    def get_latest_listing_id(self):
        result = self.execute_query("SELECT MAX(listing_id) FROM products")
        return result[0][0] if result and result[0][0] is not None else 0
    
