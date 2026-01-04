# src/backend/crud/menu.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import delete, func, or_, and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased

from src.backend.models.security.menu import Menu
from src.backend.models.security.right import Right  # mapped to "rights" table
from src.backend.schemas.menu import MenuCreate, MenuUpdate


# -----------------------------------------------------------------------------
# Helpers for menu shaping
# -----------------------------------------------------------------------------
def _menu_row_to_dict(m: Menu) -> Dict[str, Any]:
    return {
        "menu_id": (m.menu_id or "").strip(),
        "menu_name": (m.menu_name or "").strip(),
        "parent_id": (m.parent_id or "0").strip(),
        "is_parents": (m.is_parents or "N").strip(),
        "url": (m.url or "#").strip(),
        "menu_order": m.menu_order or 0,
        "icon": (m.font_awesome_icon or "").strip(),
        "icon_css": (m.f_awesome_icon_css or "").strip(),
        "children": [],
    }


# -----------------------------------------------------------------------------
# For sidebar building (visible menus by role)
# -----------------------------------------------------------------------------
async def get_visible_menus_for_role(db: AsyncSession, role_id: str) -> List[Dict[str, Any]]:
    """
    Menus that should appear in the LEFT SIDEBAR for a user with this role.

    Enforced rules for a row to be visible:
      - The menu itself must be active: Menu.status='active' AND Menu.active_flag='Y'
      - The role must have an active right for this menu: Right.view_permit='Y' AND Right.status='active'
      - If the menu is a child (not a root), then its parent must ALSO be:
          - active (status='active' AND active_flag='Y'), and
          - have an active right for the same role (view_permit='Y' AND status='active').

    Result: if parent is inactive or lacks rights, the child will NOT show.
    Returns a flat list of dicts, suitable for build_menu_tree().
    """
    if not role_id:
        return []

    # Aliases for clarity
    Parent = aliased(Menu)
    ParentRight = aliased(Right)
    ThisRight = aliased(Right)

    # Identify roots (we tolerate older seeds too)
    is_root = or_(
        Menu.is_parents == "Y",
        Menu.parent_id.in_(("", "0")),
        Menu.parent_id == Menu.menu_id,  # self-parented seeds
    )

    # Candidate menu must be active AND have an active view right
    this_menu_ok = and_(
        Menu.status == "active",
        Menu.active_flag == "Y",
        ThisRight.view_permit == "Y",
        ThisRight.status == "active",
    )

    # Child requires parent to be active AND have active right
    parent_ok = and_(
        Parent.menu_id.isnot(None),
        Parent.status == "active",
        Parent.active_flag == "Y",
        ParentRight.view_permit == "Y",
        ParentRight.status == "active",
    )

    stmt = (
        select(Menu)
        # right for this (candidate) menu
        .join(ThisRight, and_(ThisRight.menu_id == Menu.menu_id, ThisRight.role_id == role_id))
        # parent & parent's right (outer joins because roots have no parent)
        .join(Parent, Parent.menu_id == Menu.parent_id, isouter=True)
        .join(ParentRight, and_(ParentRight.menu_id == Parent.menu_id, ParentRight.role_id == role_id), isouter=True)
        # rules: this menu is OK AND (root OR parent_ok)
        .where(and_(this_menu_ok, or_(is_root, parent_ok)))
        .order_by(Menu.menu_order, Menu.menu_id)
    )

    res = await db.execute(stmt)
    menus: List[Menu] = list(res.scalars().unique().all())

    flat: List[Dict[str, Any]] = [_menu_row_to_dict(m) for m in menus]
    flat.sort(key=lambda d: (d.get("menu_order") or 0, d.get("menu_id") or ""))
    return flat


