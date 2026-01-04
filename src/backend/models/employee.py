# src/backend/models/employee.py
from sqlalchemy import Column, String, CHAR, Date
from src.backend.utils.database import Base
from src.backend.utils.timezone import today_local

class Employee(Base):
    __tablename__ = "emp_info"

    emp_id     = Column(String(20), primary_key=True)
    emp_name   = Column(String(100), nullable=False)
    emp_type   = Column(String(50), nullable=False)
    mobile     = Column(String(15), nullable=True)
    email      = Column(String(100), nullable=True)
    desig_id   = Column(String(10), nullable=True)
    zone_id    = Column(String(10), nullable=True)
    br_id      = Column(String(10), nullable=True)
    status     = Column(CHAR(1), default="A")
    created_by = Column(String(20), nullable=True)
    create_dt  = Column(Date, default=today_local, nullable=False)
    updated_by = Column(String(20), nullable=True)
    update_dt  = Column(Date, default=today_local, nullable=False)