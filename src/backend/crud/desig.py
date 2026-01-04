# src/backend/crud/desig.py
from typing import Optional, Tuple
from sqlalchemy import select, or_, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.models.org.desig_info import DesigInfo
from src.backend.schemas.desig import DesigCreate, DesigUpdate
from src.backend.utils.timezone import now_local

def _normalize_status(v: Optional[str]) -> str:
    return (v or "active").strip().lower()

async def list_desigs(
    db: AsyncSession,
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[list[DesigInfo], int]:
    base = select(DesigInfo)
    if q:
        like = f"%{q.strip()}%"
        base = base.where(
            or_(
                DesigInfo.desig_id.ilike(like),
                DesigInfo.desig_name.ilike(like),
                DesigInfo.status.ilike(like),
            )
        )
    base = base.order_by(DesigInfo.desig_id)

    # total
    res = await db.execute(base.with_only_columns(DesigInfo.desig_id).order_by(None))
    total = len(res.scalars().all())

    # page
    res2 = await db.execute(base.limit(limit).offset(offset))
    rows = list(res2.scalars().all())
    return rows, total

async def get_desig(db: AsyncSession, desig_id: str) -> Optional[DesigInfo]:
    res = await db.execute(select(DesigInfo).where(DesigInfo.desig_id == desig_id))
    return res.scalar_one_or_none()

async def create_desig(db: AsyncSession, data: DesigCreate, created_by: str = "System") -> DesigInfo:
    # Auto-ID
    new_id = await next_desig_id(db)
    row = DesigInfo(
        desig_id=new_id,
        desig_name=(data.desig_name or "").strip(),
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

async def update_desig(db: AsyncSession, desig_id: str, data: DesigUpdate, updated_by: str = "System") -> Optional[DesigInfo]:
    row = await get_desig(db, desig_id)
    if not row:
        return None
    row.desig_name = (data.desig_name or "").strip()
    row.status = _normalize_status(data.status)
    setattr(row, 'updated_by', updated_by)
    setattr(row, 'updated_dt', now_local())
    try:
        await db.commit()
        await db.refresh(row)
    except IntegrityError:
        await db.rollback()
        raise
    return row

async def delete_desig(db: AsyncSession, desig_id: str) -> bool:
    await db.execute(delete(DesigInfo).where(DesigInfo.desig_id == desig_id))
    await db.commit()
    return True

# -------- Auto-ID helper --------
async def next_desig_id(db: AsyncSession) -> str:
    """
    desig_id is a two-digit numeric string: "01", "02", ...; next = max + 1
    Falls back to "01" if none or malformed.
    """
    res = await db.execute(select(DesigInfo.desig_id))
    ids = [i for i in res.scalars().all() if (i or "").isdigit()]
    if not ids:
        return "01"
    try:
        n = max(int(x) for x in ids) + 1
        return f"{n:02d}"
    except Exception:
        return "01"
