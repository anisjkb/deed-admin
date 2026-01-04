# src/backend/models/org/br_info.py
from __future__ import annotations
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from src.backend.utils.timezone import now_local
from src.backend.utils.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship

class BranchInfo(Base):
    __tablename__ = "br_info"

    br_id: Mapped[str] = mapped_column(String(7), primary_key=True)  # e.g., 1101001
    zone_id: Mapped[str] = mapped_column(
        String(12), ForeignKey("zone_info.zone_id", ondelete="RESTRICT"), nullable=False
    )
    br_name: Mapped[str] = mapped_column(String(150), nullable=False)
    br_address: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str | None] = mapped_column(String(20), default="active")
    created_by = Column(String(50), nullable=True)
    created_dt = Column(DateTime(timezone=True), default=now_local, nullable=False)
    updated_by = Column(String(50), nullable=True)
    updated_dt = Column(DateTime(timezone=True), default=now_local, onupdate=now_local, nullable=False)

    # Relationships
    zone = relationship("ZoneInfo", back_populates="branches", lazy="joined")

    def __repr__(self) -> str:
        return f"<BranchInfo {self.br_id} {self.br_name}>"

