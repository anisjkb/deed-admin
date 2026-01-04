# src/backend/routes/routes_banner_pages.py
from __future__ import annotations

import logging
from typing import Optional, Dict, Any, cast

from fastapi import (
    APIRouter,
    Request,
    Depends,
    HTTPException,
    Form,
    UploadFile,
    File,
    Query,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from src.backend.utils.database import get_db
from src.backend.utils.auth import get_current_user
from src.backend.models.user import User

from src.backend.utils.view import render
from src.backend.utils.flash import flash_popall, redirect_with_flash
from src.backend.utils.common_context import add_common, require_admin
from src.backend.utils.permissions import (
    require_view,
    require_create,
    require_edit,
    require_delete,
)
from src.backend.utils import csrf as csrf_mod

from src.backend.crud.banner import (
    list_banners,
    get_banner,
    create_banner,
    update_banner,
    delete_banner,
    get_total_banners_count,
)
from src.backend.schemas.banner_schema import BannerCreate, BannerUpdate
from src.backend.utils.image_media import delete_media_file, save_media_with_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/banners", tags=["Admin Banners"])

# ✅ allow AVIF too
ALLOWED_BANNER_TYPES = frozenset(
    {"image/avif", "image/webp", "image/jpeg", "image/jpg", "image/png"}
)

PLACEHOLDER_IMAGE = "/images/banners/placeholder.png"


def _to_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def _to_bool(v: Any) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes", "y", "on")


# ----------------------------------------------------------
# LIST
# ----------------------------------------------------------
@router.get("", dependencies=[Depends(require_view)])
async def banners_list(
    request: Request,
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=5, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    q = (q or "").strip()
    offset = (page - 1) * size

    rows = await list_banners(db, q=q or None, limit=size, offset=offset)
    total = await get_total_banners_count(db, q=q or None)
    pages = (total + size - 1) // size if size else 1

    ctx: Dict[str, Any] = {
        "request": request,
        "title": "Manage Banners",
        "rows": rows,
        "q": q,
        "page": page,
        "pages": pages,
        "size": size,
        "total": total,
        "flashes": await flash_popall(request.session),
    }
    await add_common(ctx, db, current_user, request=request)
    return await render("admin/banners/index.html", ctx)


# ----------------------------------------------------------
# CREATE FORM
# ----------------------------------------------------------
@router.get("/new", dependencies=[Depends(require_create)])
async def banners_new_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    ctx: Dict[str, Any] = {
        "request": request,
        "title": "Create Banner",
        "mode": "create",
        "form": {
            "image_url": "",
            "headline": "",
            "subhead": "",
            "cta_text": "",
            "cta_url": "",
            "sort_order": 0,
            "is_active": True,
            "published": "Yes",
        },
        "flashes": await flash_popall(request.session),
    }
    await add_common(ctx, db, current_user, request=request)
    return await render("admin/banners/form.html", ctx)


# ----------------------------------------------------------
# CREATE ACTION
# ----------------------------------------------------------
@router.post(
    "/new",
    dependencies=[Depends(require_create), Depends(csrf_mod.csrf_protect)],
)
async def banners_create(
    request: Request,
    image_file: UploadFile = File(..., alias="image_url"),
    headline: Optional[str] = Form(None),
    subhead: Optional[str] = Form(None),
    cta_text: Optional[str] = Form(None),
    cta_url: Optional[str] = Form(None),
    sort_order: int = Form(...),
    is_active: str = Form("true"),
    published: str = Form("Yes"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    created_by = cast(str, getattr(current_user, "login_id", None)) or "System"
    is_active_bool = _to_bool(is_active)

    # Step-1: create DB row first with placeholder (to get real id)
    payload = BannerCreate(
        image_url=PLACEHOLDER_IMAGE,
        headline=_to_str(headline),
        subhead=_to_str(subhead),
        cta_text=_to_str(cta_text),
        cta_url=_to_str(cta_url),
        sort_order=int(sort_order),
        is_active=bool(is_active_bool),
        published=(published or "Yes"),
    )

    try:
        row = await create_banner(db, payload, created_by=created_by)
    except IntegrityError as e:
        ctx: Dict[str, Any] = {
            "request": request,
            "title": "Create Banner",
            "mode": "create",
            "form": payload.model_dump(),
            "error": f"Error creating banner: {e}",
            "flashes": await flash_popall(request.session),
        }
        await add_common(ctx, db, current_user, request=request)
        return await render("admin/banners/form.html", ctx)

    banner_id_int = int(getattr(row, "id"))  # ✅ fixes Column[int] -> int for Pylance

    # Step-2: save the media with real record_id + allow AVIF
    try:
        saved_url = save_media_with_id(
            subdir="banners",
            upload=image_file,
            record_id=banner_id_int,
            allowed_types=ALLOWED_BANNER_TYPES,
            max_size_mb=2,
        )
    except HTTPException as e:
        # if image save fails, remove the created banner row
        await delete_banner(db, banner_id_int)
        ctx: Dict[str, Any] = {
            "request": request,
            "title": "Create Banner",
            "mode": "create",
            "error": f"Error saving image: {e.detail}",
            "flashes": await flash_popall(request.session),
        }
        await add_common(ctx, db, current_user, request=request)
        return await render("admin/banners/form.html", ctx)

    # Step-3: update DB with saved_url
    await update_banner(
        db,
        banner_id_int,
        BannerUpdate(image_url=str(saved_url), published=(published or "Yes")),
        updated_by=created_by,
    )

    return await redirect_with_flash(
        request.session, "/admin/banners", "success", "Banner created"
    )


# ----------------------------------------------------------
# EDIT FORM
# ----------------------------------------------------------
@router.get("/{banner_id}/edit", dependencies=[Depends(require_edit)])
async def banners_edit_page(
    request: Request,
    banner_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    banner = await get_banner(db, int(banner_id))
    if banner is None:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    display_headline = (_to_str(getattr(banner, "headline")) or "Banner").strip()

    ctx: Dict[str, Any] = {
        "request": request,
        "title": f"Edit Banner — {display_headline} ({banner_id})",
        "mode": "edit",
        "form": {
            "id": int(getattr(banner, "id")),
            "image_url": str(getattr(banner, "image_url") or ""),
            "headline": _to_str(getattr(banner, "headline")),
            "subhead": _to_str(getattr(banner, "subhead")),
            "cta_text": _to_str(getattr(banner, "cta_text")),
            "cta_url": _to_str(getattr(banner, "cta_url")),
            "sort_order": int(getattr(banner, "sort_order")),
            "is_active": bool(getattr(banner, "is_active")),
            "published": str(getattr(banner, "published") or "Yes"),
        },
        "flashes": await flash_popall(request.session),
    }
    await add_common(ctx, db, current_user, request=request)
    return await render("admin/banners/form.html", ctx)


# ----------------------------------------------------------
# UPDATE ACTION
# ----------------------------------------------------------
@router.post(
    "/{banner_id}/edit",
    dependencies=[Depends(require_edit), Depends(csrf_mod.csrf_protect)],
)
async def banners_update(
    request: Request,
    banner_id: int,
    image_file: Optional[UploadFile] = File(None, alias="image_url"),
    headline: Optional[str] = Form(None),
    subhead: Optional[str] = Form(None),
    cta_text: Optional[str] = Form(None),
    cta_url: Optional[str] = Form(None),
    sort_order: Optional[int] = Form(None),
    is_active: Optional[str] = Form(None),
    published: Optional[str] = Form(None),
    deleteImageFlag: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    banner = await get_banner(db, int(banner_id))
    if banner is None:
        raise HTTPException(status_code=404, detail="Banner not found")

    updated_by = cast(str, getattr(current_user, "login_id", None)) or "System"
    banner_id_int = int(getattr(banner, "id"))

    existing_url = str(getattr(banner, "image_url") or "")
    final_image_url = existing_url if existing_url else PLACEHOLDER_IMAGE

    # delete existing image if requested
    if deleteImageFlag == "1":
        if existing_url:
            try:
                delete_media_file(existing_url)
            except Exception:
                pass
        final_image_url = PLACEHOLDER_IMAGE

    # replace image if new file uploaded
    if image_file is not None and (image_file.filename or "").strip():
        # optional: delete old image first
        if existing_url and existing_url != PLACEHOLDER_IMAGE:
            try:
                delete_media_file(existing_url)
            except Exception:
                pass

        try:
            final_image_url = save_media_with_id(
                subdir="banners",
                upload=image_file,
                record_id=banner_id_int,
                allowed_types=ALLOWED_BANNER_TYPES,
                max_size_mb=2,
            )
        except HTTPException as e:
            ctx: Dict[str, Any] = {
                "request": request,
                "title": f"Edit Banner — {banner_id_int}",
                "mode": "edit",
                "error": f"Error saving image: {e.detail}",
                "flashes": await flash_popall(request.session),
                "form": {
                    "id": banner_id_int,
                    "image_url": existing_url,
                    "headline": _to_str(headline) or _to_str(getattr(banner, "headline")) or "",
                    "subhead": _to_str(subhead) or _to_str(getattr(banner, "subhead")) or "",
                    "cta_text": _to_str(cta_text) or _to_str(getattr(banner, "cta_text")) or "",
                    "cta_url": _to_str(cta_url) or _to_str(getattr(banner, "cta_url")) or "",
                    "sort_order": int(sort_order) if sort_order is not None else int(getattr(banner, "sort_order")),
                    "is_active": _to_bool(is_active) if is_active is not None else bool(getattr(banner, "is_active")),
                    "published": (published or str(getattr(banner, "published") or "Yes")),
                },
            }
            await add_common(ctx, db, current_user, request=request)
            return await render("admin/banners/form.html", ctx)

    upd = BannerUpdate(
        image_url=str(final_image_url),
        headline=_to_str(headline) if headline is not None else _to_str(getattr(banner, "headline")),
        subhead=_to_str(subhead) if subhead is not None else _to_str(getattr(banner, "subhead")),
        cta_text=_to_str(cta_text) if cta_text is not None else _to_str(getattr(banner, "cta_text")),
        cta_url=_to_str(cta_url) if cta_url is not None else _to_str(getattr(banner, "cta_url")),
        sort_order=int(sort_order) if sort_order is not None else int(getattr(banner, "sort_order")),
        is_active=_to_bool(is_active) if is_active is not None else bool(getattr(banner, "is_active")),
        published=(published if published is not None else str(getattr(banner, "published") or "Yes")),
    )

    updated = await update_banner(db, banner_id_int, upd, updated_by=updated_by)
    title = (getattr(updated, "headline", None) or "Banner").strip()
    msg = f"{title} ({banner_id_int}) updated"
    
    return await redirect_with_flash(
        request.session, "/admin/banners", "success", msg
    )

# ----------------------------------------------------------
# DELETE ACTION
# ----------------------------------------------------------
@router.post(
    "/{banner_id}/delete",
    dependencies=[Depends(require_delete), Depends(csrf_mod.csrf_protect)],
)
async def banners_delete(
    request: Request,
    banner_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    banner = await get_banner(db, int(banner_id))
    if banner is None:
        raise HTTPException(status_code=404, detail="Banner not found")

    banner_id_int = int(getattr(banner, "id"))
    img = str(getattr(banner, "image_url") or "")

    if img:
        try:
            delete_media_file(img)
        except Exception:
            pass

    await delete_banner(db, banner_id_int)

    return await redirect_with_flash(
        request.session,
        "/admin/banners",
        "success",
        "Banner deleted successfully",
    )