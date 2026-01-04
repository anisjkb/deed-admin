# src/backend/crud/branch.py
from typing import Optional, Tuple, List
from sqlalchemy import select, or_, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.models.org.br_info import BranchInfo
from src.backend.models.org.zone_info import ZoneInfo
from src.backend.schemas.branch import BranchCreate, BranchUpdate
from src.backend.utils.timezone import now_local

def _normalize_status(v: Optional[str]) -> str:
    return (v or "active").strip().lower()

async def list_branches(
    db: AsyncSession,
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[list[BranchInfo], int]:
    base = select(BranchInfo)
    if q:
        like = f"%{q.strip()}%"
        base = base.where(
            or_(
                BranchInfo.br_id.ilike(like),
                BranchInfo.br_name.ilike(like),
                BranchInfo.br_address.ilike(like),
                BranchInfo.status.ilike(like),
            )
        )
    base = base.order_by(BranchInfo.br_id)
    count_stmt = base.with_only_columns(BranchInfo.br_id).order_by(None)
    res = await db.execute(count_stmt)
    total = len(res.scalars().all())

    page_stmt = base.limit(limit).offset(offset)
    res2 = await db.execute(page_stmt)
    rows = list(res2.scalars().all())
    return rows, total

async def list_zones_for_dropdown(db: AsyncSession) -> List[ZoneInfo]:
    res = await db.execute(
        select(ZoneInfo).where(ZoneInfo.status == "active").order_by(ZoneInfo.zone_id)
    )
    return list(res.scalars().all())

async def get_branch(db: AsyncSession, br_id: str) -> Optional[BranchInfo]:
    res = await db.execute(select(BranchInfo).where(BranchInfo.br_id == br_id))
    return res.scalar_one_or_none()

async def create_branch(db: AsyncSession, data: BranchCreate, created_by: str = "System") -> BranchInfo:
    row = BranchInfo(
        br_id=data.br_id.strip(),
        zone_id=data.zone_id.strip(),
        br_name=(data.br_name or "").strip(),
        br_address=(data.br_address or "").strip(),
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

async def update_branch(db: AsyncSession, br_id: str, data: BranchUpdate, updated_by: str = "System") -> Optional[BranchInfo]:
    row = await get_branch(db, br_id)
    if not row:
        return None
    row.zone_id = data.zone_id.strip()
    row.br_name = (data.br_name or "").strip()
    row.br_address = (data.br_address or "").strip()
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

async def delete_branch(db: AsyncSession, br_id: str) -> bool:
    await db.execute(delete(BranchInfo).where(BranchInfo.br_id == br_id))
    await db.commit()
    return True

# -------- Auto-ID helper --------
async def next_branch_id(db: AsyncSession, zone_id: str) -> str:
    """
    br_id = <zone_id> + 3-digit running number (001, 002, ...)
    For zone 1101: 1101001, 1101002, ...
    """
    res = await db.execute(select(BranchInfo.br_id).where(BranchInfo.zone_id == zone_id))
    br_ids = [x for x in res.scalars().all() if x and x.startswith(zone_id)]
    suffixes = []
    for bid in br_ids:
        sfx = bid[len(zone_id):]
        if sfx.isdigit():
            suffixes.append(int(sfx))
    next_num = (max(suffixes) + 1) if suffixes else 1
    return f"{zone_id}{next_num:03d}"
