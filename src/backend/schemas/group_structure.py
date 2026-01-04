# src/backend/schemas/group_structure.py
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field

# ---------- Group ----------
class GroupBase(BaseModel):
    group_name: str = Field(..., max_length=100)
    group_address: Optional[str] = Field(None, max_length=255)
    group_logo: Optional[str] = Field(None, max_length=255)
    status: str = Field("active", max_length=20)

class GroupCreate(GroupBase):
    group_id: Optional[int] = None  # allow DB autoincrement; keep for manual seed if needed

class GroupUpdate(GroupBase):
    pass


# ---------- Org ----------
class OrgBase(BaseModel):
    org_name: str = Field(..., max_length=100)
    org_address: Optional[str] = Field(None, max_length=255)
    org_logo: Optional[str] = Field(None, max_length=255)
    status: str = Field("active", max_length=20)

class OrgCreate(OrgBase):
    org_id: int
    group_id: int

class OrgUpdate(OrgBase):
    group_id: int  # allow re-parenting explicitly


# ---------- Zone ----------
class ZoneBase(BaseModel):
    zone_name: str = Field(..., max_length=100)
    zone_address: Optional[str] = Field(None, max_length=255)
    status: str = Field("active", max_length=20)

class ZoneCreate(ZoneBase):
    zone_id: int
    org_id: int

class ZoneUpdate(ZoneBase):
    org_id: int


# ---------- Branch ----------
class BranchBase(BaseModel):
    br_name: str = Field(..., max_length=100)
    br_address: Optional[str] = Field(None, max_length=255)
    status: str = Field("active", max_length=20)

class BranchCreate(BranchBase):
    br_id: str = Field(..., min_length=7, max_length=7)
    zone_id: int

class BranchUpdate(BranchBase):
    zone_id: int