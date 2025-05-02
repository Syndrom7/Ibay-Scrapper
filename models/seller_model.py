# models/seller_model.py

from models.base_model import BaseModel

class SellerModel(BaseModel):
    async def insert_seller(self, seller_details):
        """
        Insert a new seller into the database
        
        Args:
            seller_details (dict): Seller details including id, name, and contact_number
        """
        try:
            await self.execute_query("""
                    INSERT INTO sellers (id, name, contact_number)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (seller_details['id'], seller_details['name'], seller_details['contact_number']), 
                    fetch=False
            )
        except Exception as e:
            print(f"Database Error: {e}")

    async def update_seller(self, seller_details):
        """
        Update seller details
        
        Args:
            seller_details (dict): Seller details to update
        """
        try:
            await self.execute_query("""
                UPDATE sellers
                SET image_src = %s, is_premium = %s, description = %s, location = %s, member_since = %s, last_login = %s, updated_at = NOW()
                WHERE id = %s
                """, 
                (
                    seller_details['image_src'], 
                    seller_details['is_premium'], 
                    seller_details['description'], 
                    seller_details['location'], 
                    seller_details['member_since'], 
                    seller_details['last_login'],
                    seller_details['id']
                ), 
                fetch=False
            )
        except Exception as e:
            print(f"Database Error: {e}")

    async def fetch_seller_ids(self):
        """
        Fetch all seller IDs from the database
        
        Returns:
            list: List of seller IDs
        """
        try:
            rows = await self.execute_query("SELECT id FROM sellers")
            return [id[0] for id in rows]   
        except Exception as e:
            print(f"Database Error: {e}")
            return []