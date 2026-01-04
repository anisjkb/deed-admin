# src/backend/schemas/zone.py
from pydantic import BaseModel

class ZoneCreate(BaseModel):
    zone_id: str
    org_id: str
    zone_name: str
    zone_address: str | None = None
    status: str | None = "active"

class ZoneUpdate(BaseModel):
    org_id: str
    zone_name: str
    zone_address: str | None = None
    status: str | None = "active"
