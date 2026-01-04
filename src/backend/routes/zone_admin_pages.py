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
from src.backend.models.org.br_info import BranchInfo

from src.backend.crud.zone import (
    list_zones, get_zone, create_zone, update_zone, delete_zone,
    list_orgs_for_dropdown, next_zone_id,
)
from src.backend.schemas.zone import ZoneCreate, ZoneUpdate
from src.backend.utils import csrf as csrf_mod
from src.backend.utils.view import render
from src.backend.utils.flash import flash_popall, redirect_with_flash

# ✅ shared context & coarse admin guard
from src.backend.utils.common_context import add_common, require_admin
# ✅ fine-grained permission guards (URL->menu->rights)
from src.backend.utils.permissions import (
    require_view, require_create, require_edit, require_delete
)

router = APIRouter(prefix="/admin/zones", tags=["Admin Zones"])

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
    require_admin(current_user)

    offset = (page - 1) * size
    rows, total = await list_zones(db, q=q, limit=size, offset=offset)
    pages = math.ceil(total / size) if size else 1

    ctx: Dict[str, Any] = {
        "request": request,
        "title": "Manage Zones",
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
    return await render("admin/zones/index.html", ctx)

@router.get("/next-id", dependencies=[Depends(require_create)])
async def zones_next_id(
    org_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)
    if not org_id:
        raise HTTPException(status_code=400, detail="org_id is required")
    return {"next_id": await next_zone_id(db, org_id)}

@router.get("/new", dependencies=[Depends(require_create)])
async def new_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    orgs = await list_orgs_for_dropdown(db)
    initial_oid = orgs[0].org_id if orgs else ""
    initial_zid = await next_zone_id(db, initial_oid) if initial_oid else ""

    ctx: Dict[str, Any] = {
        "request": request,
        "title": "Create Zone",
        "mode": "create",
        "form": {"org_id": initial_oid, "zone_id": initial_zid},
        "orgs": orgs,
        "flashes": await flash_popall(request.session),
    }
    await add_common(ctx, db, current_user, request=request)
    return await render("admin/zones/form.html", ctx)

@router.get("/{zone_id}/edit", dependencies=[Depends(require_edit)])
async def edit_page(
    request: Request,
    zone_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    row = await get_zone(db, zone_id)
    if not row:
        raise HTTPException(status_code=404, detail="Zone not found")

    orgs = await list_orgs_for_dropdown(db)
    ctx: Dict[str, Any] = {
        "request": request,
        "title": f"Edit Zone {zone_id}",
        "mode": "edit",
        "form": {
            "zone_id": row.zone_id,
            "org_id": row.org_id,
            "zone_name": row.zone_name,
            "zone_address": row.zone_address,
            "status": row.status,
        },
        "orgs": orgs,
        "flashes": await flash_popall(request.session),
    }
    await add_common(ctx, db, current_user, request=request)
    return await render("admin/zones/form.html", ctx)

# -------- Actions --------
@router.post(
    "",
    dependencies=[Depends(csrf_mod.csrf_protect), Depends(require_create)],
)
async def create_action(
    request: Request,
    zone_id: str = Form(...),
    org_id: str = Form(...),
    zone_name: str = Form(...),
    zone_address: Optional[str] = Form(None),
    status: Optional[str] = Form("active"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    payload = ZoneCreate(
        zone_id=zone_id,
        org_id=org_id,
        zone_name=zone_name,
        zone_address=zone_address,
        status=status,
    )
    try:
        created_by = cast(str, getattr(current_user, "login_id", "System")) or "System"
        await create_zone(db, payload, created_by=created_by)
        return await redirect_with_flash(request.session, "/admin/zones", "success", f"Zone {zone_id} created")
    except IntegrityError:
        orgs = await list_orgs_for_dropdown(db)
        ctx: Dict[str, Any] = {
            "request": request,
            "title": "Create Zone",
            "mode": "create",
            "form": payload.model_dump(),
            "orgs": orgs,
            "error": "Zone ID already exists or invalid data.",
            "flashes": await flash_popall(request.session),
        }
        await add_common(ctx, db, current_user, request=request)
        return await render("admin/zones/form.html", ctx)
    except Exception as e:
        orgs = await list_orgs_for_dropdown(db)
        ctx: Dict[str, Any] = {
            "request": request,
            "title": "Create Zone",
            "mode": "create",
            "form": payload.model_dump(),
            "orgs": orgs,
            "error": f"Failed to create zone: {e}",
            "flashes": await flash_popall(request.session),
        }
        await add_common(ctx, db, current_user, request=request)
        return await render("admin/zones/form.html", ctx)

@router.post(
    "/{zone_id}",
    dependencies=[Depends(csrf_mod.csrf_protect), Depends(require_edit)],
)
async def update_action(
    request: Request,
    zone_id: str,
    org_id: str = Form(...),
    zone_name: str = Form(...),
    zone_address: Optional[str] = Form(None),
    status: Optional[str] = Form("active"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    payload = ZoneUpdate(
        org_id=org_id,
        zone_name=zone_name,
        zone_address=zone_address,
        status=status,
    )
    updated_by = cast(str, getattr(current_user, "login_id", "System")) or "System"
    row = await update_zone(db, zone_id, payload, updated_by=updated_by)
    if not row:
        return await redirect_with_flash(request.session, "/admin/zones", "danger", "Zone not found")

    return await redirect_with_flash(request.session, "/admin/zones", "success", f"Zone {zone_id} updated")

@router.post(
    "/{zone_id}/delete",
    dependencies=[Depends(csrf_mod.csrf_protect), Depends(require_delete)],
)
async def delete_action(
    request: Request,
    zone_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    # Prevent deletion if branches exist for this zone
    has_child = await db.scalar(select(BranchInfo.br_id).where(BranchInfo.zone_id == zone_id))
    if has_child:
        return await redirect_with_flash(
            request.session,
            "/admin/zones",
            "danger",
            "Cannot delete: one or more branches are linked to this zone.",
        )

    await delete_zone(db, zone_id)
    return await redirect_with_flash(request.session, "/admin/zones", "success", f"Zone {zone_id} deleted")