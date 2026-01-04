# src/backend/models/user.py
from sqlalchemy import Column, String, Date, CHAR
from sqlalchemy.orm import relationship
from src.backend.utils.database import Base
from src.backend.utils.timezone import today_local
from sqlalchemy.orm import Mapped, mapped_column

class User(Base):
    __tablename__ = "user_info"

    emp_id: Mapped[str] = mapped_column(String(20), nullable=False)
    login_id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)
    role_id: Mapped[str] = mapped_column(String(2), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(CHAR(1), default="A")
    created_by: Mapped[str | None] = mapped_column(String(20), nullable=True)
    create_dt: Mapped[Date] = mapped_column(
        Date,
        default=today_local,
        nullable=False,
    )
    updated_by: Mapped[str | None] = mapped_column(String(20), nullable=True)
    update_dt: Mapped[Date] = mapped_column(
        Date,
        default=today_local,
        nullable=False,
    )

    # 1-to-many to tokens via login_id
    reset_tokens = relationship(
        "PasswordResetToken",
        back_populates="user",
        cascade="all, delete-orphan",
        primaryjoin="User.login_id==PasswordResetToken.login_id",
    )
