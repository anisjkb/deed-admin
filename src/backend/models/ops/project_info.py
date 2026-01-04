# src/backend/models/ops/project_info.py
from __future__ import annotations

from enum import Enum
from datetime import date, datetime
from typing import Optional

from sqlalchemy import String, Integer, Date, DateTime, JSON
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class ProjectStatus(str, Enum):
    ongoing = "ongoing"
    upcoming = "upcoming"
    completed = "completed"

class ProjectType(str, Enum):
    residential = "residential"
    commercial = "commercial"

class ProjectInfo(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    tagline: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    status: Mapped[ProjectStatus] = mapped_column(
        postgresql.ENUM(ProjectStatus, name="projectstatus", create_type=False),
        nullable=False,
        server_default=ProjectStatus.ongoing.value,
    )

    ptype: Mapped[ProjectType] = mapped_column(
        postgresql.ENUM(ProjectType, name="projecttype", create_type=False),
        nullable=False,
        server_default=ProjectType.residential.value,
    )

    location: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    land_area_sft: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    floors: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    units_total: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    parking_spaces: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    frontage_ft: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    orientation: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    size_range: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    specs_json: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")

    brochure_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    hero_image_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    video_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    short_desc: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    highlights: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    partners: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    handover_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    progress_pct: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    br_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    emp_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    created_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    updated_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    published: Mapped[Optional[str]] = mapped_column(String(3), default="Yes", nullable=True)