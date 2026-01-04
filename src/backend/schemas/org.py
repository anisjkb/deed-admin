# src/backend/schemas/org.py
from pydantic import BaseModel

class OrgCreate(BaseModel):
    org_id: str
    group_id: str
    org_name: str
    org_address: str | None = None
    org_logo: str | None = None
    status: str | None = "active"

class OrgUpdate(BaseModel):
    group_id: str
    org_name: str
    org_address: str | None = None
    org_logo: str | None = None
    status: str | None = "active"
