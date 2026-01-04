# src/backend/routes/rights.py
from __future__ import annotations

import math
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.utils.database import get_db
from src.backend.utils.view import render
from src.backend.utils.csrf import csrf_protect
from src.backend.utils.flash import flash_popall, redirect_with_flash
from src.backend.utils.auth import get_current_user

from src.backend.models.user import User
from src.backend.models.security.role import Role
from src.backend.models.security.menu import Menu

from src.backend.crud.rights import (
    get_rights_by_role_and_menu,
    update_rights,
    delete_right,
)

from src.backend.utils.common_context import add_common, require_admin
from src.backend.utils.permissions import (
    require_view,
    require_edit,
    require_delete,
)

from src.backend.utils.menu_cache import invalidate_role_menu_cache

router = APIRouter(prefix="/admin/rights", tags=["Admin Rights"])


async def _get_roles(db: AsyncSession):
    rows = await db.execute(select(Role).order_by(Role.role_id))
    return list(rows.scalars().all())


async def _get_menus(db: AsyncSession):
    rows = await db.execute(select(Menu).order_by(Menu.menu_order, Menu.menu_id))
    return list(rows.scalars().all())


@router.get("", dependencies=[Depends(require_view)])
async def rights_index_page(
    request: Request,
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=5, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    roles = await _get_roles(db)
    if q:
        ql = q.lower().strip()
        roles = [
            r for r in roles
            if ql in (r.role_id or "").lower()
            or ql in (r.role_name or "").lower()
        ]

    total = len(roles)
    start = (page - 1) * size
    end = start + size
    rows = roles[start:end]
    pages = max(1, math.ceil(total / size))

    ctx: Dict[str, Any] = {
        "request": request,
        "title": "Manage Rights",
        "rows": rows,
        "q": q or "",
        "page": page,
        "pages": pages,
        "size": size,
        "total": total,
        "flashes": await flash_popall(request.session),
    }
    await add_common(ctx, db, current_user, request=request)
    # ✅ Step-6: DO NOT call perms_for_request() again; add_common already set ctx["perms"]
    return await render("admin/security/rights_index.html", ctx)


@router.get("/edit/{role_id}", dependencies=[Depends(require_view)])
async def edit_rights_page(
    request: Request,
    role_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    role = await db.scalar(select(Role).where(Role.role_id == role_id))
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    menus = await _get_menus(db)

    rights_rows = []
    for m in menus:
        rd = await get_rights_by_role_and_menu(db, role_id, str(m.menu_id))
        rights_rows.append({"menu": m, "rights": rd})

    ctx = {
        "request": request,
        "title": f"Edit Rights — Role {role_id}",
        "role": role,
        "menus": menus,
        "rights_rows": rights_rows,
        "flashes": await flash_popall(request.session),
    }
    await add_common(ctx, db, current_user, request=request)
    return await render("admin/security/rights_edit_form.html", ctx)


@router.post("/update/{role_id}", dependencies=[Depends(csrf_protect), Depends(require_edit)])
async def update_rights_action(
    request: Request,
    role_id: str,
    menu_id: str = Form(...),
    create_permit: str = Form("N"),
    view_permit: str = Form("N"),
    edit_permit: str = Form("N"),
    delete_permit: str = Form("N"),
    status: str = Form("active"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    def yn(v: str) -> str:
        return "Y" if (v or "").upper() == "Y" else "N"

    await update_rights(
        db=db,
        role_id=role_id,
        menu_id=str(menu_id),
        create_permit=yn(create_permit),
        view_permit=yn(view_permit),
        edit_permit=yn(edit_permit),
        delete_permit=yn(delete_permit),
        status=status or "active",
        updated_by=getattr(current_user, "login_id", "System"),
    )

    # ✅ rights change affects role menu visibility
    invalidate_role_menu_cache(role_id)

    return await redirect_with_flash(
        request.session,
        f"/admin/rights/edit/{role_id}",
        "success",
        f"Rights updated for menu {menu_id}.",
    )


@router.post("/remove/{role_id}", dependencies=[Depends(csrf_protect), Depends(require_delete)])
async def remove_rights_action(
    request: Request,
    role_id: str,
    menu_id: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    ok = await delete_right(db, role_id, str(menu_id))

    # ✅ rights change affects role menu visibility
    invalidate_role_menu_cache(role_id)

    if ok:
        return await redirect_with_flash(
            request.session,
            f"/admin/rights/edit/{role_id}",
            "success",
            f"Rights removed for menu {menu_id}.",
        )
    return await redirect_with_flash(
        request.session,
        f"/admin/rights/edit/{role_id}",
        "danger",
        "Failed to remove rights.",
    )