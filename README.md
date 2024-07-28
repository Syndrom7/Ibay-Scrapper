# Ibay Scraper

Ibay Scraper is a Python-based web scraping project to extract data from ibay.com.mv, including categories, product counts, product links, product details, and seller information.

## Features

- Scrape categories and subcategories from ibay.com.mv
- Fetch product counts for each category
- Extract product links within each category
- Retrieve detailed information for each product, including price, description, images, location, and more
- Gather seller details such as name, contact number, premium status, description, location, and membership information
- Store scraped data in PostgreSQL database

## Prerequisites

Before running the Ibay Scraper, ensure you have the following:

- Python 3.x installed
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
To start the Ibay Scraper, run the `main.py` script:

```bash
python main.py
```

The script will display a menu with different scraping options:

1. Scrape Categories
2. Scrape Product Counts
3. Scrape Category Product Links
4. Scrape Product Details
5. Scrape Seller Information
6. Scrape New Products
7. Exit

Select the desired option by entering the corresponding number.

## How It Works
The Ibay Scraper consists of several components that work together to scrape and store data from ibay.com.mv:

1. `base_model.py`: Defines the base model class and provides utility methods for executing queries.
2. `category_model.py`, `product_model.py`, `seller_model.py`: Define the models for categories, products, and sellers, respectively. These models inherit from the base model and provide methods for inserting, updating, and retrieving data from the corresponding database tables.
3. `category_scraper.py`: Scrapes categories and subcategories from ibay.com.mv and stores them in the database.
4. `product_count_scraper.py`: Fetches the product count for each category and updates the corresponding records in the database.
5. `category_product_link_scraper.py`: Extracts product links within each category and stores them in the database.
6. `product_detail_scraper.py`: Retrieves detailed information for each product, such as price, description, images, location, and more, and updates the corresponding records in the database.
7. `seller_scraper.py`: Gathers seller details, including name, contact number, premium status, description, location, and membership information, and updates the corresponding records in the database.
8. `product_updater.py`: Scrapes new products based on specified criteria (category ID and/or days) and inserts them into the database.


## Known Issues

- 301 redirected pages are not scraped currently, and a fix is yet to be implemented.

## Future Enhancements

- Implement a fix for handling 301 redirected pages during scraping.
- Add support for scheduling the scraping process.
- Implement a web interface for managing and visualizing the scraped data.