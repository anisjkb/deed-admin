# src/backend/routes/menu_admin_pages.py
from __future__ import annotations

import math
from typing import Optional, cast, Dict, Any

from fastapi import APIRouter, Request, Depends, HTTPException, Form, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.utils.database import get_db
from src.backend.utils.auth import get_current_user
from src.backend.models.user import User
from src.backend.crud.menu import (
    list_menus,
    get_menu_by_id,
    create_menu,
    update_menu,
    delete_menu,
    delete_menu_safe,
)
from src.backend.schemas.menu import MenuCreate, MenuUpdate
from src.backend.utils import csrf as csrf_mod
from src.backend.utils.view import render
from src.backend.utils.flash import flash_popall, redirect_with_flash

from src.backend.utils.common_context import add_common, require_admin
from src.backend.utils.permissions import (
    require_view,
    require_create,
    require_edit,
    require_delete,
)
from src.backend.utils.menu_cache import invalidate_all_menu_cache  # Cache Invalidation

router = APIRouter(prefix="/admin/menus", tags=["Admin Menus"])

def _yn(v: Optional[str]) -> Optional[str]:
    """Coerce a flag to strict 'Y'/'N' (or None). Ensures Pylance compatibility."""
    v = (v or "").strip().upper()
    return v if v in ("Y", "N") else None

# -----------------------
# GET PAGES (gated)
# -----------------------
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
    rows, total = await list_menus(db, q=q, limit=size, offset=offset)
    pages = math.ceil(total / size) if size else 1

    ctx: Dict[str, Any] = {
        "request": request,
        "title": "Manage Menus",
        "rows": rows,
        "q": q or "",
        "page": page,
        "pages": pages,
        "size": size,
        "total": total,
        "flashes": await flash_popall(request.session),
    }
    await add_common(ctx, db, current_user, request=request)
    return await render("admin/security/menu_index.html", ctx)


@router.get("/new", dependencies=[Depends(require_create)])
async def new_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    parents, _ = await list_menus(db, q=None, limit=1000, offset=0)
    ctx: Dict[str, Any] = {
        "request": request,
        "title": "Create Menu",
        "mode": "create",
        "parents": parents,
        "form": {},
        "flashes": await flash_popall(request.session),
    }
    await add_common(ctx, db, current_user, request=request)
    return await render("admin/security/menu_form.html", ctx)


