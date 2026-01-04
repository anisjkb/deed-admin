# src/backend/routes/role_admin_pages.py
from __future__ import annotations

import math
from typing import Optional, Dict, Any, cast

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.utils.database import get_db
from src.backend.utils.view import render
from src.backend.utils.csrf import csrf_protect
from src.backend.utils.flash import flash_popall, redirect_with_flash
from src.backend.utils.auth import get_current_user, _log_activity as _log_user_activity
from src.backend.models.user import User
from src.backend.crud.role import (
    list_roles,
    get_role_by_id,
    create_role,
    update_role,
    delete_role,
)

# ✅ shared context + admin guard
from src.backend.utils.common_context import add_common, require_admin

# 🔐 permissions (use the /admin/roles menu mapping)
from src.backend.utils.permissions import (
    require_view,
    require_create,
    require_edit,
    require_delete,
    perms_for_request,
)

router = APIRouter(prefix="/admin/roles", tags=["Admin Roles"])


# -----------------------------
# LIST PAGE — gated by view
# -----------------------------
@router.get("", dependencies=[Depends(require_view)])
async def list_page(
    request: Request,
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=5, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    offset = (page - 1) * size
    rows, total = await list_roles(db, q=q, limit=size, offset=offset)
    pages = math.ceil(total / size) if size else 1

    ctx: Dict[str, Any] = {
        "request": request,
        "title": "Manage Roles",
        "rows": rows,
        "q": q or "",
        "page": page,
        "pages": pages,
        "size": size,
        "total": total,
        "flashes": await flash_popall(request.session),
    }
    await add_common(ctx, db, current_user, request=request)
    ctx["perms"] = await perms_for_request(db, current_user, request)  # hide New/Edit/Delete buttons if needed
    return await render("admin/security/role_index.html", ctx)


# -----------------------------
# CREATE PAGE — gated by create
# -----------------------------
@router.get("/new", dependencies=[Depends(require_create)])
async def new_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    ctx = {
        "request": request,
        "title": "Create Role",
        "mode": "create",
        "form": {},
        "flashes": await flash_popall(request.session),
    }
    await add_common(ctx, db, current_user, request=request)
    ctx["perms"] = await perms_for_request(db, current_user, request)
    return await render("admin/security/role_form.html", ctx)


# -----------------------------
# EDIT PAGE — gated by edit
# -----------------------------
@router.get("/{role_id}/edit", dependencies=[Depends(require_edit)])
async def edit_page(
    request: Request,
    role_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    row = await get_role_by_id(db, role_id)
    if not row:
        raise HTTPException(status_code=404, detail="Role not found")

    ctx = {
        "request": request,
        "title": f"Edit Role {role_id}",
        "mode": "edit",
        "form": {
            "role_id": row.role_id,
            "role_name": row.role_name,
            "status": row.status or "active",
        },
        "flashes": await flash_popall(request.session),
    }
    await add_common(ctx, db, current_user, request=request)
    ctx["perms"] = await perms_for_request(db, current_user, request)
    return await render("admin/security/role_form.html", ctx)


# -----------------------------
# CREATE ACTION — gated by create + CSRF
# -----------------------------
@router.post("", dependencies=[Depends(csrf_protect), Depends(require_create)])
async def create_action(
    request: Request,
    role_id: str = Form(...),
    role_name: str = Form(...),
    status: str = Form("active"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)
    from src.backend.schemas.role import RoleCreate

    payload = RoleCreate(role_id=role_id, role_name=role_name, status=status)

    try:
        created_by = cast(str, getattr(current_user, "login_id", "System")) or "System"
        row = await create_role(db, payload, created_by=created_by)
        await _log_user_activity(db, current_user, request, "role_create", ok=True, extra={"role_id": role_id})
        return await redirect_with_flash(request.session, "/admin/roles", "success", f"Role {row.role_id} created")

    except Exception as e:
        ctx = {
            "request": request,
            "title": "Create Role",
            "mode": "create",
            "form": {"role_id": role_id, "role_name": role_name, "status": status},
            "error": f"Failed to create role: {str(e)}",
            "flashes": await flash_popall(request.session),
        }
        await add_common(ctx, db, current_user, request=request)
        ctx["perms"] = await perms_for_request(db, current_user, request)
        return await render("admin/security/role_form.html", ctx)


# -----------------------------
# UPDATE ACTION — gated by edit + CSRF
# -----------------------------
@router.post("/{role_id}", dependencies=[Depends(csrf_protect), Depends(require_edit)])
async def update_action(
    request: Request,
    role_id: str,
    role_name: str = Form(...),
    status: str = Form("active"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)
    from src.backend.schemas.role import RoleUpdate

    payload = RoleUpdate(role_name=role_name, status=status)
    row = await update_role(db, role_id, payload, updated_by=getattr(current_user, "login_id", "System"))
    if not row:
        await _log_user_activity(db, current_user, request, "role_update", ok=False, extra={"role_id": role_id})
        return await redirect_with_flash(request.session, "/admin/roles", "danger", "Role not found")

    await _log_user_activity(db, current_user, request, "role_update", ok=True, extra={"role_id": role_id})
    return await redirect_with_flash(request.session, "/admin/roles", "success", f"Role {role_id} updated")

# -----------------------------
# DELETE ACTION — gated by delete + CSRF
# -----------------------------
@router.post("/{role_id}/delete", dependencies=[Depends(csrf_protect), Depends(require_delete)])
async def delete_action(
    request: Request,
    role_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    ok = await delete_role(db, role_id)
    if not ok:
        await _log_user_activity(db, current_user, request, "role_delete", ok=False, extra={"role_id": role_id})
        return await redirect_with_flash(request.session, "/admin/roles", "danger", "Failed to delete role")

    await _log_user_activity(db, current_user, request, "role_delete", ok=True, extra={"role_id": role_id})
    return await redirect_with_flash(request.session, "/admin/roles", "success", f"Role {role_id} deleted")