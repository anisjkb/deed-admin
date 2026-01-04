# src/backend/models/ops/banner_info.py
from sqlalchemy import Column, DateTime, Integer, String, Boolean
from sqlalchemy.sql import func
from src.backend.utils.database import Base

class BannerInfo(Base):
    __tablename__ = 'banners'

    id = Column(Integer, primary_key=True, autoincrement=True)
    image_url = Column(String(500), nullable=False)
    headline = Column(String(200), nullable=True)
    subhead = Column(String(300), nullable=True)
    cta_text = Column(String(64), nullable=True)
    cta_url = Column(String(300), nullable=True)
    sort_order = Column(Integer, nullable=False)
    created_by = Column(String(50), nullable=True)
    created_dt = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_by = Column(String(50), nullable=True)
    updated_dt = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
    is_active = Column(Boolean, nullable=False)
    
    # New field to manage published status
    published = Column(String(3), default='Yes', nullable=False)  # Default is 'Yes'

    def __repr__(self):
        return f"<BannerInfo {self.id} {self.headline}>"