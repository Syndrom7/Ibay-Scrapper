# main_api.py

import uvicorn
import logging
import os
from dotenv import load_dotenv
import asyncio
import platform

# Load environment variables
load_dotenv()

# Fix for Windows: Use SelectorEventLoop instead of ProactorEventLoop
if platform.system() == 'Windows':
    import asyncio
    import sys
    
    # Set the event loop policy to use SelectorEventLoop on Windows
    if sys.version_info >= (3, 8):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    print("Windows detected: Using SelectorEventLoop for better compatibility")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("ibay_scraper_api.log")
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main function to start the FastAPI server"""
    logger.info("Starting Ibay Scraper API server")
    
    # Import here to avoid circular imports
    from app import app
    
    # Get port from environment variable or use default
    port = int(os.getenv("API_PORT", 8000))
    
    # Start the server
    uvicorn.run(
        "app:app", 
        host="0.0.0.0", 
        port=port,
        reload=True,  # Enable auto-reload during development
        log_level="info"
    )

if __name__ == "__main__":
    main()