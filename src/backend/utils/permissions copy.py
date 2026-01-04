# src/backend/utils/permissions.py
from __future__ import annotations

import logging
from typing import Optional, Callable, Dict, Any

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.utils.auth import get_current_user
from src.backend.utils.database import get_db
from src.backend.models.user import User
from src.backend.models.security.menu import Menu
from src.backend.models.security.right import Right

logger = logging.getLogger(__name__)

# map friendly names -> Right columns
_PERMIT_COL = {
    "view": "view_permit",
    "create": "create_permit",
    "edit": "edit_permit",
    "delete": "delete_permit",
}


def _state_get(request: Request, key: str) -> Any:
    try:
        return getattr(request.state, key)
    except Exception:
        return None


def _state_set(request: Request, key: str, value: Any) -> None:
    try:
        setattr(request.state, key, value)
    except Exception:
        pass


async def _resolve_active_menu_for_path(db: AsyncSession, path_no_slash: str) -> Optional[Menu]:
    """
    Find the active Menu whose URL is the longest prefix of the current path.
    Only returns if Menu.status='active' AND Menu.active_flag='Y'.
    """
    res = await db.execute(
        select(Menu).where(
            Menu.status == "active",
            Menu.active_flag == "Y",
        )
    )

    best: Optional[Menu] = None
    best_len = -1

    for m in res.scalars().all():
        url = (m.url or "").lstrip("/")
        if not url:
            continue
        if path_no_slash == url or path_no_slash.startswith(url + "/"):
            L = len(url)
            if L > best_len:
                best = m
                best_len = L

    return best


async def _get_right_row(db: AsyncSession, role_id: str, menu_id: str) -> Optional[Right]:
    """
    Fetch ONE active Right row for (role_id, menu_id).
    Use .first() to avoid crashing if duplicates exist in DB.
    """
    res = await db.execute(
        select(Right).where(
            Right.role_id == role_id,
            Right.menu_id == menu_id,
            Right.status == "active",
        )
    )
    return res.scalars().first()


async def ensure_request_perms(db: AsyncSession, user: User, request: Request) -> Dict[str, bool]:
    """
    ✅ Compute perms ONCE per request and store in request.state.perms.
    Any subsequent call in the same request returns cached value without DB hits.
    """
    cached = _state_get(request, "perms")
    if isinstance(cached, dict) and {"view", "create", "edit", "delete"}.issubset(cached.keys()):
        return cached

    # default perms
    out = {"view": False, "create": False, "edit": False, "delete": False}

    path = request.url.path.lstrip("/")
    if not path.startswith("admin/"):
        _state_set(request, "perms", out)
        return out

    role_id = (getattr(user, "role_id", "") or "").strip()
    if not role_id:
        _state_set(request, "perms", out)
        return out

    # --- DB HIT(s) happen below this line (menu + rights) ---
    menu = await _resolve_active_menu_for_path(db, path)
    if not menu:
        _state_set(request, "perms", out)
        return out

    r = await _get_right_row(db, role_id, str(menu.menu_id))
    if not r:
        _state_set(request, "perms", out)
        return out

    out["view"] = (getattr(r, "view_permit", "N") or "N") == "Y"
    out["create"] = (getattr(r, "create_permit", "N") or "N") == "Y"
    out["edit"] = (getattr(r, "edit_permit", "N") or "N") == "Y"
    out["delete"] = (getattr(r, "delete_permit", "N") or "N") == "Y"

    # ✅ store once for the whole request
    _state_set(request, "perms", out)

    # ✅ THIS is the correct place to add your debug line:
    logger.debug("PERMS COMPUTED (db hit) path=%s", request.url.path)

    return out


def require_perm(permit: str) -> Callable:
    """
    FastAPI dependency enforcing the given permit against the current URL.
    Uses request.state.perms so it does NOT re-hit DB multiple times in one request.
    """
    if permit not in _PERMIT_COL:
        raise ValueError(f"Unknown permit '{permit}'")

    async def _dep(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> None:
        path = request.url.path.lstrip("/")
        if not path.startswith("admin/"):
            return

        perms = await ensure_request_perms(db, current_user, request)
        allowed = bool(perms.get(permit, False))
        if not allowed:
            logger.warning(
                "403(permit denied): role=%s permit=%s path=%s",
                getattr(current_user, "role_id", None),
                permit,
                path,
            )
            raise HTTPException(status_code=403, detail="Forbidden")

    return _dep


# nice shorthands
require_view = require_perm("view")
require_create = require_perm("create")
require_edit = require_perm("edit")
require_delete = require_perm("delete")


async def perms_for_request(db: AsyncSession, user: User, request: Request) -> Dict[str, bool]:
    """
    Backward compatible wrapper.
    ✅ Now reuses request.state.perms, so it won't do duplicate DB work.
    """
    return await ensure_request_perms(db, user, request)