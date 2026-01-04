# src/backend/models/ops/feedback.py
from typing import Optional
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, Text, Index, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

# Shared async Base
from src.backend.utils.database import Base


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = (
        Index("idx_feedback_created", "created_at"),
        Index("idx_feedback_unread", "is_read", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(40), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Feedback {self.id} {self.name}>"