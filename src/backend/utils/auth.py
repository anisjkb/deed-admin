# src/backend/utils/auth.py
from __future__ import annotations

import os, hmac, hashlib, secrets, time, asyncio, re
from typing import Optional, Tuple, Literal, cast

import requests
from dotenv import load_dotenv
from fastapi import Request, Depends, HTTPException
from fastapi.responses import JSONResponse, Response
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.models.user import User
from src.backend.models.refresh_token import RefreshToken
from src.backend.models.user_activity_log import UserActivityLog

from src.backend.utils.database import get_db
from src.backend.utils.security import (
    create_access_token,
    verify_password,
    hash_password,
    needs_rehash,
    decode_access_token,
    JWT_SECRET,
)
from src.backend.utils.timezone import now_local

load_dotenv()

# -------------------------------------------------------------------
# Geolocation (non-blocking + optional)
# -------------------------------------------------------------------

def _parse_bool_env(name: str, default: bool) -> bool:
    v = (os.getenv(name) or "").strip().lower()
    if not v:
        return default
    return v in ("1", "true", "yes", "y", "on")

def _parse_float_env(name: str, default: float) -> float:
    """Parse float envs safely.

    Accepts values like:
      - "0.15"
      - "0.15  # comment"
      - "0.15 (even faster if enabled)"
    """
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    m = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", raw)
    if not m:
        return default
    try:
        return float(m.group(0))
    except Exception:
        return default

def _parse_int_env(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    m = re.search(r"[-+]?\d+", raw)
    if not m:
        return default
    try:
        return int(m.group(0))
    except Exception:
        return default

# If disabled, auth/login should never wait on external network.
GEOLOOKUP_ENABLED: bool = _parse_bool_env("GEOLOOKUP_ENABLED", False)
# Keep very small when enabled; this is for best-effort enrichment only.
GEOLOOKUP_TIMEOUT_SECONDS: float = _parse_float_env("GEOLOOKUP_TIMEOUT_SECONDS", 0.20)
GEOLOOKUP_TTL_SECONDS: int = _parse_int_env("GEOLOOKUP_TTL_SECONDS", 3600)

# Small in-memory cache (IP -> (expires_ts, payload_dict))
_GEO_CACHE: dict[str, tuple[float, dict]] = {}

# -------------------------------------------------------------------
# Config
# -------------------------------------------------------------------
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "14"))

# ✅ HARD SESSION LIMIT (absolute max age), ENV-driven
# - Default: 30 days
# - Set SESSION_MAX_AGE_DAYS=0 to disable hard limit
SESSION_MAX_AGE_DAYS: int = int(os.getenv("SESSION_MAX_AGE_DAYS", "30"))

COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "false").lower() in ("1", "true", "yes")

_samesite_env = (os.getenv("COOKIE_SAMESITE", "Lax") or "Lax").strip().lower()
if _samesite_env not in ("lax", "strict", "none"):
    _samesite_env = "lax"

# ✅ Browsers require SameSite=None cookies to also be Secure
if _samesite_env == "none" and not COOKIE_SECURE:
    _samesite_env = "lax"

COOKIE_SAMESITE: Optional[Literal["lax", "strict", "none"]] = cast(
    Optional[Literal["lax", "strict", "none"]], _samesite_env
)

_cookie_domain_raw = (os.getenv("COOKIE_DOMAIN") or "").strip()
COOKIE_DOMAIN: Optional[str] = _cookie_domain_raw if _cookie_domain_raw else None

ACCESS_COOKIE_NAME  = "access_token"
REFRESH_COOKIE_NAME = "refresh_token"
CSRF_COOKIE_NAME    = "XSRF-TOKEN"

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def _get_header(request: Request, name: str) -> Optional[str]:
    val = request.headers.get(name)
    return val if isinstance(val, str) else None

def _get_cookie(request: Request, name: str) -> Optional[str]:
    val = request.cookies.get(name)
    return val if isinstance(val, str) else None

