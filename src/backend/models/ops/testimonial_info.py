# src/backend/models/ops/testimonial_info.py
from sqlalchemy import Column, DateTime, Integer, String, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class TestimonialInfo(Base):
    __tablename__ = "testimonials"

    # Table Columns
    id = Column(Integer, primary_key=True, autoincrement=True)  # Auto incrementing primary key
    name = Column(String(120), nullable=False)  # Name of the person giving the testimonial
    role = Column(String(120))  # Role of the person (e.g., Homeowner, Landowner)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)  # Reference to the project
    project_title = Column(String(160))  # Project title associated with the testimonial
    quote = Column(Text, nullable=False)  # The testimonial text/quote
    video_url = Column(String(500))  # URL to a video testimonial if available
    sort_order = Column(Integer, default=0)  # Ordering value for display
    published = Column(String(3), default='Yes')  # Published status: Yes or No
    created_dt = Column(DateTime(timezone=True), default=func.now(), nullable=False)  # renamed from created_at
    created_by = Column(String(20))  # Who created this testimonial
    # Timestamps using func.now() for automatic handling
    updated_dt = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)  # renamed from updated_at
    updated_by = Column(String(20))  # Last person who updated it

    # Relationship to the projects table (assuming you have a Project model)
    project = relationship("Project", back_populates="testimonials")

    def __repr__(self):
        return f"<TestimonialInfo(id={self.id}, name={self.name}, project_title={self.project_title})>"

# Assuming you already have the `Project` model defined
class Project(Base):
    __tablename__ = "projects"
    
    # Columns for the projects table
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(120), nullable=False)
    testimonials = relationship("TestimonialInfo", back_populates="project")