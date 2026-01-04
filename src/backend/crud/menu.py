# src/backend/crud/menu.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.models.security.menu import Menu
from src.backend.models.security.right import Right
from src.backend.schemas.menu import MenuCreate, MenuUpdate


def _menu_row_to_dict(m: Menu) -> Dict[str, Any]:
    return {
        "menu_id": (m.menu_id or "").strip(),
        "menu_name": (m.menu_name or "").strip(),
        "parent_id": (m.parent_id or "0").strip(),
        "is_parents": (m.is_parents or "N").strip(),
        "url": (m.url or "#").strip(),
        "menu_order": int(m.menu_order or 0),
        "icon": (m.font_awesome_icon or "").strip(),
        "icon_css": (m.f_awesome_icon_css or "").strip(),
        "children": [],
    }


def _norm_id_py(x: Any) -> str:
    """
    Normalize IDs so:
      - trims spaces
      - numeric IDs: '01' -> '1', but keep '0' as '0'
    """
    s = str(x or "").strip()
    if s.isdigit():
        s2 = s.lstrip("0")
        return s2 if s2 != "" else "0"
    return s


def _norm_id_sql(col):
    """
    SQL-side normalization for Postgres:
      TRIM -> LTRIM('0') -> NULLIF('', NULL) -> COALESCE('0')
    So '01' and '1' become the same key.
    """
    trimmed = func.trim(col)
    lz = func.ltrim(trimmed, "0")
    return func.coalesce(func.nullif(lz, ""), "0")


async def get_visible_menus_for_role(db: AsyncSession, role_id: str) -> List[Dict[str, Any]]:
    """
    FAST + robust sidebar visibility.

    ✅ Handles:
    - spaces/case in status flags
    - '01' vs '1' id mismatches (role_id + menu_id + parent_id)
    - includes ACTIVE ancestors of visible menus (so tree doesn't break)

    Base visible menu:
      - Menu.status == 'active'
      - Menu.active_flag == 'Y'
      - Right.status == 'active'
      - Right.view_permit == 'Y'
      - Right.role_id matches role_id (normalized)
    """
    role_id = (role_id or "").strip()
    if not role_id:
        return []

    # Normalize role_id on both sides ('01' vs '1')
    rid_sql = _norm_id_sql(Right.role_id)
    rid_in = _norm_id_py(role_id)

    m_status_ok = func.lower(func.trim(Menu.status)) == "active"
    m_flag_ok = func.upper(func.trim(Menu.active_flag)) == "Y"
    r_status_ok = func.lower(func.trim(Right.status)) == "active"
    r_view_ok = func.upper(func.trim(Right.view_permit)) == "Y"

    # Join by normalized menu_id ('01' vs '1')
    join_on = _norm_id_sql(Right.menu_id) == _norm_id_sql(Menu.menu_id)

    # Step-1: menus directly visible by Right(view=Y)
    stmt = (
        select(Menu)
        .join(Right, join_on)
        .where(
            m_status_ok,
            m_flag_ok,
            r_status_ok,
            r_view_ok,
            rid_sql == rid_in,
        )
        .order_by(Menu.menu_order.asc(), Menu.menu_id.asc())
    )
    res = await db.execute(stmt)
    visible: List[Menu] = list(res.scalars().unique().all())
    if not visible:
        return []

    # Step-2: load ALL active menus once (for ancestor linking)
    all_stmt = select(Menu).where(m_status_ok, m_flag_ok)
    all_res = await db.execute(all_stmt)
    all_active: List[Menu] = list(all_res.scalars().all())

    # Lookup active menus by normalized menu_id
    by_id: Dict[str, Menu] = {}
    for m in all_active:
        mid = _norm_id_py(m.menu_id)
        if mid:
            by_id[mid] = m

    def is_root(menu: Menu) -> bool:
        pid = _norm_id_py(menu.parent_id or "0")
        mid = _norm_id_py(menu.menu_id)
        isp = (menu.is_parents or "N").strip().upper() == "Y"
        return isp or pid in ("", "0") or pid == mid

    # Step-3: include ancestors so tree remains usable
    included: Dict[str, Menu] = {}
    for m in visible:
        mid = _norm_id_py(m.menu_id)
        if mid:
            included[mid] = m

    for m in visible:
        cur = m
        guard = 0
        while cur and guard < 60:
            guard += 1
            if is_root(cur):
                break
            pid = _norm_id_py(cur.parent_id)
            if not pid or pid in ("", "0"):
                break
            parent = by_id.get(pid)
            if not parent:
                break
            pmid = _norm_id_py(parent.menu_id)
            if pmid:
                included[pmid] = parent
            cur = parent

    flat = [_menu_row_to_dict(m) for m in included.values()]
    flat.sort(key=lambda d: (d.get("menu_order") or 0, (d.get("menu_id") or "")))
    return flat


