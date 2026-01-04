# src/backend/schemas/menu.py
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, Literal

# Flags we expect to be "Y"/"N"
YN = Literal["Y", "N"]

class MenuBase(BaseModel):
    menu_name: Optional[str] = None
    parent_id: Optional[str] = None          # "0" or None => root (we normalize)
    is_parents: Optional[YN] = "N"           # "Y"/"N"
    url: Optional[str] = None
    menu_order: Optional[int] = 0
    font_awesome_icon: Optional[str] = None
    f_awesome_icon_css: Optional[str] = None
    active_flag: Optional[YN] = "Y"          # "Y"/"N"
    status: Optional[str] = "active"         # keep open or use Literal["active","inactive"]

    @field_validator("is_parents", "active_flag", mode="before")
    @classmethod
    def upper_flags(cls, v: Optional[str]):
        # Accepts None/empty and coerces to uppercase "Y"/"N" or None
        v = (v or "").strip().upper()
        return v or None

    @field_validator("parent_id", mode="before")
    @classmethod
    def normalize_parent(cls, v: Optional[str]):
        # Coerce empty -> "0" so you have a consistent "root" marker
        v = (v or "").strip()
        return v if v else "0"


class MenuCreate(MenuBase):
    menu_id: str

    @field_validator("menu_id", mode="before")
    @classmethod
    def normalize_menu_id(cls, v: str):
        return (v or "").strip()


class MenuUpdate(MenuBase):
    # No extra fields; partial update semantics decided by your handler
    pass


class MenuOut(MenuBase):
    menu_id: str
    # Pydantic v2: enable ORM attribute loading (SQLAlchemy -> Pydantic)
    model_config = ConfigDict(from_attributes=True)