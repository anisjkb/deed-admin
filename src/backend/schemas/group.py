# src/backend/schemas/group.py
from pydantic import BaseModel

class GroupCreate(BaseModel):
    group_id: str
    group_name: str
    group_address: str | None = None
    group_logo: str | None = None
    status: str | None = "active"

class GroupUpdate(BaseModel):
    group_name: str
    group_address: str | None = None
    group_logo: str | None = None
    status: str | None = "active"
