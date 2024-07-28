from models.base_model import BaseModel

class SellerModel(BaseModel):
    def insert_seller(self, seller_details):
        try:
            self.execute_query("""
                    INSERT INTO sellers (id, name, contact_number)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,(seller_details['id'], seller_details['name'], seller_details['contact_number']), commit=True)
        except Exception as e:
            print(f"Database Error: {e}")
            self.conn.rollback()

    def update_seller(self, seller_details):
        try:
            self.execute_query("""
                UPDATE sellers
                SET image_src = %s, is_premium = %s, description = %s, location = %s, member_since = %s, last_login = %s, updated_at = NOW()
                WHERE id = %s
                """, (
                    seller_details['image_src'], 
                    seller_details['is_premium'], 
                    seller_details['description'], 
                    seller_details['location'], 
                    seller_details['member_since'], 
                    seller_details['last_login'],
                    seller_details['id']
                ), 
                commit=True
            )
        except Exception as e:
            print(f"Database Error: {e}")
            self.conn.rollback()

    def fetch_seller_ids(self):
        try:
            rows = self.execute_query("SELECT id FROM sellers")
            return [id[0] for id in rows]   
        except Exception as e:
            print(f"Database Error: {e}")