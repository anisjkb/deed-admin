# src/backend/schemas/branch.py
from pydantic import BaseModel

class BranchCreate(BaseModel):
    br_id: str
    zone_id: str
    br_name: str
    br_address: str | None = None
    status: str | None = "active"

class BranchUpdate(BaseModel):
    zone_id: str
    br_name: str
    br_address: str | None = None
    status: str | None = "active"
