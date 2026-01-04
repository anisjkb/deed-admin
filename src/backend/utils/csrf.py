# src/backend/utils/csrf.py
from __future__ import annotations
import os, secrets
from typing import Optional
from fastapi import Request, HTTPException
from fastapi.responses import Response

CSRF_COOKIE_NAME = os.getenv("CSRF_COOKIE_NAME", "XSRF-TOKEN")
CSRF_HEADER_NAME = os.getenv("CSRF_HEADER_NAME", "X-CSRF-Token")
CSRF_FORM_FIELD  = os.getenv("CSRF_FORM_FIELD", "csrf_token")
IS_PROD = os.getenv("ENV", "dev").lower() == "prod"

def ensure_csrf_cookie(resp: Response, request: Request) -> None:
    # don't rotate on each GET
    if CSRF_COOKIE_NAME in request.cookies:
        return
    # use urlsafe like the values you see in the browser
    token = secrets.token_urlsafe(32)
    resp.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        httponly=False,                         # JS must read it for header/fetch cases
        samesite="none" if IS_PROD else "lax",
        secure=IS_PROD,
        path="/",
    )

async def csrf_protect(request: Request) -> None:
    # skip safe methods
    if request.method in {"GET", "HEAD", "OPTIONS", "TRACE"}:
        return

    cookie_val: Optional[str] = request.cookies.get(CSRF_COOKIE_NAME)
    if not cookie_val:
        raise HTTPException(status_code=403, detail="CSRF cookie missing")

    # Prefer header, but allow classic form field
    token: Optional[str] = request.headers.get(CSRF_HEADER_NAME)
    if not token:
        ctype = (request.headers.get("content-type") or "").lower()
        if "application/x-www-form-urlencoded" in ctype or "multipart/form-data" in ctype:
            form = await request.form()
            value = form.get(CSRF_FORM_FIELD)
            token = value if isinstance(value, str) else None

    if not token or token != cookie_val:
        raise HTTPException(status_code=403, detail="CSRF token missing or invalid")
