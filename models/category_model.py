from models.base_model import BaseModel

class CategoryModel(BaseModel):
    def insert_category(self, id, name, parent_id):
        # Insert a new category into the categories table
        self.execute_query("INSERT INTO categories (id, name, parent_id) VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING",
                           (id, name, parent_id), commit=True)

    def get_all_categories(self):
        # Retrieve all categories from the categories table
        rows = self.execute_query("SELECT id, name FROM categories")
        return [{'id': row[0], 'name': row[1]} for row in rows]

    def get_parent_categories(self):
        # Retrieve parent categories (categories without a parent) from the categories table
        rows = self.execute_query("SELECT id, name FROM categories WHERE parent_id IS NULL")
        return [{'id': row[0], 'name': row[1]} for row in rows]