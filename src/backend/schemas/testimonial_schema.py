from pydantic import BaseModel
from typing import Optional

class TestimonialCreate(BaseModel):
    name: str
    role: Optional[str] = None
    project_id: int
    project_title: Optional[str] = None
    quote: str
    video_url: Optional[str] = None
    sort_order: int
    published: str = "Yes"

class TestimonialUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    project_id: Optional[int] = None
    project_title: Optional[str] = None
    quote: Optional[str] = None
    video_url: Optional[str] = None
    sort_order: Optional[int] = None
    published: Optional[str] = None
