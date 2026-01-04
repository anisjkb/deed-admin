# src/backend/schemas/master/desig.py
from pydantic import BaseModel

class DesigCreate(BaseModel):
    # desig_id is auto-generated; not part of create payload
    desig_name: str
    status: str | None = "active"

class DesigUpdate(BaseModel):
    desig_name: str
    status: str | None = "active"
