# src/backend/crud/group.py
from typing import Optional, Tuple, List
from sqlalchemy import select, or_, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.models.org.group_info import GroupInfo
from src.backend.schemas.group import GroupCreate, GroupUpdate
from src.backend.utils.timezone import now_local

def _normalize_status(v: Optional[str]) -> str:
    return (v or "active").strip().lower()

async def list_groups(
    db: AsyncSession,
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[list[GroupInfo], int]:
    base = select(GroupInfo)
    if q:
        like = f"%{q.strip()}%"
        base = base.where(
            or_(
                GroupInfo.group_id.ilike(like),
                GroupInfo.group_name.ilike(like),
                GroupInfo.group_address.ilike(like),
                GroupInfo.status.ilike(like),
            )
        )
    base = base.order_by(GroupInfo.group_id)
    count_stmt = base.with_only_columns(GroupInfo.group_id).order_by(None)
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

async def get_group(db: AsyncSession, group_id: str) -> Optional[GroupInfo]:
    res = await db.execute(select(GroupInfo).where(GroupInfo.group_id == group_id))
    return res.scalar_one_or_none()

async def create_group(db: AsyncSession, data: GroupCreate, created_by: str = "System") -> GroupInfo:
    row = GroupInfo(
        group_id=data.group_id.strip(),
        group_name=(data.group_name or "").strip(),
        group_address=(data.group_address or "").strip(),
        group_logo=data.group_logo,
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

async def update_group(db: AsyncSession, group_id: str, data: GroupUpdate, updated_by: str = "System") -> Optional[GroupInfo]:
    row = await get_group(db, group_id)
    if not row:
        return None
    row.group_name = (data.group_name or "").strip()
    row.group_address = (data.group_address or "").strip()
    row.group_logo = data.group_logo
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

async def delete_group(db: AsyncSession, group_id: str) -> bool:
    # Child check happens in route (orgs exist?)
    await db.execute(delete(GroupInfo).where(GroupInfo.group_id == group_id))
    await db.commit()
    return True

# -------- Auto-ID helper --------
async def next_group_id(db: AsyncSession) -> str:
    """
    group_id is numeric string. Next = max(existing)::int + 1, start at '1'.
    """
    res = await db.execute(select(GroupInfo.group_id))
    ids = [i for i in res.scalars().all() if (i or "").isdigit()]
    if not ids:
        return "1"
    return str(max(int(x) for x in ids) + 1)
