from pydantic import BaseModel

class OrgOut(BaseModel):
    org_id: str
    org_name: str

    class Config:
        from_attributes = True  # very important


class ZoneOut(BaseModel):
    zone_id: str
    zone_name: str


class BranchOut(BaseModel):
    br_id: str
    br_name: str


class DesigOut(BaseModel):
    desig_id: str
    desig_name: str
