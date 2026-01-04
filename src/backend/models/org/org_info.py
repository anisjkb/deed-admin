# src/backend/models/org/org_info.py
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from src.backend.utils.timezone import now_local
from src.backend.utils.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship

class OrgInfo(Base):
    __tablename__ = "org_info"

    org_id: Mapped[str] = mapped_column(String(12), primary_key=True)
    group_id: Mapped[str] = mapped_column(
        String(10), ForeignKey("group_info.group_id", ondelete="RESTRICT"), nullable=False
    )
    org_name: Mapped[str] = mapped_column(String(150), nullable=False)
    org_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    org_logo: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[str | None] = mapped_column(String(20), default="active")
    created_by = Column(String(50), nullable=True)
    created_dt = Column(DateTime(timezone=True), default=now_local, nullable=False)
    updated_by = Column(String(50), nullable=True)
    updated_dt = Column(DateTime(timezone=True), default=now_local, onupdate=now_local, nullable=False)

    group = relationship("GroupInfo", back_populates="orgs", lazy="joined")
    zones = relationship("ZoneInfo", back_populates="org", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self) -> str:
        return f"<OrgInfo {self.org_id} {self.org_name}>"
