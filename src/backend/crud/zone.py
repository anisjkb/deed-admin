# src/backend/crud/zone.py
from typing import Optional, Tuple, List
from sqlalchemy import select, or_, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.models.org.zone_info import ZoneInfo
from src.backend.models.org.org_info import OrgInfo
from src.backend.schemas.zone import ZoneCreate, ZoneUpdate
from src.backend.utils.timezone import now_local

def _normalize_status(v: Optional[str]) -> str:
    return (v or "active").strip().lower()

async def list_zones(
    db: AsyncSession,
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[list[ZoneInfo], int]:
    base = select(ZoneInfo)
    if q:
        like = f"%{q.strip()}%"
        base = base.where(
            or_(
                ZoneInfo.zone_id.ilike(like),
                ZoneInfo.zone_name.ilike(like),
                ZoneInfo.zone_address.ilike(like),
                ZoneInfo.status.ilike(like),
            )
        )
    base = base.order_by(ZoneInfo.zone_id)
    count_stmt = base.with_only_columns(ZoneInfo.zone_id).order_by(None)
    res = await db.execute(count_stmt)
    total = len(res.scalars().all())

    page_stmt = base.limit(limit).offset(offset)
    res2 = await db.execute(page_stmt)
    rows = list(res2.scalars().all())
    return rows, total

async def list_orgs_for_dropdown(db: AsyncSession) -> List[OrgInfo]:
    res = await db.execute(
        select(OrgInfo).where(OrgInfo.status == "active").order_by(OrgInfo.org_id)
    )
    return list(res.scalars().all())

async def get_zone(db: AsyncSession, zone_id: str) -> Optional[ZoneInfo]:
    res = await db.execute(select(ZoneInfo).where(ZoneInfo.zone_id == zone_id))
    return res.scalar_one_or_none()

async def create_zone(db: AsyncSession, data: ZoneCreate, created_by: str = "System") -> ZoneInfo:
    row = ZoneInfo(
        zone_id=data.zone_id.strip(),
        org_id=data.org_id.strip(),
        zone_name=(data.zone_name or "").strip(),
        zone_address=(data.zone_address or "").strip(),
        status=_normalize_status(data.status),
        created_by=created_by,
        updated_by=created_by,
        created_dt=now_local(),
        updated_dt=now_local(),
    )
    db.add(row)
    try:
        await db.commit()
        await db.refresh(row)
    except IntegrityError:
        await db.rollback()
        raise
    return row

async def update_zone(db: AsyncSession, zone_id: str, data: ZoneUpdate, updated_by: str = "System") -> Optional[ZoneInfo]:
    row = await get_zone(db, zone_id)
    if not row:
        return None
    row.org_id = data.org_id.strip()
    row.zone_name = (data.zone_name or "").strip()
    row.zone_address = (data.zone_address or "").strip()
    row.status = _normalize_status(data.status)
    row.updated_by = updated_by
    row.updated_dt = now_local()
    try:
        await db.commit()
        await db.refresh(row)
    except IntegrityError:
        await db.rollback()
        raise
    return row

async def delete_zone(db: AsyncSession, zone_id: str) -> bool:
    # Child check happens in route (branches exist?)
    await db.execute(delete(ZoneInfo).where(ZoneInfo.zone_id == zone_id))
    await db.commit()
    return True

# -------- Auto-ID helper --------
async def next_zone_id(db: AsyncSession, org_id: str) -> str:
    """
    zone_id = <org_id> + 2-digit running number (01, 02, ...)
    For org 11: 1101, 1102, ...
    """
    res = await db.execute(select(ZoneInfo.zone_id).where(ZoneInfo.org_id == org_id))
    zone_ids = [x for x in res.scalars().all() if x and x.startswith(org_id)]
    suffixes = []
    for zid in zone_ids:
        sfx = zid[len(org_id):]
        if sfx.isdigit():
            suffixes.append(int(sfx))
    next_num = (max(suffixes) + 1) if suffixes else 1
    return f"{org_id}{next_num:02d}"