def build_menu_tree(menus: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Builds a tree from flat menus.

    Robust:
      - normalizes IDs so parent_id '01' matches menu_id '1'
      - keeps orphans visible (promoted to root)
    """
    def norm(x: Any) -> str:
        return _norm_id_py(x)

    by_id: Dict[str, Dict[str, Any]] = {}

    for m in menus:
        m["children"] = []
        m["menu_id"] = norm(m.get("menu_id"))
        m["parent_id"] = norm(m.get("parent_id") or "0")
        m["is_parents"] = str(m.get("is_parents") or "N").strip().upper()
        by_id[m["menu_id"]] = m

    def is_root(node: Dict[str, Any]) -> bool:
        return (
            node["is_parents"] == "Y"
            or node["parent_id"] in ("", "0")
            or node["parent_id"] == node["menu_id"]
        )

    roots: List[Dict[str, Any]] = []

    for m in menus:
        if is_root(m):
            roots.append(m)
            continue
        parent = by_id.get(m["parent_id"])
        if parent:
            parent["children"].append(m)
        else:
            roots.append(m)

    # de-dup roots
    seen = set()
    uniq_roots = []
    for r in roots:
        mid = r.get("menu_id")
        if mid and mid not in seen:
            uniq_roots.append(r)
            seen.add(mid)
    roots = uniq_roots

    def sort_nodes(nodes: List[Dict[str, Any]]) -> None:
        nodes.sort(key=lambda x: (x.get("menu_order") or 0, x.get("menu_id") or ""))
        for n in nodes:
            sort_nodes(n.get("children") or [])

    sort_nodes(roots)
    return roots


# --- CRUD below (unchanged) ---

async def get_menu_by_id(db: AsyncSession, menu_id: str) -> Optional[Menu]:
    res = await db.execute(select(Menu).where(Menu.menu_id == menu_id))
    return res.scalar_one_or_none()


async def list_menus(
    db: AsyncSession,
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[Menu], int]:
    stmt = select(Menu)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            (Menu.menu_id.ilike(like))
            | (Menu.menu_name.ilike(like))
            | (Menu.url.ilike(like))
            | (Menu.status.ilike(like))
        )
    stmt = stmt.order_by(Menu.menu_id, Menu.parent_id, Menu.menu_order)

    count_res = await db.execute(stmt.with_only_columns(Menu.menu_id).order_by(None))
    total = len(count_res.scalars().all())

    res = await db.execute(stmt.limit(limit).offset(offset))
    return list(res.scalars().all()), total


async def create_menu(db: AsyncSession, data: MenuCreate, created_by: str = "System") -> Menu:
    row = Menu(
        menu_id=data.menu_id,
        menu_name=data.menu_name,
        parent_id=data.parent_id,
        is_parents=(data.is_parents or "N").strip().upper(),
        url=data.url,
        menu_order=data.menu_order,
        font_awesome_icon=data.font_awesome_icon,
        f_awesome_icon_css=data.f_awesome_icon_css,
        active_flag=(data.active_flag or "Y").strip().upper(),
        status=(data.status or "active").strip().lower(),
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


async def update_menu(db: AsyncSession, menu_id: str, data: MenuUpdate, updated_by: str = "System") -> Optional[Menu]:
    row = await get_menu_by_id(db, menu_id)
    if not row:
        return None

    setattr(row, "menu_name", data.menu_name)
    setattr(row, "parent_id", data.parent_id)
    setattr(row, "is_parents", (data.is_parents or "N").strip().upper())
    setattr(row, "url", data.url)
    setattr(row, "menu_order", data.menu_order)
    setattr(row, "font_awesome_icon", data.font_awesome_icon)
    setattr(row, "f_awesome_icon_css", data.f_awesome_icon_css)
    setattr(row, "active_flag", (data.active_flag or "Y").strip().upper())
    setattr(row, "status", (data.status or "active").strip().lower())
    setattr(row, "updated_by", updated_by)

    try:
        await db.commit()
        await db.refresh(row)
    except IntegrityError:
        await db.rollback()
        raise
    return row


async def delete_menu(db: AsyncSession, menu_id: str) -> bool:
    child = await db.execute(select(Menu.menu_id).where(Menu.parent_id == menu_id).limit(1))
    if child.scalar_one_or_none():
        return False
    await db.execute(delete(Menu).where(Menu.menu_id == menu_id))
    await db.commit()
    return True


async def count_children(db: AsyncSession, menu_id: str) -> int:
    res = await db.execute(select(func.count()).select_from(Menu).where(Menu.parent_id == menu_id))
    return int(res.scalar() or 0)


async def count_right_links(db: AsyncSession, menu_id: str) -> int:
    res = await db.execute(select(func.count()).select_from(Right).where(Right.menu_id == menu_id))
    return int(res.scalar() or 0)


async def delete_menu_safe(db: AsyncSession, menu_id: str) -> Tuple[bool, str]:
    row = await get_menu_by_id(db, menu_id)
    if not row:
        return False, f"Menu '{menu_id}' not found."

    n_children = await count_children(db, menu_id)
    if n_children > 0:
        return False, f"Cannot delete menu '{menu_id}' — it has {n_children} child item(s)."

    n_rights = await count_right_links(db, menu_id)
    if n_rights > 0:
        return False, f"Cannot delete menu '{menu_id}' — it is assigned to {n_rights} role(s)."

    await db.execute(delete(Menu).where(Menu.menu_id == menu_id))
    await db.commit()
    return True, f"Menu '{menu_id}' deleted successfully."