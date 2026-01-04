# src/backend/models/refresh_token.py
from __future__ import annotations

from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime, Boolean, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.backend.utils.database import Base

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    # FK -> user_info.login_id
    login_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("user_info.login_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )

    token_hash:  Mapped[str]  = mapped_column(String(255), nullable=False, index=True)
    device_info: Mapped[str]  = mapped_column(String(255), nullable=True)
    ip_address:  Mapped[str]  = mapped_column(String(45),  nullable=True)  # ipv4/ipv6
    expires_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    session_start: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    is_revoked:  Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_by: Mapped[str | None] = mapped_column(String(20), nullable=True)
    create_dt:  Mapped[datetime]   = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_by: Mapped[str | None] = mapped_column(String(20), nullable=True)
    update_dt:  Mapped[datetime]   = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    user = relationship("User", backref="refresh_tokens")
