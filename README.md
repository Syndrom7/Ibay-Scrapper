# Ibay Scraper

Ibay Scraper is a Python-based web scraping project to extract data from ibay.com.mv, including categories, product counts, product links, product details, and seller information. It now includes a FastAPI-based web interface for controlling and monitoring scraping operations.

## Features

- **Asynchronous scraping** for high performance and efficiency
- **Windows compatibility** with special event loop handling
- **Robust transaction handling** for database operations
- **FastAPI web interface** for controlling scraping operations
- **Real-time progress updates** via WebSockets
- **Pause/Resume functionality** for scraping operations
- **Background task management** for running scrapers
- **Persistent logging** to PostgreSQL database
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
pip install fastapi uvicorn websockets
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
API_PORT=8000
```

5. Create Python package markers by adding `__init__.py` files:
   - Add an empty `__init__.py` file to the `models/` directory
   - Add an empty `__init__.py` file to the `scrapper/` directory

## Usage

### Command Line Interface

To start the command-line version of Ibay Scraper, run the `main.py` script:

```bash
python main.py
```

This will display a menu with different scraping options:

1. Scrape Categories
2. Scrape Product Counts
3. Scrape Category Product Links
4. Scrape Product Details
5. Scrape Seller Information
6. Scrape New Products
7. Update Stale Products
8. Exit

Select the desired option by entering the corresponding number.

### Web API Interface

To start the FastAPI server, run the `main_api.py` script:

```bash
python main_api.py
```

The API will be available at `http://localhost:8000`. The API documentation is available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### Scrapers

- `GET /api/scrapers` - List all available scrapers
- `POST /api/scrapers/category` - Start the category scraper
- `POST /api/scrapers/product-count` - Start the product count scraper
- `POST /api/scrapers/category-product-link` - Start the category product link scraper
- `POST /api/scrapers/product-detail` - Start the product detail scraper
- `POST /api/scrapers/seller` - Start the seller scraper
- `POST /api/scrapers/product-updater` - Start the product updater
- `POST /api/scrapers/stale-product-updater` - Start the stale product updater

### Tasks

- `GET /api/tasks` - List all tasks
- `GET /api/tasks/{task_id}` - Get details of a specific task
- `POST /api/tasks/{task_id}/stop` - Stop a running task
- `POST /api/tasks/{task_id}/pause` - Pause a running task
- `POST /api/tasks/{task_id}/resume` - Resume a paused task
- `GET /api/tasks/{task_id}/logs` - Get logs for a specific task

### WebSocket

- `WebSocket /ws/{task_id}` - Connect to a WebSocket for real-time updates on a specific task

## API Usage Examples

### Starting a Scraper

To start a scraper, make a POST request to the corresponding endpoint:

```bash
curl -X POST http://localhost:8000/api/scrapers/category
```

The response will include a task ID that you can use to track the progress of the scraping task:

```json
{
  "id": "12345678-1234-5678-1234-567812345678",
  "type": "category",
  "status": "created",
  "progress": 0,
  "created_at": "2025-05-03T12:00:00",
  "updated_at": "2025-05-03T12:00:00",
  "params": {}
}
```

### Task Control Operations

#### Pausing a Task

To pause a running task:

```bash
curl -X POST http://localhost:8000/api/tasks/12345678-1234-5678-1234-567812345678/pause
```

#### Resuming a Task

To resume a paused task:

```bash
curl -X POST http://localhost:8000/api/tasks/12345678-1234-5678-1234-567812345678/resume
```

#### Stopping a Task

To stop a running or paused task:

```bash
curl -X POST http://localhost:8000/api/tasks/12345678-1234-5678-1234-567812345678/stop
```

### Real-Time Updates via WebSocket

Connect to the WebSocket endpoint for real-time updates:

```javascript
// In browser JavaScript
const ws = new WebSocket('ws://localhost:8000/ws/12345678-1234-5678-1234-567812345678');

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log(data);
};

// Send commands through WebSocket
ws.send('pause');  // To pause the task
ws.send('resume'); // To resume the task
ws.send('stop');   // To stop the task
```

## Database Schema

The Ibay Scraper API adds two new tables to the existing database schema:

1. `scraper_tasks` - Stores information about scraping tasks:
   - Task ID, type, status, progress
   - Parameters, error information
   - Creation, update, and pause timestamps

2. `scraper_logs` - Stores detailed logs for each task:
   - Message, timestamp, log level
   - Foreign key relationship to scraper_tasks

