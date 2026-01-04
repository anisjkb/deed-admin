# src/backend/crud/org.py
from typing import Optional, Tuple, List
from sqlalchemy import select, or_, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.models.org.org_info import OrgInfo
from src.backend.models.org.group_info import GroupInfo
from src.backend.schemas.org import OrgCreate, OrgUpdate
from src.backend.utils.timezone import now_local

def _normalize_status(v: Optional[str]) -> str:
    return (v or "active").strip().lower()

async def list_orgs(
    db: AsyncSession,
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[list[OrgInfo], int]:
    base = select(OrgInfo)
    if q:
        like = f"%{q.strip()}%"
        base = base.where(
            or_(
                OrgInfo.org_id.ilike(like),
                OrgInfo.org_name.ilike(like),
                OrgInfo.org_address.ilike(like),
                OrgInfo.status.ilike(like),
            )
        )
    base = base.order_by(OrgInfo.org_id)
    count_stmt = base.with_only_columns(OrgInfo.org_id).order_by(None)
    res = await db.execute(count_stmt)
    total = len(res.scalars().all())

    page_stmt = base.limit(limit).offset(offset)
    res2 = await db.execute(page_stmt)
    rows = list(res2.scalars().all())
    return rows, total

async def list_groups_for_dropdown(db: AsyncSession) -> List[GroupInfo]:
    res = await db.execute(
        select(GroupInfo).where(GroupInfo.status == "active").order_by(GroupInfo.group_id)
    )
    return list(res.scalars().all())

async def get_org(db: AsyncSession, org_id: str) -> Optional[OrgInfo]:
    res = await db.execute(select(OrgInfo).where(OrgInfo.org_id == org_id))
    return res.scalar_one_or_none()

async def create_org(db: AsyncSession, data: OrgCreate, created_by: str = "System") -> OrgInfo:
    row = OrgInfo(
        org_id=data.org_id.strip(),
        group_id=data.group_id.strip(),
        org_name=(data.org_name or "").strip(),
        org_address=(data.org_address or "").strip(),
        org_logo=data.org_logo,
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

async def update_org(db: AsyncSession, org_id: str, data: OrgUpdate, updated_by: str = "System") -> Optional[OrgInfo]:
    row = await get_org(db, org_id)
    if not row:
        return None
    row.group_id = data.group_id.strip()
    row.org_name = (data.org_name or "").strip()
    row.org_address = (data.org_address or "").strip()
    row.org_logo = data.org_logo
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

async def delete_org(db: AsyncSession, org_id: str) -> bool:
    # Child check happens in route (zones exist?)
    await db.execute(delete(OrgInfo).where(OrgInfo.org_id == org_id))
    await db.commit()
    return True

# -------- Auto-ID helper --------
async def next_org_id(db: AsyncSession, group_id: str) -> str:
    """
    org_id = <group_id> + <running number from 1 with no padding>
    For group 1: 11, 12, 13...
    """
    res = await db.execute(select(OrgInfo.org_id).where(OrgInfo.group_id == group_id))
    org_ids = [x for x in res.scalars().all() if x and x.startswith(group_id)]
    suffixes = []
    for oid in org_ids:
        sfx = oid[len(group_id):]
        if sfx.isdigit():
            suffixes.append(int(sfx))
    next_num = (max(suffixes) + 1) if suffixes else 1
    return f"{group_id}{next_num}"
