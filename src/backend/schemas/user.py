# src/backend/schemas/user.py
from __future__ import annotations
from datetime import date
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, SecretStr, field_validator

# -------------------------------------------------------------------
# Shared base (non-sensitive). NOTE: user_name is accepted by API
# for UI convenience, but not stored in user_info (DB has no column).
# -------------------------------------------------------------------
class UserBase(BaseModel):
    emp_id: str = Field(min_length=1, max_length=20)
    login_id: str = Field(min_length=1, max_length=50)
    role_id: str = Field(min_length=1, max_length=2)
    user_name: str = Field(min_length=1, max_length=100)  # UI-only (not persisted)
    email: Optional[EmailStr] = None
    status: Optional[str] = Field(default="A", min_length=1, max_length=1)

    @field_validator("emp_id", "login_id", "role_id", mode="before")
    @classmethod
    def _trim(cls, v: str) -> str:
        return (v or "").strip()

    @field_validator("status", mode="before")
    @classmethod
    def _normalize_status(cls, v: Optional[str]) -> str:
        if not v:
            return "A"
        vv = v.strip().lower()
        if vv in ("a", "active"):
            return "A"
        if vv in ("i", "inactive"):
            return "I"
        return "A"

# -------------------------------------------------------------------
# Requests
# -------------------------------------------------------------------
class UserCreate(BaseModel):
    emp_id: str = Field(min_length=1, max_length=20)
    login_id: str = Field(min_length=1, max_length=50)
    role_id: str = Field(min_length=1, max_length=2)
    user_name: str = Field(min_length=1, max_length=100)  # UI-only
    email: Optional[EmailStr] = None
    password: SecretStr = Field(min_length=6, max_length=255)  # send already-validated; will be hashed upstream

    @field_validator("emp_id", "login_id", "role_id", mode="before")
    @classmethod
    def _trim(cls, v: str) -> str:
        return (v or "").strip()

class UserUpdate(BaseModel):
    # login_id is the PK (path param in routes) and is NOT changed here
    role_id: Optional[str] = Field(default=None, min_length=1, max_length=2)
    user_name: Optional[str] = Field(default=None, min_length=1, max_length=100)  # UI-only
    email: Optional[EmailStr] = None
    status: Optional[str] = Field(default=None, min_length=1, max_length=1)
    password: Optional[SecretStr] = Field(default=None, min_length=6, max_length=255)

    @field_validator("role_id", mode="before")
    @classmethod
    def _trim_role(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if isinstance(v, str) else v

    @field_validator("status", mode="before")
    @classmethod
    def _normalize_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        vv = v.strip().lower()
        if vv in ("a", "active"):
            return "A"
        if vv in ("i", "inactive"):
            return "I"
        return "A"

# -------------------------------------------------------------------
# Responses
# -------------------------------------------------------------------
class UserRead(UserBase):
    created_by: Optional[str] = None
    create_dt: date
    updated_by: Optional[str] = None
    update_dt: date
    model_config = {"from_attributes": True}

class UserList(BaseModel):
    emp_id: str
    login_id: str
    user_name: str   # UI-only field; populate from emp_info in views if needed
    role_id: str
    email: Optional[EmailStr] = None
    status: Optional[str] = "A"
    model_config = {"from_attributes": True}

__all__ = [
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserRead",
    "UserList",
]