@router.get("/{menu_id}/edit", dependencies=[Depends(require_edit)])
async def edit_page(
    request: Request,
    menu_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    row = await get_menu_by_id(db, menu_id)
    if not row:
        raise HTTPException(status_code=404, detail="Menu not found")

    parents, _ = await list_menus(db, q=None, limit=1000, offset=0)
    ctx: Dict[str, Any] = {
        "request": request,
        "title": f"Edit Menu {menu_id}",
        "mode": "edit",
        "parents": parents,
        "form": {
            "menu_id": row.menu_id,
            "menu_name": row.menu_name,
            "parent_id": row.parent_id or "0",
            "is_parents": row.is_parents,
            "url": row.url,
            "menu_order": row.menu_order,
            "font_awesome_icon": row.font_awesome_icon,
            "f_awesome_icon_css": row.f_awesome_icon_css,
            "active_flag": row.active_flag,
            "status": row.status,
        },
        "flashes": await flash_popall(request.session),
    }
    await add_common(ctx, db, current_user, request=request)
    return await render("admin/security/menu_form.html", ctx)


# -------------------------
# POST ACTIONS (gated + CSRF)
# -------------------------
@router.post("", dependencies=[Depends(csrf_mod.csrf_protect), Depends(require_create)])
async def create_action(
    request: Request,
    menu_id: str = Form(...),
    menu_name: Optional[str] = Form(None),
    parent_id: Optional[str] = Form("0"),
    is_parents: Optional[str] = Form("N"),
    url: Optional[str] = Form(None),
    menu_order: Optional[int] = Form(0),
    font_awesome_icon: Optional[str] = Form(None),
    f_awesome_icon_css: Optional[str] = Form(None),
    active_flag: Optional[str] = Form("Y"),
    status: Optional[str] = Form("active"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    payload: Optional[MenuCreate] = None
    try:
        is_parents_casted = _yn(is_parents)
        active_flag_casted = _yn(active_flag)

        payload = MenuCreate(
            menu_id=menu_id,
            menu_name=menu_name,
            parent_id=parent_id,
            is_parents=is_parents_casted,
            url=url,
            menu_order=menu_order,
            font_awesome_icon=font_awesome_icon,
            f_awesome_icon_css=f_awesome_icon_css,
            active_flag=active_flag_casted,
            status=status,
        )

        created_by = cast(str, getattr(current_user, "login_id", "System")) or "System"
        await create_menu(db, payload, created_by=created_by)
        
        # Invalidate the cache after creating/updating/deleting a menu
        invalidate_all_menu_cache()

        return await redirect_with_flash(request.session, "/admin/menus", "success", f"Menu {menu_id} created")

    except IntegrityError:
        parents, _ = await list_menus(db, q=None, limit=1000, offset=0)
        form_data = payload.model_dump() if payload is not None else {
            "menu_id": menu_id,
            "menu_name": menu_name,
            "parent_id": parent_id,
            "is_parents": is_parents,
            "url": url,
            "menu_order": menu_order,
            "font_awesome_icon": font_awesome_icon,
            "f_awesome_icon_css": f_awesome_icon_css,
            "active_flag": active_flag,
            "status": status,
        }
        ctx: Dict[str, Any] = {
            "request": request,
            "title": "Create Menu",
            "mode": "create",
            "parents": parents,
            "form": form_data,
            "error": "Menu ID already exists or invalid data.",
            "flashes": await flash_popall(request.session),
        }
        await add_common(ctx, db, current_user, request=request)
        return await render("admin/security/menu_form.html", ctx)

    except Exception as e:
        parents, _ = await list_menus(db, q=None, limit=1000, offset=0)
        ctx: Dict[str, Any] = {
            "request": request,
            "title": "Create Menu",
            "mode": "create",
            "parents": parents,
            "form": {
                "menu_id": menu_id,
                "menu_name": menu_name,
                "parent_id": parent_id,
                "is_parents": is_parents,
                "url": url,
                "menu_order": menu_order,
                "font_awesome_icon": font_awesome_icon,
                "f_awesome_icon_css": f_awesome_icon_css,
                "active_flag": active_flag,
                "status": status,
            },
            "error": f"Failed to create menu: {str(e)}",
            "flashes": await flash_popall(request.session),
        }
        await add_common(ctx, db, current_user, request=request)
        return await render("admin/security/menu_form.html", ctx)


@router.post("/{menu_id}", dependencies=[Depends(csrf_mod.csrf_protect), Depends(require_edit)])
async def update_action(
    request: Request,
    menu_id: str,
    menu_name: Optional[str] = Form(None),
    parent_id: Optional[str] = Form("0"),
    is_parents: Optional[str] = Form("N"),
    url: Optional[str] = Form(None),
    menu_order: Optional[int] = Form(0),
    font_awesome_icon: Optional[str] = Form(None),
    f_awesome_icon_css: Optional[str] = Form(None),
    active_flag: Optional[str] = Form("Y"),
    status: Optional[str] = Form("active"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    active_flag_casted = _yn(active_flag)
    is_parents_casted = _yn(is_parents)

    payload = MenuUpdate(
        menu_name=menu_name,
        parent_id=parent_id,
        is_parents=is_parents_casted,
        url=url,
        menu_order=menu_order,
        font_awesome_icon=font_awesome_icon,
        f_awesome_icon_css=f_awesome_icon_css,
        active_flag=active_flag_casted,
        status=status,
    )

    updated_by = cast(str, getattr(current_user, "login_id", "System")) or "System"
    row = await update_menu(db, menu_id, payload, updated_by=updated_by)
    
    # Invalidate the cache after creating/updating/deleting a menu
    invalidate_all_menu_cache()

    if not row:
        return await redirect_with_flash(request.session, "/admin/menus", "danger", "Menu not found")
    return await redirect_with_flash(request.session, "/admin/menus", "success", f"Menu {menu_id} updated")

@router.post("/{menu_id}/delete", dependencies=[Depends(csrf_mod.csrf_protect), Depends(require_delete)])
async def delete_action(
    request: Request,
    menu_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    ok, msg = await delete_menu_safe(db, menu_id)
    if ok:
        # Invalidate the cache after creating/updating/deleting a menu
        invalidate_all_menu_cache()

    if not ok:
        return await redirect_with_flash(request.session, "/admin/menus", "danger", msg)
    return await redirect_with_flash(request.session, "/admin/menus", "success", msg)