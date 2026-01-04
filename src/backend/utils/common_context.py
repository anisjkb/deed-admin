# src/backend/utils/common_context.py
from typing import Any, Dict, Optional
import logging

from fastapi import HTTPException, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.utils.menu_cache import get_cached_visible_menus_and_tree
from src.backend.utils.permissions import ensure_request_perms
from src.backend.models.user import User
from src.backend.models.org.emp_info import EmpInfo
from src.backend.models.ops.feedback import Feedback

logger = logging.getLogger(__name__)


def require_admin(user: User) -> None:
    if not getattr(user, "role_id", None):
        raise HTTPException(status_code=403, detail="Forbidden")


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """
    Safe getter for dict/RowMapping/ORM objects.
    """
    try:
        if isinstance(obj, dict):
            return obj.get(key, default)
        if hasattr(obj, "get") and callable(getattr(obj, "get")):
            try:
                return obj.get(key, default)
            except Exception:
                pass
        return getattr(obj, key, default)
    except Exception:
        return default


def _has_menu_url(flat_menus: list, target: str) -> Optional[str]:
    """
    Detect if a URL exists in visible menus by URL match (robust).
    Returns matched URL (normalized) or None.
    """
    t = (target or "").lstrip("/").rstrip("/")
    if not t:
        return None

    for m in flat_menus or []:
        raw_url = _get(m, "url", "") or ""
        u = raw_url.lstrip("/").rstrip("/")
        if not u or u == "#":
            continue

        # Accept both "admin/feedback" and "feedback"
        if u == t:
            return u
        if u.endswith("/" + t):
            return u

    return None


def _can_view_feedback_from_visible_menus(role_id: str, flat_menus: list) -> bool:
    """
    ZERO DB HIT:
    If feedback URL is in role-visible menus, it is already rights-filtered.
    """
    if not role_id:
        return False

    matched = _has_menu_url(flat_menus, "admin/feedback") or _has_menu_url(flat_menus, "feedback")
    return bool(matched)


async def add_common(
    ctx: Dict[str, Any],
    db: AsyncSession,
    current_user: User,
    request: Optional[Request] = None,
) -> None:
    """
    ✅ IMPORTANT RULE:
    - add_common() computes perms at most once per request (via request.state.perms)
    - routes must NOT call perms_for_request() again after add_common()
    """
    try:
        emp_name = await db.scalar(
            select(EmpInfo.emp_name).where(EmpInfo.emp_id == current_user.emp_id)
        )
        display_name = emp_name or current_user.login_id

        role_id = (getattr(current_user, "role_id", "") or "").strip()

        # ✅ menu cached per role (TTL) to avoid repeated joins
        flat, menu_tree = await get_cached_visible_menus_and_tree(db, role_id)

        # ✅ perms computed ONCE per request and stored in request.state.perms
        perms = {"view": False, "create": False, "edit": False, "delete": False}
        if request is not None:
            perms = await ensure_request_perms(db, current_user, request)

        ctx.update(
            {
                "current_user": current_user,
                "display_name": display_name,
                "menu_tree": menu_tree,
                "perms": perms,
            }
        )

        # Optional debug snapshot
        try:
            flat_urls = []
            for m in flat[:60]:
                u = (_get(m, "url", "") or "").lstrip("/").rstrip("/")
                if u and u != "#":
                    flat_urls.append(u)
            logger.debug(
                "add_common(): login_id=%r role_id=%r visible_menu_urls(sample)=%s",
                getattr(current_user, "login_id", None),
                role_id,
                flat_urls[:30],
            )
        except Exception:
            pass

        # ✅ feedback permission check = zero extra rights DB queries
        can_view_feedback = _can_view_feedback_from_visible_menus(role_id, flat)

        # Default safe values
        notif_feedback_unread_count = 0
        notif_feedback_unread_oldest = []

        # Only hit DB if the user can see feedback menu
        if can_view_feedback:
            unread_count_res = await db.execute(
                select(func.count(Feedback.id)).where(Feedback.is_read.is_(False))
            )
            notif_feedback_unread_count = int(unread_count_res.scalar_one() or 0)

            unread_list_res = await db.execute(
                select(Feedback)
                .where(Feedback.is_read.is_(False))
                .order_by(Feedback.created_at.asc(), Feedback.id.asc())
                .limit(10)
            )
            notif_feedback_unread_oldest = list(unread_list_res.scalars().all())

        logger.warning(
            "User %s can view feedback: %s | unread=%s",
            getattr(current_user, "login_id", ""),
            can_view_feedback,
            notif_feedback_unread_count,
        )
        logger.debug(
            "Unread feedback details: %s",
            [getattr(x, "id", None) for x in notif_feedback_unread_oldest],
        )

        ctx.update(
            {
                "can_view_feedback": can_view_feedback,
                "notif_feedback_unread_count": notif_feedback_unread_count,
                "notif_feedback_unread_oldest": notif_feedback_unread_oldest,
                # backward compatible keys used in templates
                "notif_feedback_count": notif_feedback_unread_count,
                "notif_feedback": notif_feedback_unread_oldest,
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")