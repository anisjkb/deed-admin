# src/backend/schemas/banner_schema.py
from pydantic import BaseModel
from typing import Optional

class BannerCreate(BaseModel):
    image_url: str
    headline: Optional[str] = None
    subhead: Optional[str] = None
    cta_text: Optional[str] = None
    cta_url: Optional[str] = None
    sort_order: int
    is_active: bool
    published: Optional[str] = 'Yes'  # Default to 'Yes' if not provided

class BannerUpdate(BaseModel):
    image_url: Optional[str] = None
    headline: Optional[str] = None
    subhead: Optional[str] = None
    cta_text: Optional[str] = None
    cta_url: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    published: Optional[str] = 'Yes'  # Default to 'Yes' if not provided