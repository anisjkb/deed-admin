# src/backend/schemas/feedback_schema.py
from pydantic import BaseModel
from typing import Optional

class FeedbackCreate(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    message: Optional[str] = None

class FeedbackUpdate(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    message: Optional[str] = None