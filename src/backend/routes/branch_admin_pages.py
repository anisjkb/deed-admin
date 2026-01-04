from __future__ import annotations

import math
from typing import Optional, Dict, Any, cast

from fastapi import APIRouter, Request, Depends, HTTPException, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from src.backend.utils.database import get_db
from src.backend.utils.auth import get_current_user
from src.backend.models.user import User

from src.backend.crud.branch import (
    list_branches, get_branch, create_branch, update_branch, delete_branch,
    list_zones_for_dropdown, next_branch_id,
)
from src.backend.schemas.branch import BranchCreate, BranchUpdate
from src.backend.utils import csrf as csrf_mod
from src.backend.utils.view import render
from src.backend.utils.flash import flash_popall, redirect_with_flash

# ✅ shared context & coarse admin guard
from src.backend.utils.common_context import add_common, require_admin
# ✅ fine-grained permission guards (URL->menu->rights)
from src.backend.utils.permissions import (
    require_view, require_create, require_edit, require_delete
)

router = APIRouter(prefix="/admin/branches", tags=["Admin Branches"])

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
    rows, total = await list_branches(db, q=q, limit=size, offset=offset)
    pages = math.ceil(total / size) if size else 1

    ctx: Dict[str, Any] = {
        "request": request,
        "title": "Manage Branches",
        "rows": rows,
        "q": q or "",
        "page": page,
        "pages": pages,
        "size": size,
        "total": total,
        "flashes": await flash_popall(request.session),
    }
    # 👇 pass request so templates receive `perms` for this URL
    await add_common(ctx, db, current_user, request=request)
    return await render("admin/branches/index.html", ctx)

@router.get("/next-id", dependencies=[Depends(require_create)])
async def branches_next_id(
    zone_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)
    if not zone_id:
        raise HTTPException(status_code=400, detail="zone_id is required")
    return {"next_id": await next_branch_id(db, zone_id)}

@router.get("/new", dependencies=[Depends(require_create)])
async def new_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    zones = await list_zones_for_dropdown(db)
    initial_zid = zones[0].zone_id if zones else ""
    initial_bid = await next_branch_id(db, initial_zid) if initial_zid else ""

    ctx: Dict[str, Any] = {
        "request": request,
        "title": "Create Branch",
        "mode": "create",
        "form": {"zone_id": initial_zid, "br_id": initial_bid},
        "zones": zones,
        "flashes": await flash_popall(request.session),
    }
    await add_common(ctx, db, current_user, request=request)
    return await render("admin/branches/form.html", ctx)

@router.get("/{br_id}/edit", dependencies=[Depends(require_edit)])
async def edit_page(
    request: Request,
    br_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    row = await get_branch(db, br_id)
    if not row:
        raise HTTPException(status_code=404, detail="Branch not found")

    zones = await list_zones_for_dropdown(db)
    ctx: Dict[str, Any] = {
        "request": request,
        "title": f"Edit Branch {br_id}",
        "mode": "edit",
        "form": {
            "br_id": row.br_id,
            "zone_id": row.zone_id,
            "br_name": row.br_name,
            "br_address": row.br_address,
            "status": row.status,
        },
        "zones": zones,
        "flashes": await flash_popall(request.session),
    }
    await add_common(ctx, db, current_user, request=request)
    return await render("admin/branches/form.html", ctx)

# -------- Actions --------
@router.post(
    "",
    dependencies=[Depends(csrf_mod.csrf_protect), Depends(require_create)],
)
async def create_action(
    request: Request,
    br_id: str = Form(...),
    zone_id: str = Form(...),
    br_name: str = Form(...),
    br_address: Optional[str] = Form(None),
    status: Optional[str] = Form("active"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    payload = BranchCreate(
        br_id=br_id,
        zone_id=zone_id,
        br_name=br_name,
        br_address=br_address,
        status=status,
    )
    try:
        created_by = cast(str, getattr(current_user, "login_id", "System")) or "System"
        await create_branch(db, payload, created_by=created_by)
        return await redirect_with_flash(request.session, "/admin/branches", "success", f"Branch {br_id} created")
    except IntegrityError:
        zones = await list_zones_for_dropdown(db)
        ctx: Dict[str, Any] = {
            "request": request,
            "title": "Create Branch",
            "mode": "create",
            "form": payload.model_dump(),
            "zones": zones,
            "error": "Branch ID already exists or invalid data.",
            "flashes": await flash_popall(request.session),
        }
        await add_common(ctx, db, current_user, request=request)
        return await render("admin/branches/form.html", ctx)
    except Exception as e:
        zones = await list_zones_for_dropdown(db)
        ctx: Dict[str, Any] = {
            "request": request,
            "title": "Create Branch",
            "mode": "create",
            "form": payload.model_dump(),
            "zones": zones,
            "error": f"Failed to create branch: {e}",
            "flashes": await flash_popall(request.session),
        }
        await add_common(ctx, db, current_user, request=request)
        return await render("admin/branches/form.html", ctx)

@router.post(
    "/{br_id}",
    dependencies=[Depends(csrf_mod.csrf_protect), Depends(require_edit)],
)
async def update_action(
    request: Request,
    br_id: str,
    zone_id: str = Form(...),
    br_name: str = Form(...),
    br_address: Optional[str] = Form(None),
    status: Optional[str] = Form("active"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    payload = BranchUpdate(
        zone_id=zone_id,
        br_name=br_name,
        br_address=br_address,
        status=status,
    )
    updated_by = cast(str, getattr(current_user, "login_id", "System")) or "System"
    row = await update_branch(db, br_id, payload, updated_by=updated_by)
    if not row:
        return await redirect_with_flash(request.session, "/admin/branches", "danger", "Branch not found")

    return await redirect_with_flash(request.session, "/admin/branches", "success", f"Branch {br_id} updated")

@router.post(
    "/{br_id}/delete",
    dependencies=[Depends(csrf_mod.csrf_protect), Depends(require_delete)],
)
async def delete_action(
    request: Request,
    br_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    await delete_branch(db, br_id)
    return await redirect_with_flash(request.session, "/admin/branches", "success", f"Branch {br_id} deleted")