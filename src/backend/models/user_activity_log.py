#src/backend/models/user_activity_log.py
from __future__ import annotations

from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, Float, JSON, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.backend.utils.database import Base

class UserActivityLog(Base):
    __tablename__ = "user_activity_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True,autoincrement=True)

    # FK -> user_info.login_id
    login_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("user_info.login_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )

    event_type:          Mapped[str]  = mapped_column(String(50),  nullable=False)
    ip_address:          Mapped[str]  = mapped_column(String(45),  nullable=True)
    device_info:         Mapped[str]  = mapped_column(String(255), nullable=True)
    user_agent:          Mapped[str]  = mapped_column(String(512), nullable=True)
    geolocation_city:    Mapped[str]  = mapped_column(String(100), nullable=True)
    geolocation_country: Mapped[str]  = mapped_column(String(100), nullable=True)
    login_success:       Mapped[bool] = mapped_column(Boolean, default=True)
    risk_score:          Mapped[float]= mapped_column(Float, default=0.0)
    extra_info:          Mapped[dict] = mapped_column(JSON, default=dict)

    create_dt:           Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    update_dt:           Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    user = relationship("User", backref="activity_logs")
