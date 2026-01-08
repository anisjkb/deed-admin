# src/backend/utils/error_handler.py
from __future__ import annotations

import logging
import inspect
from typing import Any, Dict

from fastapi import Request, HTTPException as FastAPIHTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("fastapi")


# ----------------------------------------
# LOW-SPAM TRACE HELPER (prints only key points)
# ----------------------------------------
def _trace(msg: str) -> None:
    """
    Low-spam trace. Prints file+line for the call-site that triggered _trace().
    Use only at decision/return points.
    """
    f = inspect.currentframe()
    if f and f.f_back:
        c = f.f_back
        text = f"[TRACE] {c.f_code.co_filename}:{c.f_lineno} | {msg}"
    else:
        text = f"[TRACE] <unknown> | {msg}"

    print(text)
    logger.debug(text)


def _safe_args(exc: Exception) -> str:
    try:
        a = getattr(exc, "args", None)
        return str(a) if a else "No additional details"
    except Exception:
        return "No additional details"


def _json_error(
    status_code: int,
    message: str,
    exc: Exception,
    extra: Dict[str, Any] | None = None,
) -> JSONResponse:
    """
    Unified JSON error response for APIs and non-HTML requests.
    Note: We keep professional user-facing messages here.
    """

    # Normalize user-facing message
    user_message = message
    if status_code == 401:
        user_message = "Your session has timed out for security reasons. Please log in again."
    elif status_code == 403:
        user_message = "Access denied. You do not have permission to access this page."
    elif status_code == 404:
        user_message = "The requested resource was not found."
    elif status_code == 500:
        user_message = "Internal Server Error. Please try again later."

    payload: Dict[str, Any] = {
        "message": user_message,
        "error_type": exc.__class__.__name__,
        "status_code": status_code,
    }

    if extra:
        payload.update(extra)

    _trace(f"RETURN JSONResponse | status={status_code} message={user_message!r}")
    return JSONResponse(status_code=status_code, content=payload)


def _log_http(request: Request, status_code: int, detail: str, exc: Exception) -> None:
    """
    Log levels:
    - 404 -> INFO (normal noise)
    - 401/403 -> WARNING (auth/permission)
    - other 4xx -> ERROR (client error worth checking)
    - 5xx -> EXCEPTION (stack trace)
    """
    url = str(request.url)
    method = request.method

    if status_code == 404:
        logger.info("404 Not Found: %s %s", method, url)
        return

    if status_code in (401, 403):
        logger.warning("%s: %s %s | detail=%s", status_code, method, url, detail)
        return

    if 400 <= status_code < 500:
        logger.error(
            "%s: %s %s | detail=%s | args=%s",
            status_code,
            method,
            url,
            detail,
            _safe_args(exc),
        )
        return

    logger.exception("%s: %s %s | detail=%s", status_code, method, url, detail)


def _wants_html(request: Request) -> bool:
    """
    IMPORTANT:
    - Do NOT treat Accept: */* as HTML (fetch often sends */*)
    - HTML means browser navigation (document) OR Accept includes text/html
    """
    accept = (request.headers.get("accept") or "").lower()

    if "text/html" in accept:
        return True
    if "application/json" in accept:
        return False

    # Browser navigation detection (Chromium-based)
    dest = (request.headers.get("sec-fetch-dest") or "").lower()
    mode = (request.headers.get("sec-fetch-mode") or "").lower()
    if dest == "document" or mode == "navigate":
        return True

    return False


def _is_admin_path(request: Request) -> bool:
    return request.url.path.startswith("/admin")


def _looks_like_logged_in(request: Request) -> bool:
    """
    Best-effort detection:
    - Authorization: Bearer ...
    - Common auth cookies (access/refresh/session)
    This lets us treat 403 differently:
      - logged in => stay within admin (redirect back to previous admin page)
      - not logged in => go public home and show modal
    """
    auth = (request.headers.get("authorization") or "").lower()
    if auth.startswith("bearer "):
        return True

    cookie = (request.headers.get("cookie") or "").lower()
    # include a few common names used across apps; harmless if not present
    for key in ("access_token", "refresh_token", "session", "sessionid", "xsrf-token"):
        if key in cookie:
            return True

    return False


