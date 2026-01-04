# src/backend/crud/award.py

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, delete, func
from src.backend.models.ops.award_info import AwardInfo
from src.backend.schemas.award_schema import AwardCreate, AwardUpdate

# -------- Get one award --------
async def get_award(db: AsyncSession, award_id: int) -> Optional[AwardInfo]:
    stmt = select(AwardInfo).where(AwardInfo.id == award_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

# -------- List awards --------
async def list_awards(
    db: AsyncSession,
    q: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> List[AwardInfo]:
    stmt = select(AwardInfo).order_by(
        AwardInfo.id.asc(),
        AwardInfo.displaying_order.asc(),
    )
    if q:
        stmt = stmt.where(AwardInfo.title.ilike(f"%{q}%"))

    result = await db.execute(stmt.limit(limit).offset(offset))
    return list(result.scalars().all())

# -------- Count awards (for pagination) --------
async def get_total_awards_count(db: AsyncSession, q: Optional[str] = None) -> int:
    stmt = select(func.count(AwardInfo.id)).where(AwardInfo.published == "Yes")

    if q:
        stmt = stmt.where(AwardInfo.title.ilike(f"%{q}%"))

    result = await db.execute(stmt)
    return result.scalar_one() or 0

# -------- Create award --------
async def create_award(
    db: AsyncSession,
    award: AwardCreate,
    created_by: str = "System",
) -> AwardInfo:
    """Create a new award from the provided schema."""
    row = AwardInfo(
        title=award.title,
        issuer=award.issuer,
        year=award.year,
        description=award.description,
        image_url=award.image_url or "",
        published=award.published or "No",
        created_by=created_by,
        updated_by=created_by,
        displaying_order=award.displaying_order or 0,
    )

    db.add(row)
    try:
        await db.commit()
        await db.refresh(row)
    except IntegrityError:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise

    return row

# -------- Update award --------
async def update_award(
    db: AsyncSession,
    award_id: int,
    award: AwardUpdate,
    updated_by: str = "System",
) -> Optional[AwardInfo]:
    award_info = await get_award(db, award_id)
    if not award_info:
        return None

    award_info.title = award.title
    award_info.issuer = award.issuer
    award_info.year = award.year
    award_info.description = award.description
    award_info.image_url = award.image_url
    award_info.published = award.published or "No"
    award_info.displaying_order = award.displaying_order or 0
    award_info.updated_by = updated_by

    try:
        await db.commit()
        await db.refresh(award_info)
    except IntegrityError:
        await db.rollback()
        raise
    return award_info

# -------- Delete award --------
async def delete_award(db: AsyncSession, award_id: int) -> bool:
    stmt = delete(AwardInfo).where(AwardInfo.id == award_id)
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount > 0