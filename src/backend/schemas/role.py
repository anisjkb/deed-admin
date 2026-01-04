# src/backend/schemas/role.py
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator

class RoleBase(BaseModel):
    role_name: str
    status: Optional[str] = "active"

    model_config = ConfigDict(from_attributes=True)

    @field_validator("role_name", "status", mode="before")
    @classmethod
    def _strip(cls, v: Optional[str]):
        return (v or "").strip() if v is not None else v

class RoleCreate(RoleBase):
    role_id: str

    @field_validator("role_id", mode="before")
    @classmethod
    def _role_id(cls, v: str):
        return (v or "").strip()

class RoleUpdate(BaseModel):
    role_name: Optional[str] = None
    status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("role_name", "status", mode="before")
    @classmethod
    def _strip_opt(cls, v: Optional[str]):
        return (v or "").strip() if v is not None else v

class RoleOut(RoleBase):
    role_id: str