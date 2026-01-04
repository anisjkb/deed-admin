# src/backend/models/org/emp_info.py
from __future__ import annotations

from datetime import date, datetime
from sqlalchemy import String, Date, DateTime, Text, ForeignKey, Integer, Enum
from sqlalchemy.orm import Mapped, mapped_column

from src.backend.utils.database import Base
from src.backend.utils.timezone import now_local

def _now_naive() -> datetime:
    dt = now_local()
    return dt.replace(tzinfo=None) if getattr(dt, "tzinfo", None) else dt

# Keep values in sync with DB enum "emp_type"
EMP_TYPE_VALUES = ("Contractual", "Permanent", "Management", "Board Member")

class EmpInfo(Base):
    __tablename__ = "emp_info"

    emp_id: Mapped[str] = mapped_column(String(6), primary_key=True)
    emp_name: Mapped[str] = mapped_column(String(100), nullable=False)
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)
    dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    mobile: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(80), nullable=True)
    join_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    desig_id: Mapped[str | None] = mapped_column(
        String(2), ForeignKey("desig_info.desig_id", onupdate="CASCADE", ondelete="SET NULL"), nullable=True
    )
    # 7 chars to match br_info.br_id like 1101001
    br_id: Mapped[str | None] = mapped_column(
        String(7), ForeignKey("br_info.br_id", onupdate="CASCADE", ondelete="SET NULL"), nullable=True
    )
    zone_id: Mapped[str | None] = mapped_column(
        String(4), ForeignKey("zone_info.zone_id", onupdate="CASCADE", ondelete="SET NULL"), nullable=True
    )
    org_id: Mapped[str | None] = mapped_column(
        String(4), ForeignKey("org_info.org_id", onupdate="CASCADE", ondelete="SET NULL"), nullable=True
    )
    group_id: Mapped[str | None] = mapped_column(
        String(4), ForeignKey("group_info.group_id", onupdate="CASCADE", ondelete="SET NULL"), nullable=True
    )

    nid: Mapped[str | None] = mapped_column(String(20), nullable=True)
    blood_group: Mapped[str | None] = mapped_column(String(5), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    emergency_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[str | None] = mapped_column(String(20), default="active")
    created_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_dt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=_now_naive)
    updated_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    updated_dt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=_now_naive)

    # NEW FIELDS (match your table)
    emp_type: Mapped[str | None] = mapped_column(
        Enum(*EMP_TYPE_VALUES, name="emp_type"), nullable=True, default="Contractual"
    )
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    sort_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bio_details: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<EmpInfo {self.emp_id} {self.emp_name}>"