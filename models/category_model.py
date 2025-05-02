# models/category_model.py

from models.base_model import BaseModel

class CategoryModel(BaseModel):
    async def insert_category(self, id, name, parent_id):
        """
        Insert a new category into the categories table
        
        Args:
            id (int): Category ID
            name (str): Category name
            parent_id (int, optional): Parent category ID
        """
        await self.execute_query(
            "INSERT INTO categories (id, name, parent_id) VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING",
            (id, name, parent_id), 
            fetch=False
        )

    async def get_all_categories(self):
        """
        Retrieve all categories from the categories table
        
        Returns:
            list: List of dictionaries containing category ID and name
        """
        rows = await self.execute_query("SELECT id, name FROM categories")
        return [{'id': row[0], 'name': row[1]} for row in rows]

    async def get_parent_categories(self):
        """
        Retrieve parent categories (categories without a parent) from the categories table
        
        Returns:
            list: List of dictionaries containing parent category ID and name
        """
        rows = await self.execute_query("SELECT id, name FROM categories WHERE parent_id IS NULL")
        return [{'id': row[0], 'name': row[1]} for row in rows]
        
    async def update_product_count(self, id, product_count):
        """
        Update the product count for a category
        
        Args:
            id (int): Category ID
            product_count (int): Number of products in the category
        """
        try:
            await self.execute_query(
                "UPDATE categories SET product_count = %s, updated_at = NOW() WHERE id = %s", 
                (product_count, id), 
                fetch=False
            )
        except Exception as e:
            print(f"Database Error: {e}")