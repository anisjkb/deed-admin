# src/backend/utils/security.py
from __future__ import annotations

import os
import hashlib
import time
from typing import Optional, Dict, Any

from dotenv import load_dotenv
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException

load_dotenv()

# ---- JWT settings (from .env) ----
JWT_SECRET: str = os.getenv("JWT_SECRET", "change-this-in-prod")
JWT_ALG: str = os.getenv("JWT_ALG", "HS256")

ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "14"))

# Clock skew tolerance (seconds)
CLOCK_SKEW_LEEWAY: int = int(os.getenv("JWT_LEEWAY_SECONDS", "30"))

# Optional debug
AUTH_DEBUG: bool = os.getenv("AUTH_DEBUG", "0") in ("1", "true", "True", "yes", "YES")


# ---- Password hashing policy ----
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated="auto",
)

# ---------------------------------------------------------------------
# Password Handling
# ---------------------------------------------------------------------
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _looks_sha256(hexstr: str) -> bool:
    return (
        isinstance(hexstr, str)
        and len(hexstr) == 64
        and all(c in "0123456789abcdef" for c in hexstr.lower())
    )


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        if pwd_context.identify(hashed):
            return pwd_context.verify(plain, hashed)
    except Exception:
        pass

    # legacy fallback (old DB values stored as raw sha256 hex)
    if _looks_sha256(hashed):
        return hashlib.sha256(plain.encode()).hexdigest() == hashed

    return False


def needs_rehash(hashed: str) -> bool:
    if _looks_sha256(hashed):
        return True
    try:
        return pwd_context.needs_update(hashed)
    except Exception:
        return True


# ---------------------------------------------------------------------
# Token Handling - Access Token
# ---------------------------------------------------------------------
def create_access_token(data: Dict[str, Any], minutes: Optional[int] = None) -> str:
    """
    Create a short-lived JWT access token.
    Uses epoch seconds to avoid timezone/datetime issues.
    """
    now_ts = int(time.time())
    exp_ts = now_ts + int(60 * (minutes or ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {**data, "iat": now_ts, "exp": exp_ts}

    if AUTH_DEBUG:
        print(">>> create_access_token", {"iat": now_ts, "exp": exp_ts, "sub": data.get("sub")})

    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALG)


def _check_exp_with_leeway(payload: Dict[str, Any]) -> None:
    exp = payload.get("exp")
    if exp is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    now = int(time.time())
    if now > int(exp) + CLOCK_SKEW_LEEWAY:
        raise HTTPException(status_code=401, detail="Token expired")


def _decode_ignoring_exp(token: str) -> Dict[str, Any]:
    """
    Decode but skip built-in exp verification; we enforce exp with our own leeway.
    python-jose doesn't accept the PyJWT 'leeway=' kwarg.
    """
    return jwt.decode(
        token,
        JWT_SECRET,
        algorithms=[JWT_ALG],
        options={"verify_aud": False, "verify_exp": False},
    )


def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Return payload or None (no exceptions)."""
    try:
        payload = _decode_ignoring_exp(token)
        _check_exp_with_leeway(payload)
        return payload
    except HTTPException:
        return None
    except JWTError:
        return None


def decode_access_token(token: str) -> Dict[str, Any]:
    """Return payload or raise HTTPException(401)."""
    try:
        payload = _decode_ignoring_exp(token)
        _check_exp_with_leeway(payload)
        return payload
    except HTTPException:
        raise
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ---------------------------------------------------------------------
# Token Handling - Refresh Token (for idle sessions + max session age)
# ---------------------------------------------------------------------
def create_refresh_token(
    data: Dict[str, Any],
    session_start_ts: Optional[int] = None,
    days: Optional[int] = None,
) -> str:
    """
    Create a refresh token that enforces MAX SESSION AGE via immutable 'session_start'.
    - session_start: fixed on login
    - exp: based on session_start + REFRESH_TOKEN_EXPIRE_DAYS
    """
    now_ts = int(time.time())
    session_start = int(session_start_ts or now_ts)
    max_days = int(days or REFRESH_TOKEN_EXPIRE_DAYS)
    exp_ts = session_start + (max_days * 86400)

    to_encode = {
        **data,
        "iat": session_start,          # fixed
        "session_start": session_start, # fixed (used for absolute max age)
        "exp": exp_ts,                # fixed absolute expiry
    }

    if AUTH_DEBUG:
        print(">>> create_refresh_token", {"session_start": session_start, "exp": exp_ts, "sub": data.get("sub")})

    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALG)


def decode_refresh_token(token: str) -> Dict[str, Any]:
    """
    Decode refresh token.
    Uses exp verification OFF and checks exp+leeway ourselves to avoid clock skew issues.
    """
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALG],
            options={"verify_aud": False, "verify_exp": False},
        )
        _check_exp_with_leeway(payload)
        return payload
    except HTTPException:
        raise
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def verify_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Return payload or None.
    Also enforces 'max session age' by comparing now vs session_start.
    """
    try:
        payload = decode_refresh_token(token)

        # Enforce immutable max session age (absolute cap)
        session_start = payload.get("session_start")
        if not session_start:
            return None

        now = int(time.time())
        max_age_seconds = int(REFRESH_TOKEN_EXPIRE_DAYS) * 86400

        if now - int(session_start) > max_age_seconds + CLOCK_SKEW_LEEWAY:
            return None

        return payload
    except HTTPException:
        return None