def _cookie_kwargs() -> dict:
    """
    Build cookie kwargs safely.
    - Include domain ONLY if it's set (avoids weird Set-Cookie)
    - path=/ so /admin routes receive cookies
    """
    kw = {
        "secure": COOKIE_SECURE,
        "samesite": COOKIE_SAMESITE,
        "path": "/",
    }
    if COOKIE_DOMAIN:
        kw["domain"] = COOKIE_DOMAIN
    return kw

def _delete_cookie_safely(response: Response, key: str) -> None:
    """
    Delete cookie robustly:
    - If domain is set, delete with domain.
    - Also delete without domain, to handle cookies set without domain.
    """
    response.delete_cookie(key, path="/")
    if COOKIE_DOMAIN:
        response.delete_cookie(key, domain=COOKIE_DOMAIN, path="/")

# -------------------------------------------------------------------
# CSRF
# -------------------------------------------------------------------
def ensure_csrf_cookie(response: Response, request: Request) -> None:
    if _get_cookie(request, CSRF_COOKIE_NAME):
        return
    token = secrets.token_urlsafe(32)
    response.set_cookie(
        CSRF_COOKIE_NAME,
        token,
        httponly=False,  # must be JS-readable
        max_age=7 * 24 * 3600,
        **_cookie_kwargs(),
    )

async def csrf_protect(request: Request):
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        header = _get_header(request, "X-CSRF-Token")
        cookie = _get_cookie(request, CSRF_COOKIE_NAME)
        if not header or not cookie or header != cookie:
            raise HTTPException(status_code=403, detail="CSRF token missing or invalid")

# -------------------------------------------------------------------
# Cookie helpers
# -------------------------------------------------------------------
def _hmac_hash(raw: str) -> str:
    return hmac.new(JWT_SECRET.encode(), raw.encode(), hashlib.sha256).hexdigest()

def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        raw_token,
        httponly=True,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        **_cookie_kwargs(),
    )

def _clear_refresh_cookie(response: Response) -> None:
    _delete_cookie_safely(response, REFRESH_COOKIE_NAME)

def _set_access_cookie(response: Response, access_token: str, max_age_seconds: int) -> None:
    response.set_cookie(
        ACCESS_COOKIE_NAME,
        access_token,
        httponly=True,
        max_age=max_age_seconds,
        **_cookie_kwargs(),
    )

def _clear_access_cookie(response: Response) -> None:
    _delete_cookie_safely(response, ACCESS_COOKIE_NAME)

# -------------------------------------------------------------------
# Activity logging
# -------------------------------------------------------------------
def _get_client_ip(request: Request) -> str:
    """Best-effort client IP with proxy header support."""
    xff = _get_header(request, "X-Forwarded-For")
    if xff:
        ip = xff.split(",")[0].strip()
        if ip:
            return ip
    xri = _get_header(request, "X-Real-IP")
    if xri:
        return xri.strip()
    cfip = _get_header(request, "CF-Connecting-IP")
    if cfip:
        return cfip.strip()
    return request.client.host if (request and request.client and request.client.host) else "0.0.0.0"

def _is_public_ip(ip: str) -> bool:
    if not ip:
        return False
    ip = ip.strip()
    if ip == "::1":
        return False
    if ip.startswith("127."):
        return False
    if ip.startswith("10."):
        return False
    if ip.startswith("192.168."):
        return False
    if ip.startswith("172."):
        try:
            second = int(ip.split(".")[1])
            if 16 <= second <= 31:
                return False
        except Exception:
            pass
    return True

