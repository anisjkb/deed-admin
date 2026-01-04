# src/backend/crud/rights.py
from __future__ import annotations

from typing import Optional
from sqlalchemy import select, update, insert, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.models.security.right import Right


def _yn(v: str | None) -> str:
    return "Y" if (v or "").strip().upper() == "Y" else "N"


async def get_rights_by_role_and_menu(
    db: AsyncSession, role_id: str, menu_id: str
) -> Optional[Right]:
    res = await db.execute(
        select(Right).where(Right.role_id == role_id, Right.menu_id == menu_id)
    )
    return res.scalar_one_or_none()


async def create_right(
    db: AsyncSession,
    role_id: str,
    menu_id: str,
    create_permit: str = "N",
    view_permit: str = "N",
    edit_permit: str = "N",
    delete_permit: str = "N",
    status: str = "active",
    created_by: Optional[str] = None,
) -> Right:
    stmt = (
        insert(Right)
        .values(
            role_id=role_id,
            menu_id=menu_id,
            create_permit=_yn(create_permit),
            view_permit=_yn(view_permit),
            edit_permit=_yn(edit_permit),
            delete_permit=_yn(delete_permit),
            status=(status or "active").strip().lower(),
            created_by=created_by,
            updated_by=created_by,
        )
        .returning(Right)
    )
    res = await db.execute(stmt)
    await db.commit()
    return res.scalar_one()


async def update_rights(
    db: AsyncSession,
    role_id: str,
    menu_id: str,
    create_permit: str = "N",
    view_permit: str = "N",
    edit_permit: str = "N",
    delete_permit: str = "N",
    status: str = "active",
    updated_by: Optional[str] = None,
) -> Right:
    """
    Upsert behavior:
      - If (role_id, menu_id) exists -> UPDATE
      - Else -> INSERT
    """
    existing = await get_rights_by_role_and_menu(db, role_id, menu_id)
    if not existing:
        # create new
        return await create_right(
            db=db,
            role_id=role_id,
            menu_id=menu_id,
            create_permit=create_permit,
            view_permit=view_permit,
            edit_permit=edit_permit,
            delete_permit=delete_permit,
            status=status,
            created_by=updated_by,
        )

    # update existing
    stmt = (
        update(Right)
        .where(Right.role_id == role_id, Right.menu_id == menu_id)
        .values(
            create_permit=_yn(create_permit),
            view_permit=_yn(view_permit),
            edit_permit=_yn(edit_permit),
            delete_permit=_yn(delete_permit),
            status=(status or "active").strip().lower(),
            updated_by=updated_by,
        )
        .returning(Right)
    )
    res = await db.execute(stmt)
    await db.commit()
    return res.scalar_one()


async def delete_right(db: AsyncSession, role_id: str, menu_id: str) -> bool:
    stmt = delete(Right).where(Right.role_id == role_id, Right.menu_id == menu_id)
    await db.execute(stmt)
    await db.commit()
    return True