# src/backend/crud/role.py
from __future__ import annotations
from typing import Optional, Tuple, List,Dict
from sqlalchemy import select, delete, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from src.backend.models.security.role import Role
from src.backend.schemas.role import RoleCreate, RoleUpdate
from typing import Dict, List

async def get_role_by_id(db: AsyncSession, role_id: str) -> Optional[Role]:
    res = await db.execute(select(Role).where(Role.role_id == role_id))
    return res.scalar_one_or_none()

async def list_roles(
    db: AsyncSession,
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[Role], int]:
    stmt = select(Role)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Role.role_id.ilike(like),
                Role.role_name.ilike(like),
                Role.status.ilike(like),
            )
        )
    stmt = stmt.order_by(Role.role_id)

    # quick count (fine for small tables)
    res_count = await db.execute(stmt.with_only_columns(Role.role_id).order_by(None))
    total = len(res_count.scalars().all())

    page = await db.execute(stmt.limit(limit).offset(offset))
    rows = list(page.scalars().all())
    return rows, total

async def create_role(db: AsyncSession, payload: RoleCreate, created_by: str = "System") -> Role:
    row = Role(
        role_id=payload.role_id,
        role_name=payload.role_name,
        status=payload.status or "active",
        created_by=created_by,
        updated_by=created_by,
    )
    db.add(row)
    try:
        await db.commit()
        await db.refresh(row)
    except IntegrityError:
        await db.rollback()
        raise
    return row

async def update_role(db: AsyncSession, role_id: str, payload: RoleUpdate, updated_by: str = "System") -> Optional[Role]:
    row = await get_role_by_id(db, role_id)
    if not row:
        return None
    if payload.role_name is not None:
        setattr(row, "role_name", payload.role_name)
    if payload.status is not None:
        setattr(row, "status", payload.status or "active")
    setattr(row, "updated_by", updated_by)
    try:
        await db.commit()
        await db.refresh(row)
    except IntegrityError:
        await db.rollback()
        raise
    return row

async def delete_role(db: AsyncSession, role_id: str) -> bool:
    await db.execute(delete(Role).where(Role.role_id == role_id))
    await db.commit()
    return True

async def list_role_ids(db: AsyncSession) -> List[str]:
    res = await db.execute(select(Role.role_id).order_by(Role.role_id))
    return list(res.scalars().all())

async def list_roles_for_select(db: AsyncSession) -> List[Dict[str, str]]:
    """
    Returns roles for select menus as [{role_id, role_name}], ordered by role_id.
    """
    res = await db.execute(select(Role.role_id, Role.role_name).order_by(Role.role_id))
    return [{"role_id": rid, "role_name": rname} for (rid, rname) in res.all()]