# src/backend/models/org/group_info.py
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from src.backend.utils.timezone import now_local
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.backend.utils.database import Base

class GroupInfo(Base):
    __tablename__ = "group_info"

    group_id: Mapped[str] = mapped_column(String(10), primary_key=True)
    group_name: Mapped[str] = mapped_column(String(150), nullable=False)
    group_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    group_logo: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[str | None] = mapped_column(String(20), default="active")
    created_by = Column(String(50), nullable=True)
    created_dt = Column(DateTime(timezone=True), default=now_local, nullable=False)
    updated_by = Column(String(50), nullable=True)
    updated_dt = Column(DateTime(timezone=True), default=now_local, onupdate=now_local, nullable=False)

    # Optional: backref to orgs (not required by CRUD)
    orgs = relationship("OrgInfo", back_populates="group", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self) -> str:
        return f"<GroupInfo {self.group_id} {self.group_name}>"