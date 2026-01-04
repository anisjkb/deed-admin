# src/backend/schemas/project.py
from pydantic import BaseModel, field_validator, ConfigDict
from typing import Optional

# Allowed values for project status and project type
_ALLOWED_STATUS = {"ongoing", "upcoming", "completed"}
_ALLOWED_PTYPE = {"residential", "commercial"}


def _blank_to_none(v):
    if v is None:
        return None
    if isinstance(v, str):
        v = v.strip()
        if v == "":
            return None
    return v


class ProjectBase(BaseModel):
    slug: str
    title: str  # 'name' replaced by 'title'
    tagline: Optional[str] = None

    status: Optional[str] = "ongoing"
    ptype: Optional[str] = "residential"
    location: Optional[str] = None

    # Metrics
    progress_pct: Optional[int] = 0
    handover_date: Optional[str] = None  # 'YYYY-MM-DD' as string, parsed in CRUD

    # Dimensions
    land_area_sft: Optional[int] = None
    floors: Optional[int] = None
    units_total: Optional[int] = None
    parking_spaces: Optional[int] = None
    frontage_ft: Optional[int] = None
    orientation: Optional[str] = None
    size_range: Optional[str] = None

    # Media URLs (just strings, final paths after upload)
    hero_image_url: Optional[str] = None
    brochure_url: Optional[str] = None
    video_url: Optional[str] = None

    # Copy
    short_desc: Optional[str] = None
    highlights: Optional[str] = None
    partners: Optional[str] = None

    # Metadata
    br_id: Optional[str] = None
    emp_id: Optional[str] = None
    published: Optional[str] = None  # "Yes" / "No"

    model_config = ConfigDict(str_strip_whitespace=True)

    # --- Validators ---

    @field_validator("status")
    @classmethod
    def v_status(cls, v: str):
        v = (v or "ongoing").lower()
        if v not in _ALLOWED_STATUS:
            raise ValueError(f"status must be one of {sorted(_ALLOWED_STATUS)}")
        return v

    @field_validator("ptype")
    @classmethod
    def v_ptype(cls, v: str):
        v = (v or "residential").lower()
        if v not in _ALLOWED_PTYPE:
            raise ValueError(f"ptype must be one of {sorted(_ALLOWED_PTYPE)}")
        return v

    # Coerce blank strings to None for numeric fields
    @field_validator(
        "land_area_sft",
        "floors",
        "units_total",
        "parking_spaces",
        "frontage_ft",
        mode="before",
    )
    @classmethod
    def blank_to_none_numbers(cls, v):
        return _blank_to_none(v)

    # Handle 'progress_pct' as string/number and convert to int
    @field_validator("progress_pct", mode="before")
    @classmethod
    def v_progress_before(cls, v):
        v = _blank_to_none(v)
        if v is None:
            return 0
        return v  # Pydantic will coerce to int


class ProjectCreate(ProjectBase):
    """
    Used for initial insert.
    File uploads are handled in routes, so this only carries URLs/values.
    """
    pass


class ProjectUpdate(BaseModel):
    """
    Used for updates.
    All fields optional so we can do partial updates.
    Routes usually send everything, but 'exclude_unset' in CRUD is also supported.
    """
    slug: Optional[str] = None
    title: Optional[str] = None
    tagline: Optional[str] = None

    status: Optional[str] = None
    ptype: Optional[str] = None
    location: Optional[str] = None

    progress_pct: Optional[int] = None
    handover_date: Optional[str] = None

    land_area_sft: Optional[int] = None
    floors: Optional[int] = None
    units_total: Optional[int] = None
    parking_spaces: Optional[int] = None
    frontage_ft: Optional[int] = None
    orientation: Optional[str] = None
    size_range: Optional[str] = None

    hero_image_url: Optional[str] = None
    brochure_url: Optional[str] = None
    video_url: Optional[str] = None

    short_desc: Optional[str] = None
    highlights: Optional[str] = None
    partners: Optional[str] = None

    br_id: Optional[str] = None
    emp_id: Optional[str] = None
    published: Optional[str] = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("status")
    @classmethod
    def v_status(cls, v: Optional[str]):
        if v is None:
            return v
        v2 = v.lower()
        if v2 not in _ALLOWED_STATUS:
            raise ValueError(f"status must be one of {sorted(_ALLOWED_STATUS)}")
        return v2

    @field_validator("ptype")
    @classmethod
    def v_ptype(cls, v: Optional[str]):
        if v is None:
            return v
        v2 = v.lower()
        if v2 not in _ALLOWED_PTYPE:
            raise ValueError(f"ptype must be one of {sorted(_ALLOWED_PTYPE)}")
        return v2

    @field_validator(
        "land_area_sft",
        "floors",
        "units_total",
        "parking_spaces",
        "frontage_ft",
        mode="before",
    )
    @classmethod
    def blank_to_none_numbers(cls, v):
        return _blank_to_none(v)

    @field_validator("progress_pct", mode="before")
    @classmethod
    def v_progress_before(cls, v):
        v = _blank_to_none(v)
        if v is None:
            return None
        return v  # Pydantic will coerce to int