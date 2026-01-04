# src/backend/routes/org_admin_pages.py
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
from src.backend.models.org.zone_info import ZoneInfo

from src.backend.crud.org import (
    list_orgs, get_org, create_org, update_org, delete_org,
    list_groups_for_dropdown, next_org_id,
)
from src.backend.schemas.org import OrgCreate, OrgUpdate
from src.backend.utils import csrf as csrf_mod
from src.backend.utils.view import render
from src.backend.utils.flash import flash_popall, redirect_with_flash

# ✅ shared context & coarse admin check
from src.backend.utils.common_context import add_common, require_admin
# ✅ fine-grained permission guards (URL->menu->rights)
from src.backend.utils.permissions import (
    require_view, require_create, require_edit, require_delete
)

router = APIRouter(prefix="/admin/orgs", tags=["Admin Orgs"])

# -------- Pages --------
@router.get("", dependencies=[Depends(require_view)])
async def list_page(
    request: Request,
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=5, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Coarse check (has a role); fine-grained is above
    require_admin(current_user)

    offset = (page - 1) * size
    rows, total = await list_orgs(db, q=q, limit=size, offset=offset)
    pages = math.ceil(total / size) if size else 1

    ctx: Dict[str, Any] = {
        "request": request,
        "title": "Manage Organizations",
        "rows": rows,
        "q": q or "",
        "page": page,
        "pages": pages,
        "size": size,
        "total": total,
        "flashes": await flash_popall(request.session),
    }
    # 👇 pass request so add_common can compute `perms` for this page
    await add_common(ctx, db, current_user, request=request)
    return await render("admin/orgs/index.html", ctx)

@router.get("/next-id", dependencies=[Depends(require_create)])
async def orgs_next_id(
    group_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)
    if not group_id:
        raise HTTPException(status_code=400, detail="group_id is required")
    return {"next_id": await next_org_id(db, group_id)}

@router.get("/new", dependencies=[Depends(require_create)])
async def new_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)
    groups = await list_groups_for_dropdown(db)
    initial_gid = groups[0].group_id if groups else ""
    initial_oid = await next_org_id(db, initial_gid) if initial_gid else ""

    ctx: Dict[str, Any] = {
        "request": request,
        "title": "Create Organization",
        "mode": "create",
        "form": {"group_id": initial_gid, "org_id": initial_oid},
        "groups": groups,
        "flashes": await flash_popall(request.session),
    }
    await add_common(ctx, db, current_user, request=request)
    return await render("admin/orgs/form.html", ctx)

@router.get("/{org_id}/edit", dependencies=[Depends(require_edit)])
async def edit_page(
    request: Request,
    org_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)
    row = await get_org(db, org_id)
    if not row:
        raise HTTPException(status_code=404, detail="Organization not found")

    groups = await list_groups_for_dropdown(db)
    ctx: Dict[str, Any] = {
        "request": request,
        "title": f"Edit Organization {org_id}",
        "mode": "edit",
        "form": {
            "org_id": row.org_id,
            "group_id": row.group_id,
            "org_name": row.org_name,
            "org_address": row.org_address,
            "org_logo": row.org_logo,
            "status": row.status,
        },
        "groups": groups,
        "flashes": await flash_popall(request.session),
    }
    await add_common(ctx, db, current_user, request=request)
    return await render("admin/orgs/form.html", ctx)

# -------- Actions (CSRF + perms) --------
@router.post(
    "",
    dependencies=[Depends(csrf_mod.csrf_protect), Depends(require_create)],
)
async def create_action(
    request: Request,
    org_id: str = Form(...),
    group_id: str = Form(...),
    org_name: str = Form(...),
    org_address: Optional[str] = Form(None),
    org_logo: Optional[str] = Form(None),
    status: Optional[str] = Form("active"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    payload = OrgCreate(
        org_id=org_id,
        group_id=group_id,
        org_name=org_name,
        org_address=org_address,
        org_logo=org_logo,
        status=status,
    )
    try:
        created_by = cast(str, getattr(current_user, "login_id", "System")) or "System"
        await create_org(db, payload, created_by=created_by)
        return await redirect_with_flash(
            request.session, "/admin/orgs", "success", f"Organization {org_id} created"
        )
    except IntegrityError:
        groups = await list_groups_for_dropdown(db)
        ctx: Dict[str, Any] = {
            "request": request,
            "title": "Create Organization",
            "mode": "create",
            "form": payload.model_dump(),
            "groups": groups,
            "error": "Organization ID already exists or invalid data.",
            "flashes": await flash_popall(request.session),
        }
        await add_common(ctx, db, current_user, request=request)
        return await render("admin/orgs/form.html", ctx)
    except Exception as e:
        groups = await list_groups_for_dropdown(db)
        ctx: Dict[str, Any] = {
            "request": request,
            "title": "Create Organization",
            "mode": "create",
            "form": payload.model_dump(),
            "groups": groups,
            "error": f"Failed to create organization: {e}",
            "flashes": await flash_popall(request.session),
        }
        await add_common(ctx, db, current_user, request=request)
        return await render("admin/orgs/form.html", ctx)

@router.post(
    "/{org_id}",
    dependencies=[Depends(csrf_mod.csrf_protect), Depends(require_edit)],
)
async def update_action(
    request: Request,
    org_id: str,
    group_id: str = Form(...),
    org_name: str = Form(...),
    org_address: Optional[str] = Form(None),
    org_logo: Optional[str] = Form(None),
    status: Optional[str] = Form("active"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    payload = OrgUpdate(
        group_id=group_id,
        org_name=org_name,
        org_address=org_address,
        org_logo=org_logo,
        status=status,
    )
    updated_by = cast(str, getattr(current_user, "login_id", "System")) or "System"
    row = await update_org(db, org_id, payload, updated_by=updated_by)
    if not row:
        return await redirect_with_flash(request.session, "/admin/orgs", "danger", "Organization not found")

    return await redirect_with_flash(
        request.session, "/admin/orgs", "success", f"Organization {org_id} updated"
    )

@router.post(
    "/{org_id}/delete",
    dependencies=[Depends(csrf_mod.csrf_protect), Depends(require_delete)],
)
async def delete_action(
    request: Request,
    org_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    # ✅ Prevent deletion if zones exist for this org
    has_child = await db.scalar(select(ZoneInfo.zone_id).where(ZoneInfo.org_id == org_id))
    if has_child:
        return await redirect_with_flash(
            request.session,
            "/admin/orgs",
            "danger",
            "Cannot delete: one or more zones are linked to this organization.",
        )

    await delete_org(db, org_id)
    return await redirect_with_flash(
        request.session, "/admin/orgs", "success", f"Organization {org_id} deleted"
    )