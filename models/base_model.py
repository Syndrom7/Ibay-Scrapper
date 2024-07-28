import os
import psycopg2
from dotenv import load_dotenv

class BaseModel:
    def __init__(self):
        # Load environment variables from .env file
        dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        load_dotenv(dotenv_path)
    
        # Establish a connection to the PostgreSQL database
        self.conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT')
        )

        # Create necessary tables if they don't exist
        self.create_table()
        
    def execute_query(self, query, params=None, commit=False):
        # Execute a SQL query with optional parameters and commit flag
        with self.conn.cursor() as cursor:
            cursor.execute(query, params)
            if commit:
                self.conn.commit()
            if query.strip().upper().startswith("SELECT"):
                return cursor.fetchall()

    def create_table(self):
        # Create tables for categories, sellers, products, product_categories, product_images, and product_info
        self.execute_query('''
                CREATE TABLE IF NOT EXISTS categories (
                    id SERIAL PRIMARY KEY,
                    name TEXT,
                    parent_id INTEGER,
                    product_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS sellers (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    contact_number TEXT,
                    image_src TEXT,
                    is_premium BOOLEAN DEFAULT FALSE,
                    description TEXT,
                    location TEXT,
                    member_since DATE,
                    last_login DATE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    name TEXT,
                    url TEXT,
                    listing_id INTEGER UNIQUE,
                    seller_id INTEGER REFERENCES sellers(id) ON DELETE CASCADE,
                    price DECIMAL(10,2),
                    product_location TEXT,
                    description TEXT,
                    last_updated DATE,
                    status VARCHAR(255) DEFAULT 'NOT_SCRAPED',
                    error_message TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS product_categories (
                    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
                    category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
                    PRIMARY KEY (product_id, category_id),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS product_images (
                    id SERIAL PRIMARY KEY,
                    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
                    image_url TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS product_info (
                    id SERIAL PRIMARY KEY,
                    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
                    info_key TEXT,
                    info_value TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            ''')
    
    def close(self):
        # Close the database connection
        self.conn.close()