def _geolocate_cached(ip: str) -> tuple[str, str, dict]:
    """Fast best-effort geo lookup with TTL cache.
    Returns: (city, country, full_payload_dict)
    """
    if not GEOLOOKUP_ENABLED:
        return "Unknown", "Unknown", {"geo_enabled": False}

    if not _is_public_ip(ip):
        return "Unknown", "Unknown", {"geo_enabled": True, "skipped": True, "reason": "non-public ip", "ip": ip}

    now_ts = time.time()
    cached = _GEO_CACHE.get(ip)
    if cached and cached[0] > now_ts:
        payload = cached[1]
        city = (payload.get("city") or "Unknown") if isinstance(payload, dict) else "Unknown"
        country = (payload.get("country_name") or "Unknown") if isinstance(payload, dict) else "Unknown"
        return city, country, payload

    payload: dict = {}
    try:
        r = requests.get(
            f"https://ipapi.co/{ip}/json/",
            timeout=max(0.05, float(GEOLOOKUP_TIMEOUT_SECONDS)),
        )
        if r.status_code == 200:
            j = r.json() if hasattr(r, "json") else {}
            payload = j if isinstance(j, dict) else {}
        else:
            payload = {"geo_enabled": True, "status_code": r.status_code, "ip": ip}
    except Exception as e:
        payload = {"geo_enabled": True, "error": str(e), "ip": ip}

    _GEO_CACHE[ip] = (now_ts + max(5, int(GEOLOOKUP_TTL_SECONDS)), payload)

    city = (payload.get("city") or "Unknown") if isinstance(payload, dict) else "Unknown"
    country = (payload.get("country_name") or "Unknown") if isinstance(payload, dict) else "Unknown"
    return city, country, payload

async def _log_activity(db: AsyncSession, user: User, request: Request, event: str, ok=True, risk=0.0, extra=None):
    ip = _get_client_ip(request)
    ua = _get_header(request, "User-Agent") or "Unknown"

    # Geo lookup is optional and time-bounded; disabled by default.
    city, country, geo_payload = _geolocate_cached(ip)

    extra_payload = {}
    if isinstance(extra, dict):
        extra_payload.update(extra)
    extra_payload.setdefault("geo", geo_payload)

    log = UserActivityLog(
        login_id=user.login_id,
        event_type=event,
        ip_address=ip,
        device_info=ua[:255],
        user_agent=ua,
        geolocation_city=city,
        geolocation_country=country,
        login_success=ok,
        risk_score=risk,
        extra_info=extra_payload,
    )
    db.add(log)
    await db.commit()

# -------------------------------------------------------------------
# Core auth
# -------------------------------------------------------------------
async def authenticate_user(db: AsyncSession, login_id: str, password: str) -> Optional[User]:
    login_id = (login_id or "").strip()
    if not login_id or not password:
        return None

    user = await db.scalar(select(User).where(User.login_id == login_id))
    if not user:
        return None

    stored_hash = cast(str, user.password)
    if not verify_password(password, stored_hash):
        return None

    try:
        if needs_rehash(stored_hash):
            setattr(user, "password", hash_password(password))
            db.add(user)
            await db.commit()
    except Exception:
        pass

    return user

# -------------------------------------------------------------------
# 🔐 Refresh token issue/rotate with session_start
# -------------------------------------------------------------------
def _get_session_start_from_token_row(token_row: RefreshToken) -> Optional[int]:
    try:
        v = getattr(token_row, "session_start", None)
        return int(v) if v is not None else None
    except Exception:
        return None

def _set_session_start_on_token_row(token_row: RefreshToken, session_start: int) -> None:
    try:
        setattr(token_row, "session_start", int(session_start))
    except Exception:
        pass

def _enforce_hard_session_limit_if_enabled(session_start: Optional[int]) -> None:
    if SESSION_MAX_AGE_DAYS <= 0:
        return
    if session_start is None:
        return

    now_ts = int(time.time())
    max_age_seconds = int(SESSION_MAX_AGE_DAYS) * 86400
    if (now_ts - int(session_start)) > max_age_seconds:
        raise HTTPException(status_code=401, detail="Session expired")

async def _issue_refresh(
    db: AsyncSession,
    user: User,
    request: Request,
    session_start: Optional[int] = None,
) -> str:
    raw = secrets.token_urlsafe(64)
    ip = _get_client_ip(request)
    ua = (_get_header(request, "User-Agent") or "Unknown")[:255]

    token_db = RefreshToken(
        login_id=user.login_id,
        token_hash=_hmac_hash(raw),
        device_info=ua,
        ip_address=ip,
        expires_at=now_local() + __import__("datetime").timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        is_revoked=False,
    )

    if session_start is not None:
        _set_session_start_on_token_row(token_db, session_start)

    db.add(token_db)
    await db.commit()
    return raw

