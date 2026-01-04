# src/backend/models/ops/award_info.py
from typing import Optional
from datetime import datetime
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

# Use the shared Base from the project's async database module
from src.backend.utils.database import Base


class AwardInfo(Base):
    __tablename__ = 'awards'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    issuer: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(400), nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    published: Mapped[str] = mapped_column(String(3), default='No', nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_dt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
    )
    updated_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    updated_dt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    displaying_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<AwardInfo {self.id} {self.title}>"
