# src/backend/schemas/award_schema.py
from pydantic import BaseModel
from typing import Optional

class AwardCreate(BaseModel):
    title: str
    issuer: Optional[str] = None
    year: Optional[int] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    published: Optional[str] = 'No'
    displaying_order: Optional[int] = None

class AwardUpdate(BaseModel):
    title: str
    issuer: Optional[str] = None
    year: Optional[int] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    published: Optional[str] = 'No'
    displaying_order: Optional[int] = None