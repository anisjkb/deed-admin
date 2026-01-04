# src/backend/utils/common_context.py
from __future__ import annotations

from typing import Any, Dict, Optional
import logging

from fastapi import HTTPException, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.models.user import User
from src.backend.models.org.emp_info import EmpInfo
from src.backend.models.ops.feedback import Feedback

from src.backend.utils.permissions import ensure_request_perms
from src.backend.utils.menu_cache import (
    get_cached_visible_menus_and_tree,
    invalidate_role_menu_cache,
)

# Fallback direct imports (only used when cache returns empty)
from src.backend.crud.menu import get_visible_menus_for_role, build_menu_tree

logger = logging.getLogger(__name__)


def require_admin(user: User) -> None:
    if not getattr(user, "role_id", None):
        raise HTTPException(status_code=403, detail="Forbidden")


def _get(obj: Any, key: str, default: Any = None) -> Any:
    try:
        if isinstance(obj, dict):
            return obj.get(key, default)
        if hasattr(obj, "get") and callable(getattr(obj, "get")):
            return obj.get(key, default)  # type: ignore[attr-defined]
        return getattr(obj, key, default)
    except Exception:
        return default


async def add_common(
    ctx: Dict[str, Any],
    db: AsyncSession,
    current_user: User,
    request: Optional[Request] = None,
) -> None:
    try:
        # Display name
        emp_name = await db.scalar(
            select(EmpInfo.emp_name).where(EmpInfo.emp_id == current_user.emp_id)
        )
        display_name = emp_name or current_user.login_id

        role_id = (getattr(current_user, "role_id", "") or "").strip()

        # ✅ perms once per request
        perms: Dict[str, bool] = {"view": False, "create": False, "edit": False, "delete": False}
        if request is not None:
            perms = await ensure_request_perms(request, current_user, db)

        # ✅ sidebar menus (cached)
        flat, menu_tree = await get_cached_visible_menus_and_tree(db, role_id) if role_id else ([], [])

        # 🔥 If cache returned empty, force rebuild ONCE (prevents “stuck empty”)
        if role_id and not flat:
            logger.warning("Menu cache returned empty for role_id=%r -> forcing rebuild", role_id)
            invalidate_role_menu_cache(role_id)
            flat = await get_visible_menus_for_role(db, role_id)
            menu_tree = build_menu_tree(flat) if flat else []

        ctx.update(
            {
                "current_user": current_user,
                "display_name": display_name,
                "menu_tree": menu_tree,
                "perms": perms,
            }
        )

        # Debug snapshot
        visible_menu_urls = []
        for m in (flat or [])[:80]:
            u = (_get(m, "url", "") or "").lstrip("/").rstrip("/")
            if u and u != "#":
                visible_menu_urls.append(u)

        logger.debug(
            "add_common(): login_id=%r role_id=%r visible_menu_urls(sample)=%r",
            getattr(current_user, "login_id", None),
            role_id,
            visible_menu_urls[:20],
        )

        # --- Feedback notification (keep it safe and fast) ---
        # If you want it permission-based later, we can wire it to menus/rights.
        can_view_feedback = True

        notif_feedback_unread_count = 0
        if can_view_feedback:
            unread_count_res = await db.execute(
                select(func.count(Feedback.id)).where(Feedback.is_read.is_(False))
            )
            notif_feedback_unread_count = int(unread_count_res.scalar_one() or 0)

        ctx.update(
            {
                "can_view_feedback": can_view_feedback,
                "notif_feedback_unread_count": notif_feedback_unread_count,
                "notif_feedback_count": notif_feedback_unread_count,
            }
        )

        logger.warning(
            "User %s can view feedback: %s | unread=%s",
            getattr(current_user, "login_id", None),
            can_view_feedback,
            notif_feedback_unread_count,
        )

    except Exception:
        logger.exception("add_common(): failed")
        raise