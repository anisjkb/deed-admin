# src/backend/models/security/role.py
from sqlalchemy import Column, String, Date, text
from sqlalchemy.schema import PrimaryKeyConstraint
from src.backend.utils.database import Base
from src.backend.utils.timezone import today_local

class Role(Base):
    __tablename__ = "roles"
    __table_args__ = (PrimaryKeyConstraint("role_id"),)

    role_id    = Column(String(2),  nullable=False)
    role_name  = Column(String(50), nullable=False)
    status     = Column(String(20), nullable=True, server_default=text("'active'"))

    created_by = Column(String(50), nullable=True)
    created_dt = Column(Date, default=today_local, nullable=False)
    updated_by = Column(String(50), nullable=True)
    updated_dt = Column(Date, default=today_local, nullable=False)