async def issue_tokens_response(db: AsyncSession, user: User, request: Request) -> JSONResponse:
    session_start = int(time.time())

    access = create_access_token({"sub": str(user.login_id)})
    raw_refresh = await _issue_refresh(db, user, request, session_start=session_start)

    resp = JSONResponse({
        "access_token": access,
        "token_type": "bearer",
        "user": {
            "login_id": user.login_id,
            "email": user.email,
            "role_id": user.role_id,
        }
    })

    _set_access_cookie(resp, access, ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    _set_refresh_cookie(resp, raw_refresh)
    ensure_csrf_cookie(resp, request)

    await _log_activity(db, user, request, "login", ok=True)
    return resp

async def registration_response(db: AsyncSession, user: User, request: Request) -> JSONResponse:
    session_start = int(time.time())

    access = create_access_token({"sub": str(user.login_id)})
    raw_refresh = await _issue_refresh(db, user, request, session_start=session_start)

    resp = JSONResponse({
        "access_token": access,
        "token_type": "bearer",
        "user": {
            "login_id": user.login_id,
            "email": user.email,
            "role_id": user.role_id,
        }
    })

    _set_access_cookie(resp, access, ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    _set_refresh_cookie(resp, raw_refresh)
    ensure_csrf_cookie(resp, request)

    await _log_activity(db, user, request, "registration", ok=True)
    return resp

async def rotate_refresh_response(db: AsyncSession, request: Request) -> JSONResponse:
    raw_cookie = _get_cookie(request, REFRESH_COOKIE_NAME)
    if not raw_cookie:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    token = await db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == _hmac_hash(raw_cookie),
            RefreshToken.is_revoked.is_(False),
        )
    )
    if not token or token.expires_at < now_local():
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = await db.scalar(select(User).where(User.login_id == token.login_id))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    existing_session_start = _get_session_start_from_token_row(token)
    if existing_session_start is None:
        existing_session_start = int(time.time())

    _enforce_hard_session_limit_if_enabled(existing_session_start)

    token.is_revoked = True
    await db.commit()

    new_raw = await _issue_refresh(db, user, request, session_start=existing_session_start)
    access = create_access_token({"sub": str(user.login_id)})

    resp = JSONResponse({"access_token": access, "token_type": "bearer"})
    _set_access_cookie(resp, access, ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    _set_refresh_cookie(resp, new_raw)
    ensure_csrf_cookie(resp, request)
    return resp

async def revoke_refresh_response(db: AsyncSession, request: Request) -> JSONResponse:
    raw_cookie = _get_cookie(request, REFRESH_COOKIE_NAME)
    if raw_cookie:
        token = await db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == _hmac_hash(raw_cookie))
        )
        if token:
            token.is_revoked = True
            await db.commit()

    resp = JSONResponse({"detail": "Logged out"})
    _clear_access_cookie(resp)
    _clear_refresh_cookie(resp)
    return resp

# -------------------------------------------------------------------
# Protected dependency
# -------------------------------------------------------------------
def _extract_bearer(request: Request) -> Optional[str]:
    auth_header = _get_header(request, "Authorization")
    if auth_header:
        parts = auth_header.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()

    cookie_tok = _get_cookie(request, ACCESS_COOKIE_NAME)
    if cookie_tok:
        return cookie_tok.strip()

    return None

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    token = _extract_bearer(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = decode_access_token(token)
        sub = payload.get("sub")
        if not isinstance(sub, str) or not sub:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except HTTPException as e:
        raise e
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = await db.scalar(select(User).where(User.login_id == sub))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

async def log_rights_activity(
    db: AsyncSession,
    user: User,
    request: Request,
    event: str,
    success: bool = True,
    extra_info: Optional[dict] = None
):
    ip = _get_client_ip(request)
    ua = _get_header(request, "User-Agent") or "Unknown"
    city, country, geo_payload = _geolocate_cached(ip)

    extra_payload = {}
    if isinstance(extra_info, dict):
        extra_payload.update(extra_info)
    extra_payload.setdefault("geo", geo_payload)

    log = UserActivityLog(
        login_id=user.login_id,
        event_type=event,
        ip_address=ip,
        device_info=ua[:255],
        user_agent=ua,
        geolocation_city=city,
        geolocation_country=country,
        login_success=success,
        extra_info=extra_payload,
    )
    db.add(log)
    await db.commit()