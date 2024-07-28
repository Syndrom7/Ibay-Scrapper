from scrapper.category_scrapper import CategoryScraper
from scrapper.product_count_scraper import ProductCountScraper
from scrapper.category_product_link_scrapper import CategoryProductLinkScraper
from scrapper.product_detail_scraper import ProductDetailScraper
from scrapper.seller_scraper import SellerScraper
from scrapper.product_updater import ProductUpdater


def main_menu():
    print("\nIbay Scrapper")
    print("1. Scrape Categories")
    print("2. Scrape Product Counts")
    print("3. Scrape Category Product Links")
    print("4. Scrape Product Details")
    print("5. Scrape Seller Information")
    print("6. Scrape New Products")
    print("7. Exit")

def main():
    while True:
        main_menu()
        choice = input("Enter your choice (1-7): ")
        
        if choice == '1':
            category_scraper = CategoryScraper()
            category_scraper.run()
            category_scraper.close()
        elif choice == '2':
            count_scraper = ProductCountScraper()
            count_scraper.run()
            count_scraper.close()
        elif choice == '3':
            link_scraper = CategoryProductLinkScraper()
            link_scraper.run()
            link_scraper.close()
            pass
        elif choice == '4':
            details_scraper = ProductDetailScraper()
            details_scraper.run()
            details_scraper.close()
            pass
        elif choice == '5':
            seller_scraper = SellerScraper()
            seller_scraper.run()
            seller_scraper.close()
            pass
        elif choice == '6':
            updater = ProductUpdater()
            updater.run(days=3)
            updater.close()
            pass
        elif choice == '7':
            print("Exiting the program.")
            break
        else:
            print("Invalid choice. Please enter a number between 1 and 6.")

if __name__ == "__main__":
    main()