These tables provide persistence for the task information and logs, allowing you to monitor and track scraping operations even after server restarts.

## How It Works

### Asynchronous Implementation

The asynchronous implementation uses:

- `asyncio` for asynchronous I/O operations
- `aiohttp` for asynchronous HTTP requests
- `aiopg` for asynchronous PostgreSQL access
- `fastapi` for the web API
- `websockets` for real-time updates

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

#### Task Management

The task management system provides:

- Background task execution
- Real-time progress updates
- Pause/resume functionality
- Detailed logging
- Persistent storage of task information

### Components

The Ibay Scraper consists of several components that work together to scrape and store data from ibay.com.mv:

1. **Base Models**: Provide database connection and query execution
   - `BaseModel`: Base class for asynchronous database operations

2. **Data Models**: Handle specific entity operations
   - `CategoryModel`, `ProductModel`, `SellerModel`: Models for categories, products, and sellers
   - `TaskLogModel`: Model for task logs and status

3. **Scrapers**: Perform web scraping for different data types
   - `CategoryScraper`: Scrapes categories and subcategories
   - `ProductCountScraper`: Fetches product counts for each category
   - `CategoryProductLinkScraper`: Extracts product links within each category
   - `ProductDetailScraper`: Retrieves detailed product information
   - `SellerScraper`: Gathers seller details
   - `ProductUpdater`: Scrapes new products based on specified criteria
   - `StaleProductUpdater`: Updates old product information

4. **API Components**: Provide the web interface
   - `app.py`: Main FastAPI application
   - `task_manager.py`: Manages background tasks
   - `api_models.py`: Defines API request and response models
   - `scrapper_adapters.py`: Adapts scrapers for use with the task system

## Project Structure

```
ibay-scraper/
├── models/
│   ├── __init__.py          # Package marker
│   ├── base_model.py        # Base model for async operations
│   ├── category_model.py    # Category model
│   ├── product_model.py     # Product model
│   ├── seller_model.py      # Seller model
│   └── task_log_model.py    # Task log model
├── scrapper/
│   ├── __init__.py          # Package marker
│   ├── category_scrapper.py # Category scraper
│   ├── product_count_scraper.py # Product count scraper
│   └── [other scrapers...]
├── app.py                   # FastAPI application
├── api_models.py            # API models
├── task_manager.py          # Task management system
├── scrapper_adapters.py     # Scraper adapters
├── main_api.py              # API entry point
├── main.py                  # CLI entry point
├── requirements.txt         # Project dependencies
└── .env                     # Environment variables
```

## Known Issues

- 301 redirected pages are not scraped currently, and a fix is yet to be implemented.

## Future Enhancements

- Implement a fix for handling 301 redirected pages during scraping.
- Add support for scheduling the scraping process.
- Implement a frontend web interface for easier visualization and control.
- Add more robust error recovery and retry mechanisms.
- Implement a distributed scraping system for even higher performance.
- Add user authentication for the API.
- Implement data visualization in the web interface.

## Troubleshooting

### Windows-Specific Issues

If you encounter "NotImplementedError" or event loop errors on Windows:
- Make sure your Python version is 3.8 or higher
- Check that the WindowsSelectorEventLoopPolicy is being used correctly
- Try adjusting the connection pool limits in `base_model.py`

### Database Connection Issues

If you encounter database connection issues:
- Verify that PostgreSQL is running
- Check that your `.env` file has the correct database connection information
- Ensure that you have the necessary permissions to create and modify tables
- For transaction errors, check if your PostgreSQL version supports the ACID operations being used

### API Issues

If you encounter issues with the API:
- Check the server logs in `ibay_scraper_api.log`
- Ensure all required Python packages are installed
- Make sure the database connection is working
- Verify that the package marker files (`__init__.py`) are present in the required directories

## Performance Tips

1. **Adjust Concurrency Levels**: The semaphore values in each scraper control the maximum number of concurrent requests. You can tune these based on your machine's capabilities.

2. **Database Connection Pooling**: The connection pool size can be adjusted in `BaseModel.init_pool()` to optimize database performance.

3. **Rate Limiting**: To avoid overwhelming the target website, built-in delays and semaphores are used. Adjust these values carefully to balance speed with respect for the site.

4. **Memory Usage**: For large scraping jobs, consider monitoring memory usage and implementing pagination or batching strategies to keep memory consumption under control.

5. **WebSocket Connections**: For long-running scraping operations, keep the WebSocket connection alive with ping/pong messages or reconnect logic in the client.