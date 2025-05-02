# scrapper/seller_scraper.py

import aiohttp
import os
import asyncio
from bs4 import BeautifulSoup
from models.seller_model import SellerModel

class SellerScraper:
    def __init__(self):
        self.seller_model = SellerModel()
        self.base_url = os.getenv('BASE_URL')
        self.headers = {"User-Agent": os.getenv('USER_AGENT')}
        self.session = None
        self.semaphore = asyncio.Semaphore(20)  # Limit concurrent requests
        
    async def init_session(self):
        """Initialize aiohttp session"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(headers=self.headers, timeout=timeout)
        return self.session
    
    async def extract_seller_info(self, seller_id):
        """
        Extract seller information from their profile page
        
        Args:
            seller_id (int): Seller ID
            
        Returns:
            dict or None: Seller information or None if error
        """
        session = await self.init_session()
        print(f"Fetching Seller id: {seller_id}")
        url = f"{self.base_url}/index.php?page=profile&id={seller_id}"
        
        # Use semaphore to limit concurrent requests
        async with self.semaphore:
            try:
                async with session.get(url, timeout=30) as response:
                    if response.status != 200:
                        print(f"Failed to fetch seller {seller_id}, status code: {response.status}")
                        return None
                    
                    content = await response.text()
                    soup = BeautifulSoup(content, 'lxml')
                    
                    seller_info = {
                        "id": seller_id,
                        "image_src": "https://" + (soup.select_one('.bg-light .col.s6.l2 img[src]')['src'] if soup.select_one('.bg-light .col.s6.l2 img[src]') else ''),
                        "is_premium": bool(soup.select_one('.bg-light .col.s6.l4 img[alt="Premium Seller"]')),
                        "description": soup.select_one('.bg-light .col.s12.l6 p').get_text() if soup.select_one('.bg-light .col.s12.l6 p') else None,
                        "location": soup.select_one('.bg-light .col.s12.l6 p b:nth-child(1)').get_text() if soup.select_one('.bg-light .col.s12.l6 p b:nth-child(1)') else None,
                        "member_since": soup.select_one('.bg-light .col.s12.l6 p b:nth-child(2)').get_text() if soup.select_one('.bg-light .col.s12.l6 p b:nth-child(2)') else None,
                        "last_login": soup.select_one('.bg-light .col.s12.l6 p:nth-of-type(3) b').next_sibling.strip() if soup.select_one('.bg-light .col.s12.l6 p:nth-of-type(3) b') else None
                    }

                    await self.seller_model.update_seller(seller_info)
                    return seller_info
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                print(f"Error occurred while processing seller ID {seller_id}: {e}")
            except Exception as e:
                print(f"Unexpected error processing seller ID {seller_id}: {e}")
                
            return None

    async def run(self):
        """Run the seller scraper"""
        seller_ids = await self.seller_model.fetch_seller_ids()
        
        # Process sellers in batches to manage memory usage
        batch_size = 100
        for i in range(0, len(seller_ids), batch_size):
            batch = seller_ids[i:i + batch_size]
            tasks = [self.extract_seller_info(sid) for sid in batch]
            await asyncio.gather(*tasks)
            
            # Small delay between batches
            await asyncio.sleep(1)
            
        print("Completed updating all sellers.")

    async def close(self):
        """Close connections and resources"""
        if self.session:
            await self.session.close()
        await self.seller_model.close()