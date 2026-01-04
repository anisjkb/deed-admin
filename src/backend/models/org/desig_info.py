# src/backend/models/org/desig_info.py
from __future__ import annotations
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime,Column
from src.backend.utils.database import Base
from src.backend.utils.timezone import now_local

class DesigInfo(Base):
    __tablename__ = "desig_info"

    desig_id: Mapped[str]      = mapped_column(String(2), primary_key=True)  # "01", "02", ...
    desig_name: Mapped[str]    = mapped_column(String(50), nullable=False)
    status: Mapped[str | None] = mapped_column(String(20), default="active")

    created_by = Column(String(50), nullable=True)
    created_dt = Column(DateTime(timezone=True), default=now_local, nullable=False)
    updated_by = Column(String(50), nullable=True)
    updated_dt = Column(DateTime(timezone=True), default=now_local, onupdate=now_local, nullable=False)

    def __repr__(self) -> str:
        return f"<DesigInfo {self.desig_id} {self.desig_name}>"