def _redirect_back_with_flag(request: Request, flag: str) -> RedirectResponse:
    """
    Redirect back to the previous page (Referer) if possible, preserving UI state.
    Fallback to /admin/master for logged-in admin users.
    """
    ref = (request.headers.get("referer") or "").strip()

    # Only trust referers from our own app host in local/dev; in production you may tighten this.
    # Also avoid redirect loop: don't redirect back to the same forbidden URL.
    same_path = False
    try:
        same_path = ref.endswith(request.url.path)
    except Exception:
        same_path = False

    if ref and not same_path:
        sep = "&" if "?" in ref else "?"
        url = f"{ref}{sep}auth={flag}"
        _trace(f"RETURN RedirectResponse -> {url} (303) [back to referer]")
        return RedirectResponse(url=url, status_code=303)

    # Fallback: admin landing page
    url = f"/admin/master?auth={flag}"
    _trace(f"RETURN RedirectResponse -> {url} (303) [fallback]")
    return RedirectResponse(url=url, status_code=303)


async def custom_exception_handler(request: Request, exc: Exception):
    """
    Custom exception handler.

    Updated behavior (your requirements):
    1) If user is already logged in and hits 403 on /admin/* (HTML navigation):
       - DO NOT kick to public home
       - Redirect back to previous page (Referer) and show Access Denied modal there
         (keeps app on the same page/state)
    2) If user is NOT logged in and hits any /admin/*:
       - Redirect to public home and show modal there
    """

    _trace(f"ENTER handler | path={request.url.path} method={request.method} exc={exc.__class__.__name__}")

    # -----------------------------
    # 1) Starlette HTTPException
    # -----------------------------
    if isinstance(exc, StarletteHTTPException):
        status = int(exc.status_code)
        detail = str(exc.detail)

        _trace(f"BRANCH StarletteHTTPException | status={status} detail={detail!r}")
        _log_http(request, status, detail, exc)

        if (
            request.method in ("GET", "HEAD")
            and _is_admin_path(request)
            and _wants_html(request)
            and status in (401, 403)
        ):
            flag = "expired" if status == 401 else "forbidden"

            # 401 => not logged in / session expired => go public home
            if status == 401:
                _trace(f"RETURN RedirectResponse -> /?auth={flag} (303) [401 admin->home]")
                return RedirectResponse(url=f"/?auth={flag}", status_code=303)

            # 403 => permission denied
            # if logged in => stay in admin context (redirect back)
            if _looks_like_logged_in(request):
                return _redirect_back_with_flag(request, flag=flag)

            # not logged in => go public home
            _trace(f"RETURN RedirectResponse -> /?auth={flag} (303) [403 not-logged-in admin->home]")
            return RedirectResponse(url=f"/?auth={flag}", status_code=303)

        return _json_error(status_code=status, message=detail, exc=exc)

    # -----------------------------
    # 2) FastAPI HTTPException
    # -----------------------------
    if isinstance(exc, FastAPIHTTPException):
        status = int(exc.status_code)
        detail = str(exc.detail)

        _trace(f"BRANCH FastAPIHTTPException | status={status} detail={detail!r}")
        _log_http(request, status, detail, exc)

        if (
            request.method in ("GET", "HEAD")
            and _is_admin_path(request)
            and _wants_html(request)
            and status in (401, 403)
        ):
            flag = "expired" if status == 401 else "forbidden"

            if status == 401:
                _trace(f"RETURN RedirectResponse -> /?auth={flag} (303) [401 admin->home]")
                return RedirectResponse(url=f"/?auth={flag}", status_code=303)

            if _looks_like_logged_in(request):
                return _redirect_back_with_flag(request, flag=flag)

            _trace(f"RETURN RedirectResponse -> /?auth={flag} (303) [403 not-logged-in admin->home]")
            return RedirectResponse(url=f"/?auth={flag}", status_code=303)

        return _json_error(status_code=status, message=detail, exc=exc)

    # -----------------------------
    # 3) Validation error
    # -----------------------------
    if isinstance(exc, RequestValidationError):
        _trace("BRANCH RequestValidationError (422)")
        logger.warning(
            "422 Validation error: %s %s | %s",
            request.method,
            str(request.url),
            exc.errors(),
        )
        return _json_error(
            status_code=422,
            message="Validation error occurred",
            exc=exc,
            extra={"validation_errors": exc.errors()},
        )

    # -----------------------------
    # 4) Any other unexpected exception
    # -----------------------------
    _trace("BRANCH Unhandled exception (500)")
    logger.exception("500 Unhandled exception: %s %s | %s", request.method, str(request.url), str(exc))
    return _json_error(
        status_code=500,
        message="Internal Server Error. Please try again later.",
        exc=exc,
    )