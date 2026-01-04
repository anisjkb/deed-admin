from __future__ import annotations

import math
from typing import Optional, Dict, Any, cast

from fastapi import APIRouter, Request, Depends, HTTPException, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from src.backend.utils.database import get_db
from src.backend.utils.auth import get_current_user
from src.backend.models.user import User

from src.backend.crud.desig import (
    list_desigs, get_desig, create_desig, update_desig, delete_desig, next_desig_id
)
from src.backend.schemas.desig import DesigCreate, DesigUpdate
from src.backend.utils import csrf as csrf_mod
from src.backend.utils.view import render
from src.backend.utils.flash import flash_popall, redirect_with_flash

# ✅ shared context & coarse admin guard
from src.backend.utils.common_context import add_common, require_admin
# ✅ fine-grained permission guards (URL->menu->rights)
from src.backend.utils.permissions import (
    require_view, require_create, require_edit, require_delete
)

router = APIRouter(prefix="/admin/designations", tags=["Admin Designations"])

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
    rows, total = await list_desigs(db, q=q, limit=size, offset=offset)
    pages = math.ceil(total / size) if size else 1

    ctx: Dict[str, Any] = {
        "request": request,
        "title": "Manage Designations",
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
    return await render("admin/designations/index.html", ctx)

@router.get("/next-id", dependencies=[Depends(require_create)])
async def desigs_next_id(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)
    nid = await next_desig_id(db)
    return {"next_id": nid}

@router.get("/new", dependencies=[Depends(require_create)])
async def new_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)
    generated_id = await next_desig_id(db)
    ctx: Dict[str, Any] = {
        "request": request,
        "title": "Create Designation",
        "mode": "create",
        "form": {"desig_id": generated_id},
        "flashes": await flash_popall(request.session),
    }
    await add_common(ctx, db, current_user, request=request)
    return await render("admin/designations/form.html", ctx)

@router.get("/{desig_id}/edit", dependencies=[Depends(require_edit)])
async def edit_page(
    request: Request,
    desig_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)
    row = await get_desig(db, desig_id)
    if not row:
        raise HTTPException(status_code=404, detail="Designation not found")

    ctx: Dict[str, Any] = {
        "request": request,
        "title": f"Edit Designation {desig_id}",
        "mode": "edit",
        "form": {
            "desig_id": row.desig_id,
            "desig_name": row.desig_name,
            "status": row.status,
        },
        "flashes": await flash_popall(request.session),
    }
    await add_common(ctx, db, current_user, request=request)
    return await render("admin/designations/form.html", ctx)

# -------- Actions --------
@router.post(
    "",
    dependencies=[Depends(csrf_mod.csrf_protect), Depends(require_create)],
)
async def create_action(
    request: Request,
    desig_name: str = Form(...),
    status: Optional[str] = Form("active"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)
    payload = DesigCreate(desig_name=desig_name, status=status)

    try:
        created_by = cast(str, getattr(current_user, "login_id", "System")) or "System"
        row = await create_desig(db, payload, created_by=created_by)
        return await redirect_with_flash(
            request.session, "/admin/designations", "success", f"Designation {row.desig_id} created"
        )
    except IntegrityError:
        ctx: Dict[str, Any] = {
            "request": request,
            "title": "Create Designation",
            "mode": "create",
            "form": {"desig_id": await next_desig_id(db), "desig_name": desig_name, "status": status},
            "error": "Designation already exists or invalid data.",
            "flashes": await flash_popall(request.session),
        }
        await add_common(ctx, db, current_user, request=request)
        return await render("admin/designations/form.html", ctx)
    except Exception as e:
        ctx: Dict[str, Any] = {
            "request": request,
            "title": "Create Designation",
            "mode": "create",
            "form": {"desig_id": await next_desig_id(db), "desig_name": desig_name, "status": status},
            "error": f"Failed to create designation: {e}",
            "flashes": await flash_popall(request.session),
        }
        await add_common(ctx, db, current_user, request=request)
        return await render("admin/designations/form.html", ctx)

@router.post(
    "/{desig_id}",
    dependencies=[Depends(csrf_mod.csrf_protect), Depends(require_edit)],
)
async def update_action(
    request: Request,
    desig_id: str,
    desig_name: str = Form(...),
    status: Optional[str] = Form("active"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)
    payload = DesigUpdate(desig_name=desig_name, status=status)

    updated_by = cast(str, getattr(current_user, "login_id", "System")) or "System"
    row = await update_desig(db, desig_id, payload, updated_by=updated_by)
    if not row:
        return await redirect_with_flash(request.session, "/admin/designations", "danger", "Designation not found")

    return await redirect_with_flash(
        request.session, "/admin/designations", "success", f"Designation {desig_id} updated"
    )

@router.post(
    "/{desig_id}/delete",
    dependencies=[Depends(csrf_mod.csrf_protect), Depends(require_delete)],
)
async def delete_action(
    request: Request,
    desig_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)
    await delete_desig(db, desig_id)
    return await redirect_with_flash(
        request.session, "/admin/designations", "success", f"Designation {desig_id} deleted"
    )
