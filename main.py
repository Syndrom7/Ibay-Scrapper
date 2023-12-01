import config
from scrapper.category_scrapper import CategoryScraper
from scrapper.product_count_scraper import ProductCountScraper
from scrapper.category_product_link_scrapper import CategoryProductLinkScraper
from scrapper.product_detail_scraper import ProductDetailScraper
from scrapper.seller_scraper import SellerScraper

def main():
    while True:
        print("\nIbay Scrapper")
        print("1. Scrape Categories")
        print("2. Scrape Product Counts")
        print("3. Scrape Category Product Links")
        print("4. Scrape Product Details")
        print("5. Scrape Seller Information")
        print("6. Exit")
        
        choice = input("Enter your choice (1-6): ")
        
        if choice == '1':
            category_scraper = CategoryScraper("ibay_categories.json")
            category_scraper.run()
        elif choice == '2':
            product_count_scraper = ProductCountScraper(config.CATEGORIES_JSON, config.PRODUCT_COUNT_OUTPUT_DATA_JSON)
            product_count_scraper.run()
        elif choice == '3':
            link_scraper = CategoryProductLinkScraper(config.PRODUCT_COUNT_OUTPUT_DATA_JSON, config.PRODUCT_LINK_OUTPUT_DATA_JSON)
            link_scraper.run()
        elif choice == '4':
            detail_scraper = ProductDetailScraper("data/", config.PRODUCT_DETAILS_OUTPUT_DATA_JSON)
            detail_scraper.run()
        elif choice == '5':
            seller_scraper = SellerScraper(config.SELLERS_INPUT_DATA_JSON, config.SELLERS_OUTPUT_DATA_JSON)
            seller_scraper.run()
        elif choice == '6':
            print("Exiting the program.")
            break
        else:
            print("Invalid choice. Please enter a number between 1 and 6.")

if __name__ == "__main__":
    main()