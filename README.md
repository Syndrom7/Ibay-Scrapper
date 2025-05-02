# Ibay Scraper

Ibay Scraper is a Python-based web scraping project to extract data from ibay.com.mv, including categories, product counts, product links, product details, and seller information.

## Features

- **Asynchronous scraping** for high performance and efficiency
- **Windows compatibility** with special event loop handling
- **Robust transaction handling** for database operations
- Scrape categories and subcategories from ibay.com.mv
- Fetch product counts for each category
- Extract product links within each category
- Retrieve detailed information for each product, including price, description, images, location, and more
- Gather seller details such as name, contact number, premium status, description, location, and membership information
- Store scraped data in PostgreSQL database

## Prerequisites

Before running the Ibay Scraper, ensure you have the following:

- Python 3.8+ installed (asyncio and aiohttp require Python 3.7+)
- PostgreSQL database set up with the required tables (see `base_model.py` for table schemas)
- Required Python packages installed (see `requirements.txt`)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/Syndrom7/Ibay-Scrapper.git
cd ibay-scraper
```

2. Create a virtual environment (optional but recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

3. Install the required packages:

```bash
pip install -r requirements.txt
```

4. Set up the database connection by creating a .env file in the project root with the following variables:

```dotenv
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_HOST=your_database_host
DB_PORT=your_database_port
BASE_URL=https://ibay.com.mv
USER_AGENT=your_user_agent
```

## Usage

### Synchronous Version

To start the synchronous version of Ibay Scraper, run the `main.py` script:

```bash
python main.py
```

### Asynchronous Version

To start the asynchronous version of Ibay Scraper, run the `async_main.py` script:

```bash
python async_main.py
```

Both scripts will display a menu with different scraping options:

1. Scrape Categories
2. Scrape Product Counts
3. Scrape Category Product Links
4. Scrape Product Details
5. Scrape Seller Information
6. Scrape New Products
7. Exit

Select the desired option by entering the corresponding number.

## How It Works

### Asynchronous Implementation

The asynchronous implementation uses:

- `asyncio` for asynchronous I/O operations
- `aiohttp` for asynchronous HTTP requests
- `aiopg` for asynchronous PostgreSQL access

This implementation offers several advantages over the synchronous threading approach:

- Lower memory footprint
- Better concurrency control
- Improved error handling
- More efficient I/O operations
- Better scalability

### Special Features

#### Windows Compatibility

The asynchronous implementation includes special handling for Windows:

- Uses the appropriate event loop policy (`WindowsSelectorEventLoopPolicy`)
- Implements connection pool management with shorter timeouts
- Provides better error handling for socket operations

#### Transaction Handling

The database operations use robust transaction handling:

- Explicit SQL transaction control (`BEGIN`, `COMMIT`, `ROLLBACK`)
- Batch operations for bulk inserts
- Error recovery with transaction rollbacks
- Connection pooling for efficient database access

### Components

The Ibay Scraper consists of several components that work together to scrape and store data from ibay.com.mv:

1. **Base Models**: Provide database connection and query execution
   - `BaseModel`: Base class for asynchronous database operations

2. **Data Models**: Handle specific entity operations
   - `CategoryModel`, `ProductModel`, `SellerModel`: Models for categories, products, and sellers

3. **Scrapers**: Perform web scraping for different data types
   - `CategoryScraper`: Scrapes categories and subcategories
   - `ProductCountScraper`: Fetches product counts for each category
   - `CategoryProductLinkScraper`: Extracts product links within each category
   - `ProductDetailScraper`: Retrieves detailed product information
   - `SellerScraper`: Gathers seller details
   - `ProductUpdater`: Scrapes new products based on specified criteria

## Project Structure

```
ibay-scraper/
├── models/
│   ├── base_model.py        # Base model for async operations
│   ├── category_model.py    # Category model (async)
│   ├── product_model.py     # Product model (async)
│   └── seller_model.py      # Seller model (async)
├── scrapper/
│   ├── category_scrapper.py # Category scraper (async)
│   ├── product_count_scraper.py # Product count scraper (async)
│   ├── [other scrapers...]
├── main.py                        # Main script for sync operation
├── main.py                  # Main script for async operation
├── requirements.txt               # Project dependencies
└── .env                           # Environment variables
```

## Known Issues

- 301 redirected pages are not scraped currently, and a fix is yet to be implemented.

## Future Enhancements

- Implement a fix for handling 301 redirected pages during scraping.
- Add support for scheduling the scraping process.
- Implement a web interface for managing and visualizing the scraped data.
- Add more robust error recovery and retry mechanisms.
- Implement a distributed scraping system for even higher performance.

## Troubleshooting

### Windows-Specific Issues

If you encounter "NotImplementedError" or event loop errors on Windows:
- Make sure your Python version is 3.8 or higher
- Check that the WindowsSelectorEventLoopPolicy is being used correctly
- Try adjusting the connection pool limits in `async_base_model.py`

### Database Connection Issues

If you encounter database connection issues:
- Verify that PostgreSQL is running
- Check that your `.env` file has the correct database connection information
- Ensure that you have the necessary permissions to create and modify tables
- For transaction errors, check if your PostgreSQL version supports the ACID operations being used

## Performance Tips

1. **Adjust Concurrency Levels**: The semaphore values in each scraper control the maximum number of concurrent requests. You can tune these based on your machine's capabilities.

2. **Database Connection Pooling**: The connection pool size can be adjusted in `AsyncBaseModel.init_pool()` to optimize database performance.

3. **Rate Limiting**: To avoid overwhelming the target website, built-in delays and semaphores are used. Adjust these values carefully to balance speed with respect for the site.

4. **Memory Usage**: For large scraping jobs, consider monitoring memory usage and implementing pagination or batching strategies to keep memory consumption under control.