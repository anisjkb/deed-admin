# src/backend/crud/banner.py
from __future__ import annotations

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from sqlalchemy.exc import IntegrityError

from src.backend.models.ops.banner_info import BannerInfo
from src.backend.schemas.banner_schema import BannerCreate, BannerUpdate
from src.backend.utils.timezone import now_local

logger = logging.getLogger(__name__)


# -------- Get one banner --------
async def get_banner(db: AsyncSession, banner_id: int) -> BannerInfo | None:
    stmt = select(BannerInfo).where(BannerInfo.id == banner_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# -------- List banners --------
async def list_banners(
    db: AsyncSession,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[BannerInfo]:
    stmt = select(BannerInfo)

    if q:
        stmt = stmt.where(BannerInfo.headline.ilike(f"%{q.strip()}%"))

    # sort_order first (your UI expects this), then id stable tie-break
    stmt = stmt.order_by(BannerInfo.sort_order.asc(), BannerInfo.id.asc())

    result = await db.execute(stmt.limit(limit).offset(offset))
    return list(result.scalars().all())


# ✅ -------- Count banners (for pagination) --------
async def get_total_banners_count(db: AsyncSession, q: str | None = None) -> int:
    # COUNT(*) query must return exactly one row
    stmt = select(func.count()).select_from(BannerInfo)

    if q:
        stmt = stmt.where(BannerInfo.headline.ilike(f"%{q.strip()}%"))

    result = await db.execute(stmt)
    total = result.scalar_one()
    return int(total or 0)


# -------- Create banner --------
async def create_banner(
    db: AsyncSession,
    banner: BannerCreate,
    created_by: str = "System",
) -> BannerInfo:
    row = BannerInfo(
        image_url=banner.image_url,
        headline=banner.headline,
        subhead=banner.subhead,
        cta_text=banner.cta_text,
        cta_url=banner.cta_url,
        sort_order=banner.sort_order,
        is_active=banner.is_active,
        published=banner.published or "Yes",
        created_by=created_by,
        updated_by=created_by,
        created_dt=now_local(),
        updated_dt=now_local(),
    )

    db.add(row)
    try:
        await db.commit()
        await db.refresh(row)
    except IntegrityError as e:
        await db.rollback()
        logger.error("Integrity error while creating banner: %s", e)
        raise

    return row


# -------- Update banner --------
async def update_banner(
    db: AsyncSession,
    banner_id: int,
    banner: BannerUpdate,
    updated_by: str = "System",
) -> BannerInfo | None:
    banner_info = await get_banner(db, banner_id)
    if not banner_info:
        return None

    update_data = {
        "image_url": banner.image_url if banner.image_url is not None else banner_info.image_url,
        "headline": banner.headline if banner.headline is not None else banner_info.headline,
        "subhead": banner.subhead if banner.subhead is not None else banner_info.subhead,
        "cta_text": banner.cta_text if banner.cta_text is not None else banner_info.cta_text,
        "cta_url": banner.cta_url if banner.cta_url is not None else banner_info.cta_url,
        "sort_order": banner.sort_order if banner.sort_order is not None else banner_info.sort_order,
        "is_active": banner.is_active if banner.is_active is not None else banner_info.is_active,
        "published": banner.published if banner.published is not None else banner_info.published,
        "updated_by": updated_by,
        "updated_dt": now_local(),
    }

    try:
        await db.execute(
            BannerInfo.__table__.update()
            .where(BannerInfo.id == banner_id)
            .values(**update_data)
        )
        await db.commit()
        await db.refresh(banner_info)
    except IntegrityError as e:
        await db.rollback()
        logger.error("Integrity error while updating banner: %s", e)
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Unexpected error while updating banner: %s", e)
        raise

    return banner_info


# -------- Delete banner --------
async def delete_banner(db: AsyncSession, banner_id: int) -> bool:
    stmt = delete(BannerInfo).where(BannerInfo.id == banner_id)
    result = await db.execute(stmt)
    await db.commit()
    return (result.rowcount or 0) > 0