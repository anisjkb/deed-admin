# src/backend/utils/flash.py
from __future__ import annotations

import json
from typing import Any, Coroutine, Dict, List, MutableMapping, Optional, cast

from starlette.responses import RedirectResponse

# ✅ make sure this is the ASYNC client, not redis.Redis
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from src.backend.config import settings

Session = MutableMapping[str, Any]
_FLASH_SESSION_KEY = "flashq"

_redis: Optional[Redis] = None
_REDIS_OK: bool = True


def _get_redis() -> Optional[Redis]:
    """Create and cache an asyncio Redis client (no network I/O here)."""
    global _redis, _REDIS_OK
    if not _REDIS_OK:
        return None
    if _redis is None:
        try:
            _redis = Redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,  # str in/out
            )
        except Exception:
            _REDIS_OK = False
            _redis = None
    return _redis


async def _redis_available() -> bool:
    """
    True if Redis is reachable. We pin failures to this process lifetime.
    """
    global _REDIS_OK
    if not _REDIS_OK:
        return False
    r = _get_redis()
    if not r:
        _REDIS_OK = False
        return False
    try:
        # Some stubsets confuse Pylance; cast to Coroutine to keep it happy.
        ok = await cast(Coroutine[Any, Any, bool], r.ping())
        if not ok:
            _REDIS_OK = False
        return ok
    except Exception:
        _REDIS_OK = False
        return False


async def flash_add(session: Session, category: str, text: str) -> None:
    """
    Add a flash message. Prefer Redis per-session list; if Redis is down,
    store on the session under _FLASH_SESSION_KEY.
    """
    item: Dict[str, str] = {"category": category, "message": text}

    if await _redis_available():
        try:
            r = _get_redis()
            if r is not None:
                sid = (
                    str(session.get("_session_id"))
                    or str(session.get("session"))
                    or "sid"
                )
                key = f"{settings.FLASH_PREFIX}{sid}"

                # rpush / expire are coroutines at runtime; cast keeps Pylance quiet.
                await cast(Coroutine[Any, Any, int], r.rpush(key, json.dumps(item)))
                await cast(
                    Coroutine[Any, Any, bool],
                    r.expire(key, int(settings.FLASH_TTL)),
                )
                return
        except (RedisConnectionError, OSError):
            pass
        except Exception:
            pass

    # ---- Session fallback (no awaits here!) ----
    stack: List[Dict[str, str]] = list(session.get(_FLASH_SESSION_KEY, []))
    stack.append(item)
    session[_FLASH_SESSION_KEY] = stack


async def flash_popall(session: Session) -> List[Dict[str, str]]:
    """
    Pop all flash messages and return them.
    Uses Redis if available, otherwise session fallback.
    """
    if await _redis_available():
        try:
            r = _get_redis()
            if r is not None:
                sid = (
                    str(session.get("_session_id"))
                    or str(session.get("session"))
                    or "sid"
                )
                key = f"{settings.FLASH_PREFIX}{sid}"

                msgs: List[Dict[str, str]] = []
                while True:
                    raw = await cast(
                        Coroutine[Any, Any, Optional[str]],
                        r.lpop(key),
                    )
                    if raw is None:
                        break
                    try:
                        decoded = json.loads(raw) if isinstance(raw, str) else None
                        if isinstance(decoded, dict):
                            msgs.append(
                                {
                                    "category": str(decoded.get("category", "")),
                                    "message": str(decoded.get("message", "")),
                                }
                            )
                    except Exception:
                        # swallow malformed entries
                        pass
                return msgs
        except (RedisConnectionError, OSError):
            pass
        except Exception:
            pass

    # ---- Session fallback (no awaits here!) ----
    stack_any = session.pop(_FLASH_SESSION_KEY, [])
    msgs: List[Dict[str, str]] = []
    if isinstance(stack_any, list):
        for it in stack_any:
            if isinstance(it, dict):
                msgs.append(
                    {
                        "category": str(it.get("category", "")),
                        "message": str(it.get("message", "")),
                    }
                )
    return msgs

async def redirect_with_flash(
    session: Session,
    url: str,
    category: str,
    text: str,
    status_code: int = 303,
):
    """Add a flash then return a redirect response."""
    await flash_add(session, category, text)
    return RedirectResponse(url, status_code=status_code)