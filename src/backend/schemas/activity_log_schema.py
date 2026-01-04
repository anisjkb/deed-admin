# src/backend/schemas/activity_log_schema.py
from pydantic import BaseModel
from typing import Optional, Dict

class UserActivityLogBase(BaseModel):
    event_type: str
    ip_address: str
    device_info: str
    geolocation_city: str
    geolocation_country: str
    login_success: bool
    risk_score: float
    extra_info: Optional[Dict] = {}

class UserActivityLogRead(UserActivityLogBase):
    id: int
    user_id: int
    timestamp: str

    model_config = {
        "from_attributes": True
    }