def build_menu_tree(menus: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Build a parent->children tree.

    Root rule (robust):
      - is_parents == 'Y'  → root
      - OR parent_id in ('', '0') → root (tolerate old seeds)
      - OR parent_id == menu_id → root (self-parented seeds)

    Children attach by parent_id; if parent is not present in the visible set,
    the item is promoted to a root so nothing is lost.
    """
    by_id: Dict[str, Dict[str, Any]] = {}
    for m in menus:
        m["children"] = []
        m["is_parents"] = (m.get("is_parents") or "N").strip().upper()
        m["menu_id"] = str(m.get("menu_id", "")).strip()
        m["parent_id"] = str(m.get("parent_id", "") or "").strip()
        by_id[m["menu_id"]] = m

    roots: List[Dict[str, Any]] = []

    def is_root(node: Dict[str, Any]) -> bool:
        return (
            node["is_parents"] == "Y"
            or node["parent_id"] in ("", "0")
            or node["parent_id"] == node["menu_id"]
        )

    # first pass: explicit roots
    for m in menus:
        if is_root(m):
            roots.append(m)

    # second pass: attach children or promote if parent missing
    for m in menus:
        if is_root(m):
            continue
        parent = by_id.get(m["parent_id"])
        if parent:
            parent["children"].append(m)
        else:
            roots.append(m)  # orphan → root

    # de-dup roots
    seen = set()
    uniq_roots = []
    for r in roots:
        if r["menu_id"] not in seen:
            uniq_roots.append(r)
            seen.add(r["menu_id"])
    roots = uniq_roots

    # sort by menu_order at each level
    def sort_deep(nodes: List[Dict[str, Any]]) -> None:
        nodes.sort(key=lambda x: x.get("menu_order") or 0)
        for n in nodes:
            sort_deep(n["children"])

    sort_deep(roots)
    return roots


# -----------------------------------------------------------------------------
# Basic CRUD
# -----------------------------------------------------------------------------
async def get_menu_by_id(db: AsyncSession, menu_id: str) -> Optional[Menu]:
    res = await db.execute(select(Menu).where(Menu.menu_id == menu_id))
    return res.scalar_one_or_none()


async def list_menus(
    db: AsyncSession,
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[Menu], int]:
    base = select(Menu)
    if q:
        like = f"%{q.strip()}%"
        base = base.where(
            or_(
                Menu.menu_id.ilike(like),
                Menu.menu_name.ilike(like),
                Menu.url.ilike(like),
                Menu.status.ilike(like),
            )
        )
    base = base.order_by(Menu.menu_id, Menu.parent_id, Menu.menu_order)

    # quick count
    res_count = await db.execute(base.with_only_columns(Menu.menu_id).order_by(None))
    total = len(res_count.scalars().all())

    res = await db.execute(base.limit(limit).offset(offset))
    rows = list(res.scalars().all())
    return rows, total


async def create_menu(db: AsyncSession, data: MenuCreate, created_by: str = "System") -> Menu:
    new_row = Menu(
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
    db.add(new_row)
    try:
        await db.commit()
        await db.refresh(new_row)
    except IntegrityError:
        await db.rollback()
        raise
    return new_row


async def update_menu(db: AsyncSession, menu_id: str, data: MenuUpdate, updated_by: str = "System") -> Optional[Menu]:
    row = await get_menu_by_id(db, menu_id)
    if not row:
        return None

    # Use setattr to keep type-checkers happy with SQLAlchemy InstrumentedAttribute
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
    """
    Legacy simple delete (kept for compatibility).
    Blocks deletion if this menu has children.
    Does NOT check rights. Prefer delete_menu_safe() below.
    """
    children = await db.execute(select(Menu.menu_id).where(Menu.parent_id == menu_id).limit(1))
    if children.scalar_one_or_none():
        return False

    await db.execute(delete(Menu).where(Menu.menu_id == menu_id))
    await db.commit()
    return True


# -----------------------------------------------------------------------------
# Safe delete (checks children + rights)
# -----------------------------------------------------------------------------
async def count_children(db: AsyncSession, menu_id: str) -> int:
    res = await db.execute(select(func.count()).select_from(Menu).where(Menu.parent_id == menu_id))
    return int(res.scalar() or 0)


async def count_right_links(db: AsyncSession, menu_id: str) -> int:
    """Count how many rights rows reference this menu."""
    res = await db.execute(select(func.count()).select_from(Right).where(Right.menu_id == menu_id))
    return int(res.scalar() or 0)


async def menu_has_any_rights(db: AsyncSession, menu_id: str) -> bool:
    res = await db.execute(select(Right.menu_id).where(Right.menu_id == menu_id).limit(1))
    return res.scalar_one_or_none() is not None


async def delete_menu_safe(db: AsyncSession, menu_id: str) -> Tuple[bool, str]:
    """
    Deletes a menu iff:
      - it exists
      - it has no child menus
      - it is not referenced in rights
    Returns (ok, message).
    """
    row = await get_menu_by_id(db, menu_id)
    if not row:
        return False, f"Menu '{menu_id}' not found."

    # 1) children?
    n_children = await count_children(db, menu_id)
    if n_children > 0:
        return (
            False,
            f"Cannot delete menu '{row.menu_name}' (ID: {menu_id}) — it has {n_children} child item(s). Remove/move them first.",
        )

    # 2) referenced in rights?
    n_rights = await count_right_links(db, menu_id)
    if n_rights > 0:
        return (
            False,
            f"Cannot delete menu '{row.menu_name}' (ID: {menu_id}) — it is assigned to {n_rights} role(s). Remove those rights first.",
        )

    # 3) safe to delete
    await db.execute(delete(Menu).where(Menu.menu_id == menu_id))
    await db.commit()
    return True, f"Menu '{row.menu_name}' (ID: {menu_id}) deleted successfully."