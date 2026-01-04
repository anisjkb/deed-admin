# src/backend/models/security/right.py
from sqlalchemy import Date,Column, String, CHAR, DateTime, PrimaryKeyConstraint, text, func
from src.backend.utils.database import Base
from src.backend.utils.timezone import now_local

class Right(Base):
    __tablename__ = "rights"
    __table_args__ = (PrimaryKeyConstraint("role_id", "menu_id"),)

    role_id       = Column(String(2), nullable=False)
    menu_id       = Column(String(2), nullable=False)

    create_permit = Column(CHAR(1), nullable=False, server_default=text("'N'"))
    view_permit   = Column(CHAR(1), nullable=False, server_default=text("'N'"))
    edit_permit   = Column(CHAR(1), nullable=False, server_default=text("'N'"))
    delete_permit = Column(CHAR(1), nullable=False, server_default=text("'N'"))

    status        = Column(String(20), nullable=True, server_default=text("'active'"))
    created_by  = Column(String(20), nullable=True)
    created_dt = Column(DateTime(timezone=True), default=now_local, nullable=False)
    updated_by  = Column(String(20), nullable=True)
    updated_dt = Column(DateTime(timezone=True), default=now_local, onupdate=now_local, nullable=False)

