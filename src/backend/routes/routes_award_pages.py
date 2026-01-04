# src/backend/routes/routes_award_pages.py

from datetime import datetime
from typing import Optional,cast
from fastapi import (
    APIRouter,Request,Depends,HTTPException,Form,UploadFile,File,
)
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from src.backend.utils.database import get_db
from src.backend.utils.auth import get_current_user
from src.backend.models.user import User
from src.backend.utils.view import render
from src.backend.utils.flash import flash_popall, redirect_with_flash
from src.backend.utils.common_context import add_common, require_admin
from src.backend.utils.permissions import require_view, require_create, require_edit, require_delete

from src.backend.crud.award import (
    list_awards,
    get_award,
    create_award,
    update_award,
    delete_award,
    get_total_awards_count,
)

from src.backend.schemas.award_schema import AwardCreate, AwardUpdate
from src.backend.utils import csrf as csrf_mod
from src.backend.utils.image_media import delete_media_file, save_media_with_id  # GLOBAL MEDIA SYSTEM

# Define logger
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/awards", tags=["Admin Awards"])

# ============================================================
#                       LIST AWARDS
# ============================================================

@router.get("", dependencies=[Depends(require_view)])
async def list_awards_page(
    request: Request,
    q: Optional[str] = None,
    page: int = 1,
    size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    require_admin(current_user)

    q = q or ""
    offset = (page - 1) * size

    rows = await list_awards(db, q=q, limit=size, offset=offset)
    total = await get_total_awards_count(db, q=q)
    pages = (total + size - 1) // size if size else 1

    ctx = {
        "request": request,
        "title": "Manage Awards",
        "rows": rows,
        "q": q,
        "page": page,
        "pages": pages,
        "size": size,
        "total": total,
        "flashes": await flash_popall(request.session),
    }

    await add_common(ctx, db, current_user, request=request)
    return await render("admin/awards/index.html", ctx)

# ============================================================
#               NEW AWARD PAGE (GET)
# ============================================================

@router.get("/new", dependencies=[Depends(require_create)])
async def new_award_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    require_admin(current_user)

    ctx = {
        "request": request,
        "title": "Create Award",
        "mode": "create",
        "form": {
            "title": "",
            "issuer": "",
            "year": datetime.now().year,
            "description": "",
            "image_url": "",
            "published": "No",
            "displaying_order": 1,
        },
        "flashes": await flash_popall(request.session),
    }

    await add_common(ctx, db, current_user, request=request)
    return await render("admin/awards/form.html", ctx)

# ============================================================
#               CREATE AWARD (POST)
# ============================================================

@router.post("/new", dependencies=[Depends(require_create), Depends(csrf_mod.csrf_protect)])
async def create_award_action(
    request: Request,
    title: str = Form(...),
    issuer: Optional[str] = Form(None),
    year: int = Form(...),
    description: Optional[str] = Form(None),
    image_file: UploadFile = File(..., alias="image_url"),
    published: str = Form(...),
    displaying_order: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    require_admin(current_user)

    # ---- Validate file type ----
    allowed_types = {"image/jpeg", "image/jpg", "image/png", "image/avif", "image/webp"}
    if image_file.content_type not in allowed_types:
        return await render(
            "admin/awards/form.html",
            {
                "request": request,
                "title": "Create Award",
                "mode": "create",
                "error": "Invalid image type. Only AVIF/JPG/PNG allowed.",
                "form": {
                    "title": title,
                    "issuer": issuer,
                    "year": year,
                    "description": description,
                    "image_url": "",
                    "published": published,
                    "displaying_order": displaying_order,
                },
                "flashes": await flash_popall(request.session),
            },
        )

    # STEP 1 — Create record WITHOUT image first (to get ID)
    payload_no_image = AwardCreate(
        title=title,
        issuer=issuer,
        year=year,
        description=description,
        image_url="",
        published=published,
        displaying_order=displaying_order,
    )

    created_by = cast(str, getattr(current_user, "login_id", "System")) or "System"
    new_award = await create_award(db, payload_no_image, created_by=created_by)

    new_id = new_award.id

    # STEP 2 — Use global media system (correct parameters!)
    image_url = save_media_with_id(
        subdir="awards",
        upload=image_file,
        record_id=new_id
    )

    # STEP 3 — Update database with final image URL
    award_update = AwardUpdate(
        title=title,
        issuer=issuer,
        year=year,
        description=description,
        image_url=image_url,
        published=published,
        displaying_order=displaying_order,
    )

    await update_award(db, new_id, award_update)

    return await redirect_with_flash(
        request.session,
        "/admin/awards",
        "success",
        f"Award '{title}' created successfully."
    )

# ============================================================
#               EDIT AWARD (GET)
# ============================================================

@router.get("/{award_id}/edit", dependencies=[Depends(require_edit)])
async def edit_award_page(
    request: Request,
    award_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    require_admin(current_user)

    award = await get_award(db, award_id)
    if not award:
        raise HTTPException(status_code=404, detail="Award not found")

    display_headline = (getattr(award, "title") or "Award").strip()
    ctx = {
        "request": request,
        "title": f"Edit Award — {display_headline} ({award_id})",
        "mode": "edit",
        "form": {
            "id": award.id,
            "title": award.title,
            "issuer": award.issuer,
            "year": award.year,
            "description": award.description,
            "image_url": award.image_url,
            "published": award.published,
            "displaying_order": award.displaying_order,
        },
        "flashes": await flash_popall(request.session),
    }

    await add_common(ctx, db, current_user, request=request)
    return await render("admin/awards/form.html", ctx)

# ============================================================
#               UPDATE AWARD (POST)
# ============================================================

@router.post("/{award_id}/edit", dependencies=[Depends(require_edit), Depends(csrf_mod.csrf_protect)])
async def update_award_action(
    request: Request,
    award_id: int,
    title: str = Form(...),
    issuer: Optional[str] = Form(None),
    year: int = Form(...),
    description: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None, alias="image_url"),
    published: str = Form(...),
    displaying_order: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    require_admin(current_user)

    existing = await get_award(db, award_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Award not found")

    image_url_str = existing.image_url

    # ---- If NEW image uploaded ----
    if image_file and image_file.filename:
        allowed_types = {"image/jpeg", "image/jpg", "image/png", "image/avif", "image/webp"}
        if image_file.content_type not in allowed_types:
            return await render(
                "admin/awards/form.html",
                {
                    "request": request,
                    "title": f"Edit Award — {title} ({award_id})",
                    "mode": "edit",
                    "error": "Invalid image type. Only AVIF/JPG/PNG/WEBP allowed.",
                    "form": {
                        "id": award_id,
                        "title": title,
                        "issuer": issuer,
                        "year": year,
                        "description": description,
                        "image_url": image_url_str,
                        "published": published,
                        "displaying_order": displaying_order,
                    },
                    "flashes": await flash_popall(request.session),
                },
            )

        # STEP 1 — Save using global media system
        image_url_str = save_media_with_id(
            subdir="awards",
            upload=image_file,
            record_id=award_id
        )

    # Update record
    award_update = AwardUpdate(
        title=title,
        issuer=issuer,
        year=year,
        description=description,
        image_url=image_url_str,
        published=published,
        displaying_order=displaying_order,
    )
    updated_by = cast(str, getattr(current_user, "login_id", "System")) or "System"
    updated_award = await update_award(db, award_id, award_update,updated_by)

    if not updated_award:
        raise HTTPException(status_code=404, detail="Award not found")

    return await redirect_with_flash(
        request.session,
        "/admin/awards",
        "success",
        f"Award '{updated_award.title}' updated successfully."
    )

# ============================================================
#               DELETE AWARD
# ============================================================

@router.post("/{award_id}/delete", dependencies=[Depends(require_delete), Depends(csrf_mod.csrf_protect)])
async def delete_award_action(
    request: Request,
    award_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    require_admin(current_user)

    # Fetch award to get its image URL
    award = await get_award(db, award_id)
    if not award:
        raise HTTPException(status_code=404, detail="Award not found")

    # Delete the related image file
    if award.image_url:
        try:
            delete_media_file(award.image_url)
            logger.info(f"Image for award {award_id} deleted successfully.")
        except Exception as e:
            logger.error(f"Error deleting image for award {award_id}: {e}")
            return await render(
                "admin/awards/index.html",
                {
                    "request": request,
                    "error": f"Error deleting related media for Award {award_id}. The award was deleted, but media could not be removed.",
                },
            )

    # Now delete the award from the database
    deleted = await delete_award(db, award_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Award not found")

    return await redirect_with_flash(
        request.session,
        "/admin/awards",
        "success",
        "Award and related media deleted successfully."
    )