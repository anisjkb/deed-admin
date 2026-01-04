from __future__ import annotations
from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import  Dict, Any
from src.backend.utils.database import get_db
from src.backend.utils.auth import get_current_user
from src.backend.models.user import User
from src.backend.utils.view import render
from src.backend.utils.flash import flash_popall
from src.backend.utils.common_context import add_common, require_admin
from src.backend.utils.permissions import require_view

# Initialize router
router = APIRouter(prefix="/admin/image-editor", tags=["Admin Image Editor"])

# -------- Pages --------
@router.get("", dependencies=[Depends(require_view)])
async def image_editor_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    # Pass necessary data for rendering image editor
    ctx: Dict[str, Any] = {
        "request": request,
        "title": "Image Editor",
        "flashes": await flash_popall(request.session),
    }

    await add_common(ctx, db, current_user, request=request)
    return await render("admin/image_editor/form.html", ctx)