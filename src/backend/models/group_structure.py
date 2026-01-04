# src/backend/models/group_structure.py
# for group_info, org_info, zone_info, and br_info, defining hierarchical relationships
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.backend.utils.timezone import now_local
from src.backend.utils.database import Base


# -----------------------------
# 1️⃣ Group Info Table
# -----------------------------
class GroupInfo(Base):
    __tablename__ = "group_info"

    group_id = Column(Integer, primary_key=True, autoincrement=True)
    group_name = Column(String(100), nullable=False)
    group_address = Column(String(255), nullable=True)
    group_logo = Column(String(255), nullable=True)
    status = Column(String(20), default="active")
    created_by = Column(String(50), nullable=True)
    created_dt = Column(DateTime(timezone=True), default=now_local, nullable=False)
    updated_by = Column(String(50), nullable=True)
    updated_dt = Column(DateTime(timezone=True), default=now_local, onupdate=now_local, nullable=False)

    # Relationships
    orgs = relationship("OrgInfo", back_populates="group", cascade="all, delete-orphan")


# -----------------------------
# 2️⃣ Organization Info Table
# -----------------------------
class OrgInfo(Base):
    __tablename__ = "org_info"

    org_id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("group_info.group_id"), nullable=False)
    org_name = Column(String(100), nullable=False)
    org_address = Column(String(255), nullable=True)
    org_logo = Column(String(255), nullable=True)
    status = Column(String(20), default="active")
    created_by = Column(String(50), nullable=True)
    created_dt = Column(DateTime(timezone=True), default=now_local, nullable=False)
    updated_by = Column(String(50), nullable=True)
    updated_dt = Column(DateTime(timezone=True), default=now_local, onupdate=now_local, nullable=False)

    # Relationships
    group = relationship("GroupInfo", back_populates="orgs")
    zones = relationship("ZoneInfo", back_populates="org", cascade="all, delete-orphan")


# -----------------------------
# 3️⃣ Zone Info Table
# -----------------------------
class ZoneInfo(Base):
    __tablename__ = "zone_info"

    zone_id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("org_info.org_id"), nullable=False)
    zone_name = Column(String(100), nullable=False)
    zone_address = Column(String(255), nullable=True)
    status = Column(String(20), default="active")
    created_by = Column(String(50), nullable=True)
    created_dt = Column(DateTime(timezone=True), default=now_local, nullable=False)
    updated_by = Column(String(50), nullable=True)
    updated_dt = Column(DateTime(timezone=True), default=now_local, onupdate=now_local, nullable=False)

    # Relationships
    org = relationship("OrgInfo", back_populates="zones")
    branches = relationship("BranchInfo", back_populates="zone", cascade="all, delete-orphan")


# -----------------------------
# 4️⃣ Branch Info Table
# -----------------------------
class BranchInfo(Base):
    __tablename__ = "br_info"

    br_id = Column(String(7), primary_key=True)
    zone_id = Column(Integer, ForeignKey("zone_info.zone_id"), nullable=False)
    br_name = Column(String(100), nullable=False)
    br_address = Column(String(255), nullable=True)
    status = Column(String(20), default="active")
    created_by = Column(String(50), nullable=True)
    created_dt = Column(DateTime(timezone=True), default=now_local, nullable=False)
    updated_by = Column(String(50), nullable=True)
    updated_dt = Column(DateTime(timezone=True), default=now_local, onupdate=now_local, nullable=False)

    # Relationships
    zone = relationship("ZoneInfo", back_populates="branches")
