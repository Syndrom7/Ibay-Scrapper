# Models/base_model.py

import os
import asyncio
import aiopg
import platform
from dotenv import load_dotenv

class BaseModel:
    def __init__(self):
        # Load environment variables from .env file
        dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        load_dotenv(dotenv_path)
        
        # Database connection details
        self.db_config = {
            'dbname': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'host': os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT')
        }
        
        # Connection pool will be initialized when needed
        self.pool = None
        
        # Flag to track if we're on Windows (for special handling)
        self.is_windows = platform.system() == 'Windows'

    async def init_pool(self):
        """Initialize the connection pool if not already done"""
        if self.pool is None:
            try:
                # Set a shorter timeout for Windows to avoid blocking issues
                if self.is_windows:
                    self.pool = await aiopg.create_pool(
                        **self.db_config, 
                        timeout=10,
                        echo=False  # Disable echo to reduce file descriptor usage
                    )
                else:
                    self.pool = await aiopg.create_pool(**self.db_config)
                
                # Create necessary tables
                await self.create_table()
            except Exception as e:
                print(f"Error initializing pool: {e}")
                # Re-raise to ensure caller knows about the issue
                raise
                
        return self.pool

    async def execute_query(self, query, params=None, fetch=True):
        """
        Execute a SQL query asynchronously with optional parameters and fetch results
        
        Args:
            query (str): SQL query to execute
            params (tuple, optional): Parameters for the query
            fetch (bool, optional): Whether to fetch results (for SELECT queries)
            
        Returns:
            list: Query results (for SELECT queries) or None
        """
        try:
            pool = await self.init_pool()
            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, params)
                    
                    if fetch and query.strip().upper().startswith("SELECT"):
                        return await cursor.fetchall()
                    return None
        except Exception as e:
            print(f"Database error executing query: {e}")
            # Re-raise for critical operations
            if "CREATE TABLE" in query:
                raise
            return [] if fetch else None

    async def execute_transaction(self, queries_and_params):
        """
        Execute multiple queries in a single transaction using explicit SQL transaction statements
        
        Args:
            queries_and_params (list): List of tuples (query, params)
        """
        try:
            pool = await self.init_pool()
            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # Start transaction with BEGIN
                    await cursor.execute("BEGIN")
                    try:
                        for query, params in queries_and_params:
                            await cursor.execute(query, params)
                        # If all queries succeed, commit the transaction
                        await cursor.execute("COMMIT")
                    except Exception as e:
                        # If any query fails, rollback the transaction
                        await cursor.execute("ROLLBACK")
                        print(f"Transaction error: {e}")
                        raise
        except Exception as e:
            print(f"Database connection error: {e}")
            raise

    async def create_table(self):
        """Create necessary database tables if they don't exist"""
        table_queries = [
            '''CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                name TEXT,
                parent_id INTEGER,
                product_count INTEGER DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );''',
            '''CREATE TABLE IF NOT EXISTS sellers (
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
            );''',
            '''CREATE TABLE IF NOT EXISTS products (
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
            );''',
            '''CREATE TABLE IF NOT EXISTS product_categories (
                product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
                category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
                PRIMARY KEY (product_id, category_id),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );''',
            '''CREATE TABLE IF NOT EXISTS product_images (
                id SERIAL PRIMARY KEY,
                product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
                image_url TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );''',
            '''CREATE TABLE IF NOT EXISTS product_info (
                id SERIAL PRIMARY KEY,
                product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
                info_key TEXT,
                info_value TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );''',
            '''CREATE TABLE IF NOT EXISTS scraper_tasks (
                id VARCHAR(36) PRIMARY KEY,
                type VARCHAR(50) NOT NULL,
                status VARCHAR(20) NOT NULL,
                progress FLOAT DEFAULT 0,
                params JSONB DEFAULT '{}'::jsonb,
                error TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                paused_at TIMESTAMP WITH TIME ZONE
            );''',
            '''CREATE TABLE IF NOT EXISTS scraper_logs (
                id SERIAL PRIMARY KEY,
                task_id VARCHAR(36) REFERENCES scraper_tasks(id) ON DELETE CASCADE,
                message TEXT NOT NULL,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                level VARCHAR(10) DEFAULT 'INFO'
            );'''
        ]
        
        # Execute each CREATE TABLE statement individually
        # aiopg will auto-commit DDL statements
        pool = await self.init_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                for query in table_queries:
                    await cursor.execute(query)

    async def execute_batch(self, query, params_list):
        """
        Execute a batch of SQL queries asynchronously with explicit transaction control
        
        Args:
            query (str): SQL query to execute
            params_list (list): List of parameter tuples
        """
        if not params_list:
            return
            
        try:
            pool = await self.init_pool()
            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # Start transaction with BEGIN statement
                    await cursor.execute("BEGIN")
                    try:
                        for params in params_list:
                            await cursor.execute(query, params)
                        # If all executions succeed, commit the transaction
                        await cursor.execute("COMMIT")
                    except Exception as e:
                        # If any execution fails, rollback the transaction
                        await cursor.execute("ROLLBACK")
                        print(f"Batch error: {e}")
                        raise
        except Exception as e:
            print(f"Database error executing batch: {e}")
            raise

    async def close(self):
        """Close the database connection pool safely"""
        try:
            if self.pool is not None:
                self.pool.close()
                # Use a timeout to prevent hanging
                await asyncio.wait_for(self.pool.wait_closed(), timeout=5.0)
        except asyncio.TimeoutError:
            print("Warning: Pool close timed out - some connections may not be properly closed")
        except Exception as e:
            print(f"Error closing pool: {e}")