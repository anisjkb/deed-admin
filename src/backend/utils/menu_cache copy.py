# src/backend/utils/menu_cache.py
from __future__ import annotations

import os
import time
import asyncio
import copy
import logging
import re
from collections import OrderedDict
from typing import Any, Dict, List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.crud.menu import get_visible_menus_for_role, build_menu_tree

logger = logging.getLogger(__name__)


def _env_bool(name: str, default: bool = True) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return bool(default)
    return raw in ("1", "true", "yes", "y", "on")


_FLOAT_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def _env_float(name: str, default: float) -> float:
    """
    Robust float parser:
    - Accepts: "300", "300 # comment", "0.15 (even faster)", "0.2s" -> extracts first float token
    - Falls back to default if nothing parseable
    """
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return float(default)

    # strip inline comments (support both # and ;)
    raw = raw.split("#", 1)[0].split(";", 1)[0].strip()

    m = _FLOAT_RE.search(raw)
    if not m:
        return float(default)

    try:
        return float(m.group(0))
    except Exception:
        return float(default)


def _env_int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return int(default)
    raw = raw.split("#", 1)[0].split(";", 1)[0].strip()
    m = re.search(r"[-+]?\d+", raw)
    if not m:
        return int(default)
    try:
        return int(m.group(0))
    except Exception:
        return int(default)


MENU_CACHE_ENABLED: bool = _env_bool("MENU_CACHE_ENABLED", True)
MENU_CACHE_TTL_SECONDS: float = _env_float("MENU_CACHE_TTL_SECONDS", 300.0)  # 5 minutes default
MENU_CACHE_MAX_ROLES: int = _env_int("MENU_CACHE_MAX_ROLES", 500)  # prevent unbounded growth
MENU_CACHE_DEBUG: bool = _env_bool("MENU_CACHE_DEBUG", False)

# role_id -> {"expires": float, "flat": List[dict], "tree": List[dict], "last": float}
# OrderedDict enables simple LRU eviction: newest moved to end
_CACHE: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()

# role_id -> asyncio.Lock to prevent cache stampede
_ROLE_LOCKS: Dict[str, asyncio.Lock] = {}
_LOCKS_GUARD = asyncio.Lock()


async def _get_role_lock(role_id: str) -> asyncio.Lock:
    async with _LOCKS_GUARD:
        lock = _ROLE_LOCKS.get(role_id)
        if lock is None:
            lock = asyncio.Lock()
            _ROLE_LOCKS[role_id] = lock
        return lock


def _cache_get(role_id: str, now: float) -> Tuple[List[Dict[str, Any]] | None, List[Dict[str, Any]] | None]:
    cached = _CACHE.get(role_id)
    if not cached:
        return None, None
    if float(cached.get("expires", 0)) <= now:
        return None, None

    # LRU touch
    cached["last"] = now
    _CACHE.move_to_end(role_id, last=True)

    # return deep copies so callers can’t mutate shared cache
    return copy.deepcopy(cached["flat"]), copy.deepcopy(cached["tree"])


def _cache_set(role_id: str, flat: List[Dict[str, Any]], tree: List[Dict[str, Any]]) -> None:
    now = time.time()
    ttl = max(5.0, float(MENU_CACHE_TTL_SECONDS))
    _CACHE[role_id] = {
        "expires": now + ttl,
        "flat": flat,
        "tree": tree,
        "last": now,
    }
    _CACHE.move_to_end(role_id, last=True)

    # simple LRU eviction
    max_roles = max(50, int(MENU_CACHE_MAX_ROLES))
    while len(_CACHE) > max_roles:
        _CACHE.popitem(last=False)  # remove oldest


def invalidate_role_menu_cache(role_id: str) -> None:
    """Invalidate cache for one role."""
    rid = (role_id or "").strip()
    if not rid:
        return
    _CACHE.pop(rid, None)


def invalidate_all_menu_cache() -> None:
    """Invalidate cache for all roles."""
    _CACHE.clear()


async def get_cached_visible_menus_and_tree(
    db: AsyncSession, role_id: str
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Returns (flat_visible_menus, menu_tree) for a role.

    ✅ Fast path:
      - If MENU_CACHE_ENABLED and cache not expired -> returns deep copies
    ✅ Slow path:
      - Query menus+rights join once, build tree, store cache

    Stampede-safe: only one coroutine per role does DB work at a time.
    """
    rid = (role_id or "").strip()
    if not rid:
        return [], []

    if not MENU_CACHE_ENABLED:
        if MENU_CACHE_DEBUG:
            logger.debug("MENU CACHE DISABLED -> DB HIT role_id=%s", rid)
        flat = await get_visible_menus_for_role(db, rid)
        tree = build_menu_tree(flat) if flat else []
        return flat, tree

    now = time.time()
    flat_cached, tree_cached = _cache_get(rid, now)
    if flat_cached is not None and tree_cached is not None:
        if MENU_CACHE_DEBUG:
            logger.debug("MENU CACHE HIT role_id=%s", rid)
        return flat_cached, tree_cached

    # stampede lock per role
    lock = await _get_role_lock(rid)
    async with lock:
        now2 = time.time()
        flat_cached2, tree_cached2 = _cache_get(rid, now2)
        if flat_cached2 is not None and tree_cached2 is not None:
            if MENU_CACHE_DEBUG:
                logger.debug("MENU CACHE HIT(after lock) role_id=%s", rid)
            return flat_cached2, tree_cached2

        # DB hit
        if MENU_CACHE_DEBUG:
            logger.debug("MENU CACHE MISS -> DB HIT role_id=%s", rid)

        flat = await get_visible_menus_for_role(db, rid)
        tree = build_menu_tree(flat) if flat else []

        _cache_set(rid, flat, tree)
        return copy.deepcopy(flat), copy.deepcopy(tree)