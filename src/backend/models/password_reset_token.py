from __future__ import annotations

from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.backend.utils.database import Base

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # FK -> user_info.login_id
    login_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("user_info.login_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )

    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    created_by: Mapped[str | None] = mapped_column(String(8), nullable=True)
    create_dt:  Mapped[datetime]   = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_by: Mapped[str | None] = mapped_column(String(8), nullable=True)
    update_dt:  Mapped[datetime]   = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user = relationship("User", back_populates="reset_tokens")

    def __repr__(self) -> str:
        return f"<PasswordResetToken id={self.id} login_id={self.login_id}>"
