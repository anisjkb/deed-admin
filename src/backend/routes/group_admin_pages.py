# src/backend/routes/group_admin_pages.py
from __future__ import annotations

import math
from typing import Optional, Dict, Any, cast

from fastapi import APIRouter, Request, Depends, HTTPException, Form, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from src.backend.utils.database import get_db
from src.backend.utils.auth import get_current_user
from src.backend.models.user import User
from src.backend.models.org.org_info import OrgInfo

from src.backend.crud.group import (
    list_groups, get_group, create_group, update_group, delete_group, next_group_id
)
from src.backend.schemas.group import GroupCreate, GroupUpdate
from src.backend.utils import csrf as csrf_mod
from src.backend.utils.view import render
from src.backend.utils.flash import flash_popall, redirect_with_flash

# ✅ shared context & coarse admin guard
from src.backend.utils.common_context import add_common, require_admin
# ✅ fine-grained permission guards (URL->menu->rights)
from src.backend.utils.permissions import (
    require_view, require_create, require_edit, require_delete
)

router = APIRouter(prefix="/admin/groups", tags=["Admin Groups"])

# -------- List (view) --------
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
    rows, total = await list_groups(db, q=q, limit=size, offset=offset)
    pages = math.ceil(total / size) if size else 1

    ctx: Dict[str, Any] = {
        "request": request,
        "title": "Manage Groups",
        "rows": rows,
        "q": q or "",
        "page": page,
        "pages": pages,
        "size": size,
        "total": total,
        "flashes": await flash_popall(request.session),
    }
    # 👇 pass request so templates get `perms` for this page
    await add_common(ctx, db, current_user, request=request)
    return await render("admin/groups/index.html", ctx)

# -------- Helpers / AJAX (create) --------
@router.get("/next-id", dependencies=[Depends(require_create)])
async def groups_next_id(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)
    nid = await next_group_id(db)
    return {"next_id": nid}

# -------- New (create) --------
@router.get("/new", dependencies=[Depends(require_create)])
async def new_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    generated_id = await next_group_id(db)
    ctx: Dict[str, Any] = {
        "request": request,
        "title": "Create Group",
        "mode": "create",
        "form": {"group_id": generated_id},
        "flashes": await flash_popall(request.session),
    }
    await add_common(ctx, db, current_user, request=request)
    return await render("admin/groups/form.html", ctx)

# -------- Edit (edit) --------
@router.get("/{group_id}/edit", dependencies=[Depends(require_edit)])
async def edit_page(
    request: Request,
    group_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    row = await get_group(db, group_id)
    if not row:
        raise HTTPException(status_code=404, detail="Group not found")

    ctx: Dict[str, Any] = {
        "request": request,
        "title": f"Edit Group {group_id}",
        "mode": "edit",
        "form": {
            "group_id": row.group_id,
            "group_name": row.group_name,
            "group_address": row.group_address,
            "group_logo": row.group_logo,
            "status": row.status,
        },
        "flashes": await flash_popall(request.session),
    }
    await add_common(ctx, db, current_user, request=request)
    return await render("admin/groups/form.html", ctx)

# -------- Actions (create/edit/delete) --------
@router.post("", dependencies=[Depends(csrf_mod.csrf_protect), Depends(require_create)],)
async def create_action(
    request: Request,
    group_id: str = Form(...),
    group_name: str = Form(...),
    group_address: Optional[str] = Form(None),
    group_logo: Optional[str] = Form(None),
    status: Optional[str] = Form("active"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    payload = GroupCreate(
        group_id=group_id,
        group_name=group_name,
        group_address=group_address,
        group_logo=group_logo,
        status=status,
    )
    try:
        created_by = cast(str, getattr(current_user, "login_id", "System")) or "System"
        await create_group(db, payload, created_by=created_by)
        return await redirect_with_flash(
            request.session, "/admin/groups", "success", f"Group {group_id} created"
        )
    except IntegrityError:
        ctx: Dict[str, Any] = {
            "request": request,
            "title": "Create Group",
            "mode": "create",
            "form": payload.model_dump(),
            "error": "Group ID already exists or invalid data.",
            "flashes": await flash_popall(request.session),
        }
        await add_common(ctx, db, current_user, request=request)
        return await render("admin/groups/form.html", ctx)
    except Exception as e:
        ctx: Dict[str, Any] = {
            "request": request,
            "title": "Create Group",
            "mode": "create",
            "form": payload.model_dump(),
            "error": f"Failed to create group: {e}",
            "flashes": await flash_popall(request.session),
        }
        await add_common(ctx, db, current_user, request=request)
        return await render("admin/groups/form.html", ctx)

@router.post(
    "/{group_id}",
    dependencies=[Depends(csrf_mod.csrf_protect), Depends(require_edit)],
)
async def update_action(
    request: Request,
    group_id: str,
    group_name: str = Form(...),
    group_address: Optional[str] = Form(None),
    group_logo: Optional[str] = Form(None),
    status: Optional[str] = Form("active"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    payload = GroupUpdate(
        group_name=group_name,
        group_address=group_address,
        group_logo=group_logo,
        status=status,
    )
    updated_by = cast(str, getattr(current_user, "login_id", "System")) or "System"
    row = await update_group(db, group_id, payload, updated_by=updated_by)
    if not row:
        return await redirect_with_flash(request.session, "/admin/groups", "danger", "Group not found")

    return await redirect_with_flash(
        request.session, "/admin/groups", "success", f"Group {group_id} updated"
    )

@router.post(
    "/{group_id}/delete",
    dependencies=[Depends(csrf_mod.csrf_protect), Depends(require_delete)],
)
async def delete_action(
    request: Request,
    group_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    # ✅ Prevent deletion if any organization exists for this group
    has_child = await db.scalar(select(OrgInfo.org_id).where(OrgInfo.group_id == group_id))
    if has_child:
        return await redirect_with_flash(
            request.session,
            "/admin/groups",
            "danger",
            "Cannot delete: one or more organizations are linked to this group.",
        )

    await delete_group(db, group_id)
    return await redirect_with_flash(
        request.session, "/admin/groups", "success", f"Group {group_id} deleted"
    )