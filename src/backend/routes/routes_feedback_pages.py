# src/backend/routes/routes_feedback_pages.py
from typing import Optional, cast
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.utils.database import get_db
from src.backend.utils.auth import get_current_user
from src.backend.models.user import User
from src.backend.utils.view import render
from src.backend.utils.flash import flash_popall, redirect_with_flash
from src.backend.utils.common_context import add_common, require_admin
from src.backend.utils.permissions import (
    require_view, require_create, require_edit, require_delete
)
from src.backend.utils import csrf as csrf_mod

from src.backend.schemas.feedback_schema import FeedbackCreate, FeedbackUpdate
from src.backend.crud.feedback import (
    list_feedback, get_feedback, create_feedback,
    update_feedback, delete_feedback, get_total_feedback_count,
    mark_feedback_read,            # auto-mark-as-read on edit
    count_unread_feedback,         # for API response badge refresh
)

router = APIRouter(prefix="/admin/feedback", tags=["Admin Feedback"])

# ============================================================
#                       LIST FEEDBACK
# ============================================================
@router.get("", dependencies=[Depends(require_view)])
async def list_feedback_page(
    request: Request,
    q: Optional[str] = None,
    page: int = 1,
    size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    q = q or ""
    offset = (page - 1) * size

    rows = await list_feedback(db, q=q, limit=size, offset=offset)
    total = await get_total_feedback_count(db, q=q)
    pages = (total + size - 1) // size if size else 1

    ctx = {
        "request": request,
        "title": "Manage Feedback",
        "rows": rows,
        "q": q,
        "page": page,
        "pages": pages,
        "size": size,
        "total": total,
        "flashes": await flash_popall(request.session),
    }
    await add_common(ctx, db, current_user, request=request)
    return await render("admin/feedback/index.html", ctx)


# ============================================================
#                    NEW FEEDBACK (GET)
# ============================================================
@router.get("/new", dependencies=[Depends(require_create)])
async def new_feedback_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    ctx = {
        "request": request,
        "title": "Create Feedback",
        "mode": "create",
        "form": {
            "name": "",
            "phone": "",
            "email": "",
            "message": "",
        },
        "flashes": await flash_popall(request.session),
    }
    await add_common(ctx, db, current_user, request=request)
    return await render("admin/feedback/form.html", ctx)


# ============================================================
#                    CREATE FEEDBACK (POST)
# ============================================================
@router.post("/new", dependencies=[Depends(require_create), Depends(csrf_mod.csrf_protect)])
async def create_feedback_action(
    request: Request,
    name: str = Form(...),
    phone: str = Form(...),
    email: Optional[str] = Form(None),
    message: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    created_by = cast(str, getattr(current_user, "login_id", "System")) or "System"
    payload = FeedbackCreate(name=name, phone=phone, email=email, message=message)
    row = await create_feedback(db, payload, created_by=created_by)

    return await redirect_with_flash(
        request.session,
        "/admin/feedback",
        "success",
        f"Feedback #{row.id} created successfully."
    )


# ============================================================
#                     EDIT FEEDBACK (GET)
# ============================================================
@router.get("/{feedback_id}/edit", dependencies=[Depends(require_edit)])
async def edit_feedback_page(
    request: Request,
    feedback_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    row = await get_feedback(db, feedback_id)
    if not row:
        raise HTTPException(status_code=404, detail="Feedback not found")

    # ---------- auto-mark as read on open ----------
    if hasattr(row, "is_read") and not row.is_read:
        await mark_feedback_read(db, feedback_id)
        row.is_read = True
    # -----------------------------------------------

    display_headline = (getattr(row, "name") or "Feedback").strip()
    ctx = {
        "request": request,
        "title": f"Edit Feedback — {display_headline} ({feedback_id})",
        "mode": "edit",
        "form": {
            "id": row.id,
            "name": row.name,
            "phone": row.phone,
            "email": row.email,
            "message": row.message,
            "created_at": row.created_at,
        },
        "flashes": await flash_popall(request.session),
    }
    await add_common(ctx, db, current_user, request=request)
    return await render("admin/feedback/form.html", ctx)


# ============================================================
#                     UPDATE FEEDBACK (POST)
# ============================================================
@router.post("/{feedback_id}/edit", dependencies=[Depends(require_edit), Depends(csrf_mod.csrf_protect)])
async def update_feedback_action(
    request: Request,
    feedback_id: int,
    name: str = Form(...),
    phone: str = Form(...),
    email: Optional[str] = Form(None),
    message: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    payload = FeedbackUpdate(name=name, phone=phone, email=email, message=message)
    updated = await update_feedback(db, feedback_id, payload, updated_by=getattr(current_user, "login_id", "System"))
    if not updated:
        raise HTTPException(status_code=404, detail="Feedback not found")

    return await redirect_with_flash(
        request.session,
        "/admin/feedback",
        "success",
        f"Feedback #{feedback_id} updated successfully."
    )


# ============================================================
#                        DELETE FEEDBACK
# ============================================================
@router.post("/{feedback_id}/delete", dependencies=[Depends(require_delete), Depends(csrf_mod.csrf_protect)])
async def delete_feedback_action(
    request: Request,
    feedback_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    row = await get_feedback(db, feedback_id)
    if not row:
        raise HTTPException(status_code=404, detail="Feedback not found")

    deleted = await delete_feedback(db, feedback_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Feedback not found")

    return await redirect_with_flash(
        request.session,
        "/admin/feedback",
        "success",
        f"Feedback #{feedback_id} deleted successfully."
    )


# ============================================================
#                 AJAX: MARK AS READ (API)
#   Path: POST /admin/api/feedback/{feedback_id}/mark-read
#   Keep this router in the same file; register it in main.py
# ============================================================
api_router = APIRouter(tags=["Admin Feedback API"])

@api_router.post(
    "/admin/api/feedback/{feedback_id}/mark-read",
    dependencies=[Depends(require_edit), Depends(csrf_mod.csrf_protect)],
)
async def mark_feedback_as_read_api(
    feedback_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark a feedback row as read (idempotent).
    Returns: { ok, id, updated, unread_count }
    """
    require_admin(current_user)

    row = await get_feedback(db, feedback_id)
    if not row:
        raise HTTPException(status_code=404, detail="Feedback not found")

    updated = await mark_feedback_read(db, feedback_id)
    unread_count = await count_unread_feedback(db)

    return {
        "ok": True,
        "id": feedback_id,
        "updated": bool(updated),   # True if state changed from unread -> read
        "unread_count": unread_count,
    }