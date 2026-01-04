# src/backend/models/org/zone_info.py
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from src.backend.utils.timezone import now_local
from src.backend.utils.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship

class ZoneInfo(Base):
    __tablename__ = "zone_info"

    zone_id: Mapped[str] = mapped_column(String(12), primary_key=True)  # e.g., 1101
    org_id: Mapped[str] = mapped_column(
        String(12), ForeignKey("org_info.org_id", ondelete="RESTRICT"), nullable=False
    )
    zone_name: Mapped[str] = mapped_column(String(150), nullable=False)
    zone_address: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str | None] = mapped_column(String(20), default="active")
    created_by = Column(String(50), nullable=True)
    created_dt = Column(DateTime(timezone=True), default=now_local, nullable=False)
    updated_by = Column(String(50), nullable=True)
    updated_dt = Column(DateTime(timezone=True), default=now_local, onupdate=now_local, nullable=False)
    # Relationships
    org = relationship("OrgInfo", back_populates="zones", lazy="joined")
    branches = relationship("BranchInfo", back_populates="zone", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self) -> str:
        return f"<ZoneInfo {self.zone_id} {self.zone_name}>"