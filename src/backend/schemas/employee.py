# src/backend/schemas/employee.py
from pydantic import BaseModel, field_validator
from typing import Optional

EMP_TYPE_VALUES = ("Contractual", "Permanent", "Management", "Board Member")

class EmployeeCreate(BaseModel):
    emp_id: str
    emp_name: str
    gender: Optional[str] = None
    dob: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    join_date: Optional[str] = None

    desig_id: Optional[str] = None
    br_id: Optional[str] = None
    zone_id: Optional[str] = None
    org_id: Optional[str] = None
    group_id: Optional[str] = None

    nid: Optional[str] = None
    blood_group: Optional[str] = None
    address: Optional[str] = None
    emergency_phone: Optional[str] = None
    photo_url: Optional[str] = None

    status: Optional[str] = "active"

    # NEW
    emp_type: Optional[str] = "Contractual"
    bio: Optional[str] = None
    linkedin_url: Optional[str] = None
    sort_order: Optional[int] = None
    bio_details: Optional[str] = None

    @field_validator("emp_id")
    @classmethod
    def must_be_6_chars(cls, v: str) -> str:
        v = (v or "").strip()
        if len(v) != 6:
            raise ValueError("emp_id must be exactly 6 characters (e.g., 000123)")
        return v

    @field_validator("emp_type")
    @classmethod
    def validate_emp_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return "Contractual"
        v = v.strip()
        if v not in EMP_TYPE_VALUES:
            raise ValueError(f"emp_type must be one of {EMP_TYPE_VALUES}")
        return v

class EmployeeUpdate(BaseModel):
    emp_name: str
    gender: Optional[str] = None
    dob: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    join_date: Optional[str] = None

    desig_id: Optional[str] = None
    br_id: Optional[str] = None
    zone_id: Optional[str] = None
    org_id: Optional[str] = None
    group_id: Optional[str] = None

    nid: Optional[str] = None
    blood_group: Optional[str] = None
    address: Optional[str] = None
    emergency_phone: Optional[str] = None
    photo_url: Optional[str] = None

    status: Optional[str] = "active"

    # NEW
    emp_type: Optional[str] = "Contractual"
    bio: Optional[str] = None
    linkedin_url: Optional[str] = None
    sort_order: Optional[int] = None
    bio_details: Optional[str] = None

    @field_validator("emp_type")
    @classmethod
    def validate_emp_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return "Contractual"
        v = v.strip()
        if v not in EMP_TYPE_VALUES:
            raise ValueError(f"emp_type must be one of {EMP_TYPE_VALUES}")
        return v