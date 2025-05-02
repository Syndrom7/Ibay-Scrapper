# main.py

import asyncio
import platform
from scrapper.category_scrapper import CategoryScraper
from scrapper.product_count_scraper import ProductCountScraper
from scrapper.category_product_link_scrapper import CategoryProductLinkScraper
from scrapper.product_detail_scraper import ProductDetailScraper
from scrapper.seller_scraper import SellerScraper
from scrapper.product_updater import ProductUpdater
from scrapper.stale_product_updater import StaleProductUpdater

async def run_scraper(scraper_instance, method_name='run', **kwargs):
    """
    Run a scraper instance's method and ensure proper cleanup
    
    Args:
        scraper_instance: Scraper instance to run
        method_name (str): Method name to run (default: 'run')
        **kwargs: Additional arguments to pass to the method
    """
    try:
        method = getattr(scraper_instance, method_name)
        await method(**kwargs)
    finally:
        await scraper_instance.close()

def main_menu():
    """Display the main menu"""
    print("\nAsync Ibay Scrapper")
    print("1. Scrape Categories")
    print("2. Scrape Product Counts")
    print("3. Scrape Category Product Links")
    print("4. Scrape Product Details")
    print("5. Scrape Seller Information")
    print("6. Scrape New Products")
    print("7. Update Stale Products")
    print("8. Exit")

async def async_main():
    """Main async function to run the scraper"""
    while True:
        main_menu()
        choice = input("Enter your choice (1-8): ")
        
        if choice == '1':
            category_scraper = CategoryScraper()
            await run_scraper(category_scraper)
        elif choice == '2':
            count_scraper = ProductCountScraper()
            await run_scraper(count_scraper)
        elif choice == '3':
            link_scraper = CategoryProductLinkScraper()
            await run_scraper(link_scraper)
        elif choice == '4':
            details_scraper = ProductDetailScraper()
            await run_scraper(details_scraper)
        elif choice == '5':
            seller_scraper = SellerScraper()
            await run_scraper(seller_scraper)
        elif choice == '6':
            days = int(input("Enter number of days (default: 3): ") or "3")
            category_id = input("Enter category ID (optional): ") or None
            if category_id:
                category_id = int(category_id)
            
            updater = ProductUpdater()
            await run_scraper(updater, days=days, category_id=category_id)
        elif choice == '7':
            days = int(input("Enter number of days to consider stale (default: 30): ") or "30")
            category_id = input("Enter category ID to filter (optional): ") or None
            if category_id:
                category_id = int(category_id)
            
            limit = input("Enter maximum number of products to update (optional): ") or None
            if limit:
                limit = int(limit)
                
            status = input("Enter product status to filter (default: SCRAPED): ") or "SCRAPED"
            
            stale_updater = StaleProductUpdater()
            await run_scraper(stale_updater, days=days, category_id=category_id, status=status, limit=limit)
        elif choice == '8':
            print("Exiting the program.")
            break
        else:
            print("Invalid choice. Please enter a number between 1 and 8.")

def main():
    """Entry point to run the async main function"""
    # Fix for Windows: Use SelectorEventLoop instead of ProactorEventLoop
    if platform.system() == 'Windows':
        # Import needed modules for Windows fix
        import asyncio
        import sys
        
        # Set the event loop policy to use SelectorEventLoop on Windows
        if sys.version_info >= (3, 8):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        print("Windows detected: Using SelectorEventLoop for better compatibility")
    
    # Run the async main function
    asyncio.run(async_main())

if __name__ == "__main__":
    main()