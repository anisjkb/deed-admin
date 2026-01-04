# src/backend/crud/testimonial.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, delete
from src.backend.models.ops.testimonial_info import TestimonialInfo
from src.backend.schemas.testimonial_schema import TestimonialCreate, TestimonialUpdate
import logging
from fastapi import HTTPException
from src.backend.models.ops.project_info import ProjectInfo

from typing import List

# Set up logging
logger = logging.getLogger(__name__)

# -------- Get one testimonial --------
async def get_testimonial(db: AsyncSession, testimonial_id: int) -> TestimonialInfo | None:
    try:
        stmt = select(TestimonialInfo).where(TestimonialInfo.id == testimonial_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Error getting testimonial {testimonial_id}: {e}")
        raise HTTPException(status_code=500, detail="Error fetching testimonial")

# -------- List testimonials --------
async def list_testimonials(
    db: AsyncSession,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[TestimonialInfo]:
    try:
        stmt = select(TestimonialInfo).order_by(TestimonialInfo.id.asc())
        if q:
            stmt = stmt.where(TestimonialInfo.name.ilike(f"%{q}%"))
        stmt = stmt.order_by(TestimonialInfo.sort_order)
        result = await db.execute(stmt.limit(limit).offset(offset))
        return list(result.scalars().all())
    except Exception as e:
        logger.error(f"Error listing testimonials: {e}")
        raise HTTPException(status_code=500, detail="Error fetching testimonials")

# -------- Create testimonial --------
async def create_testimonial(db: AsyncSession, testimonial: TestimonialCreate, created_by: str = "System"):
    try:
        # Create new testimonial entry
        row = TestimonialInfo(
            name=testimonial.name,
            role=testimonial.role,
            project_id=testimonial.project_id,
            project_title=testimonial.project_title,
            quote=testimonial.quote,
            video_url=testimonial.video_url,
            sort_order=testimonial.sort_order,
            published=testimonial.published,
            created_by=created_by,
            updated_by=created_by,
        )

        db.add(row)
        await db.commit()
        await db.refresh(row)
        logger.debug(f"Testimonial created successfully: {row.id}")
        return row
    except IntegrityError as e:
        logger.error(f"Integrity error while creating testimonial: {e}")
        await db.rollback()
        raise HTTPException(status_code=400, detail="Integrity error while creating testimonial")
    except Exception as e:
        logger.error(f"Unexpected error while creating testimonial: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Unexpected error")

# -------- Update testimonial --------
async def update_testimonial(
    db: AsyncSession,
    testimonial_id: int,
    testimonial: TestimonialUpdate,
    updated_by: str = "System",
) -> TestimonialInfo | None:
    try:
        # Fetch the existing testimonial to update
        testimonial_info = await get_testimonial(db, testimonial_id)
        if not testimonial_info:
            raise HTTPException(status_code=404, detail="Testimonial not found")

        # Prepare the update data with column names as strings
        update_data = {
            "name": testimonial.name or testimonial_info.name,
            "role": testimonial.role or testimonial_info.role,
            "project_id": testimonial.project_id or testimonial_info.project_id,
            "project_title": testimonial.project_title or testimonial_info.project_title,
            "quote": testimonial.quote or testimonial_info.quote,
            "video_url": testimonial.video_url or testimonial_info.video_url,
            "sort_order": testimonial.sort_order or testimonial_info.sort_order,
            "published": testimonial.published or testimonial_info.published,
            "updated_by": updated_by,
        }

        # Update the testimonial record
        await db.execute(
            TestimonialInfo.__table__.update().where(TestimonialInfo.id == testimonial_id).values(**update_data)
        )
        await db.commit()
        await db.refresh(testimonial_info)
        return testimonial_info
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Integrity error while updating testimonial")
    except Exception as e:
        logger.error(f"Error while updating testimonial {testimonial_id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Unexpected error while updating testimonial")

# -------- Delete testimonial --------
async def delete_testimonial(db: AsyncSession, testimonial_id: int) -> bool:
    try:
        stmt = delete(TestimonialInfo).where(TestimonialInfo.id == testimonial_id)
        result = await db.execute(stmt)
        await db.commit()
        if result.rowcount > 0:
            logger.debug(f"Testimonial {testimonial_id} deleted successfully")
            return True
        else:
            raise HTTPException(status_code=404, detail="Testimonial not found")
    except Exception as e:
        logger.error(f"Error deleting testimonial {testimonial_id}: {e}")
        raise HTTPException(status_code=500, detail="Error deleting testimonial")
    
# ---------- Dropdown helpers ----------

async def list_projects(db: AsyncSession) -> List[ProjectInfo]:
    res = await db.execute(select(ProjectInfo).where(ProjectInfo.published == "Yes").order_by(ProjectInfo.title))
    return list(res.scalars().all())

# Fetch the project title by project_id
async def get_project_title_by_id(db: AsyncSession, project_id: int) -> str:
    try:
        stmt = select(ProjectInfo).where(ProjectInfo.id == project_id)
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()
        if project:
            return str(project.title)
        else:
            raise HTTPException(status_code=404, detail="Project not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching project: {e}")