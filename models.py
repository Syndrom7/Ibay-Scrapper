# models.py
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

class ScraperType(Enum):
    CATEGORY = "category"
    PRODUCT_COUNT = "product_count"
    CATEGORY_PRODUCT_LINK = "category_product_link"
    PRODUCT_DETAIL = "product_detail"
    SELLER = "seller"
    PRODUCT_UPDATER = "product_updater"
    STALE_PRODUCT_UPDATER = "stale_product_updater"

class TaskCreate(BaseModel):
    type: ScraperType
    params: Optional[Dict[str, Any]] = {}

class TaskResponse(BaseModel):
    id: str
    type: str
    status: str
    progress: float
    created_at: datetime
    updated_at: datetime
    params: Dict[str, Any]

class LogEntry(BaseModel):
    message: str
    timestamp: str

class TaskLogs(BaseModel):
    logs: List[LogEntry]
    total: int

# Request models for different scraper types
class CategoryRequest(BaseModel):
    pass  # No parameters needed

class ProductCountRequest(BaseModel):
    pass  # No parameters needed

class CategoryProductLinkRequest(BaseModel):
    pass  # No parameters needed

class ProductDetailRequest(BaseModel):
    pass  # No parameters needed

class SellerRequest(BaseModel):
    pass  # No parameters needed

class ProductUpdateRequest(BaseModel):
    days: int = Field(default=3, description="Number of days to filter by")
    category_id: Optional[int] = Field(default=None, description="Category ID to filter by")

class StaleProductUpdateRequest(BaseModel):
    days: int = Field(default=30, description="Number of days to consider stale")
    category_id: Optional[int] = Field(default=None, description="Category ID to filter by")
    status: Optional[str] = Field(default="SCRAPED", description="Product status to filter by")
    limit: Optional[int] = Field(default=None, description="Limit the number of products to update")