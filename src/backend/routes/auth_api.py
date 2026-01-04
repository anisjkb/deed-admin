# src/backend/routes/auth_api.py
import os
import secrets
from typing import cast, Any
from datetime import timedelta

from fastapi import APIRouter, Form, Request, Depends, HTTPException
from pydantic import EmailStr, BaseModel, ValidationError, TypeAdapter
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.utils.database import get_db
from src.backend.models.refresh_token import RefreshToken
from src.backend.utils.auth import (
    authenticate_user,
    issue_tokens_response,
    rotate_refresh_response,
    revoke_refresh_response,
    get_current_user,
    registration_response,
    REFRESH_COOKIE_NAME,
    _hmac_hash,
    _get_session_start_from_token_row,
    _enforce_hard_session_limit_if_enabled,
    rotate_refresh_response,
    revoke_refresh_response,
)
from src.backend.utils.view import render
from src.backend.utils.csrf import csrf_protect
from src.backend.utils.flash import redirect_with_flash
from src.backend.utils.email_notifier import send_email
from src.backend.utils.security import (
    hash_password,
    verify_password,
    verify_refresh_token,   # ✅ NEW: max session age enforcement on refresh
)
from src.backend.models.user import User
from src.backend.models.password_reset_token import PasswordResetToken
from src.backend.utils.timezone import now_local
from src.backend.crud.users import (
    create_user,
    get_user_by_emp_id,
    get_user_by_login_id,
    check_email_exist,
)

auth_api = APIRouter()

# -----------------------------------------------------------------------------
# Register / Login / Token lifecycle
# -----------------------------------------------------------------------------

@auth_api.post("/register", dependencies=[Depends(csrf_protect)])
async def register(
    request: Request,
    emp_id: str = Form(...),
    login_id: str = Form(...),
    role_id: str = Form(...),
    email: EmailStr = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    emp_id_norm = (emp_id or "").strip()
    login_id_norm = (login_id or "").strip()
    role_id_norm = (role_id or "").strip()
    email_norm = (email or "").strip().lower()

    if not emp_id_norm or not login_id_norm or not role_id_norm or not email_norm:
        raise HTTPException(status_code=400, detail="emp_id, login_id, role_id, and email are required.")

    # Conflict checks
    if await get_user_by_emp_id(db, emp_id_norm):
        raise HTTPException(status_code=409, detail=f"Employee ID '{emp_id_norm}' is already registered.")
    if await get_user_by_login_id(db, login_id_norm):
        raise HTTPException(status_code=409, detail=f"Login ID '{login_id_norm}' is already in use.")
    if await check_email_exist(db, email_norm):
        raise HTTPException(status_code=409, detail=f"Email '{email_norm}' is already associated with another user.")

    try:
        user = await create_user(
            db=db,
            emp_id=emp_id_norm,
            login_id=login_id_norm,
            role_id=role_id_norm,
            email=email_norm,
            password=hash_password(password),
            created_by="System",
        )
        return await registration_response(db, user, request)
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Employee ID, Login ID, or Email already exists.")


@auth_api.post("/login", dependencies=[Depends(csrf_protect)])
async def login(
    request: Request,
    logInId: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    user = await authenticate_user(db, logInId, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid login ID or password.")
    return await issue_tokens_response(db, user, request)


@auth_api.post("/refresh", dependencies=[Depends(csrf_protect)])
async def refresh_token(request: Request, db: AsyncSession = Depends(get_db)):
    """
    🔁 Refresh access token using refresh-token cookie only

    Security guarantees:
    - No access token required
    - CSRF protected
    - Refresh token rotation
    - Sliding refresh expiry
    - Absolute session cap enforced (via session_start)
    - Multi-tab safe logout
    """

    raw_refresh = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_refresh:
        # No refresh cookie → unauthenticated
        raise HTTPException(status_code=401, detail="Not authenticated")

    # 🔐 Look up refresh token row (hashed)
    token = await db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == _hmac_hash(raw_refresh),
            RefreshToken.is_revoked.is_(False),
        )
    )

    # ❌ Invalid / revoked / expired
    if not token or token.expires_at < now_local():
        await revoke_refresh_response(db, request)
        raise HTTPException(status_code=401, detail="Not authenticated")

    # 🔒 Enforce absolute session lifetime (ENV-driven)
    session_start = _get_session_start_from_token_row(token)
    _enforce_hard_session_limit_if_enabled(session_start)

    # 🔁 Rotate refresh + issue new access token
    return await rotate_refresh_response(db, request)

@auth_api.post("/logout", dependencies=[Depends(csrf_protect)])
async def logout(request: Request, db: AsyncSession = Depends(get_db)):
    return await revoke_refresh_response(db, request)


@auth_api.get("/me", dependencies=[Depends(csrf_protect)])
async def me(request: Request, current_user: User = Depends(get_current_user)):
    return {
        "emp_id": current_user.emp_id,
        "login_id": current_user.login_id,
        "role_id": current_user.role_id,
        "email": current_user.email,
        "status": current_user.status,
        "created_by": current_user.created_by,
        "create_dt": current_user.create_dt,
        "updated_by": current_user.updated_by,
        "update_dt": current_user.update_dt,
    }


# -----------------------------------------------------------------------------
# Forgot Username — dual-mode (JSON or Form)
# -----------------------------------------------------------------------------

@auth_api.post("/forgot-username", dependencies=[Depends(csrf_protect)])
async def forgot_username(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Accepts:
      - JSON:  { "email": "..." } -> returns JSON
      - Form:  email=... -> redirects (flash)
    """
    ctype = (request.headers.get("content-type") or "").lower()
    is_json = "application/json" in ctype

    email_raw = ""
    if is_json:
        try:
            data = await request.json()
        except Exception:
            data = {}
        email_raw = (data.get("email") or "").strip() if isinstance(data, dict) else ""
    else:
        form = await request.form()
        v = form.get("email")
        email_raw = v.strip() if isinstance(v, str) else ""

    try:
        email = TypeAdapter(EmailStr).validate_python(email_raw)
    except ValidationError:
        if is_json:
            raise HTTPException(status_code=422, detail="Invalid email address.")
        return await render(
            "forgot_username.html",
            {
                "request": request,
                "title": "Forgot Username",
                "error": "Please enter a valid email address.",
                "flashes": [],
            },
        )

    user = await db.scalar(select(User).where(User.email == str(email)))
    if not user:
        msg = "No account found with that email."
        if is_json:
            raise HTTPException(status_code=404, detail=msg)
        return await redirect_with_flash(request.session, "/forgot-username", "danger", msg)

    send_email(
        to=cast(str, user.email),
        subject="Your Login ID",
        body=(
            "Hello,\n\n"
            f"Your login ID is: {user.login_id}\n\n"
            "If you didn't request this, please ignore this email."
        ),
    )

    if is_json:
        return {"message": "Your login ID has been sent to your email."}
    return await redirect_with_flash(request.session, "/login", "success", "We’ve emailed your login ID.")


# -----------------------------------------------------------------------------
# Forgot / Reset Password (JSON)
# -----------------------------------------------------------------------------

class ForgotPasswordRequest(BaseModel):
    login_id: str
    email: EmailStr


@auth_api.post("/link-forgot-password", dependencies=[Depends(csrf_protect)])
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    login_id = request.login_id.strip()
    email = request.email

    user = await db.scalar(select(User).where(User.login_id == login_id, User.email == email))
    if not user:
        raise HTTPException(status_code=404, detail="User with that login ID and email was not found.")

    reset_token = secrets.token_urlsafe(32)
    hashed_token = hash_password(reset_token)

    now_dt = now_local()
    expires_at = now_dt + timedelta(minutes=15)

    token_entry = PasswordResetToken(
        login_id=user.login_id,
        token_hash=hashed_token,
        expires_at=expires_at,
    )
    db.add(token_entry)
    await db.commit()
    await db.refresh(token_entry)

    frontend_url = os.getenv("FRONTEND_URL") or "http://localhost:8000"
    reset_link = f"{frontend_url.rstrip('/')}/reset-password/{reset_token}"

    send_email(
        to=cast(str, user.email),
        subject="Password Reset Request",
        body=(
            "You requested a password reset.\n\n"
            f"Click here to reset your password (valid for 15 minutes): {reset_link}\n\n"
            "If you did not request this, please ignore this email."
        ),
    )
    return {"message": "Password reset link sent to your email."}


class ResetPasswordRequest(BaseModel):
    reset_code: str
    password: str


@auth_api.post("/reset-password", dependencies=[Depends(csrf_protect)])
async def reset_password(
    req: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    now_dt = now_local()

    res = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.expires_at >= now_dt)
    )
    tokens = list(res.scalars().all())
    if not tokens:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

    matching_token = None
    for t in tokens:
        if verify_password(req.reset_code, t.token_hash):
            matching_token = t
            break

    if not matching_token:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

    user = await db.scalar(select(User).where(User.login_id == matching_token.login_id))
    if not user:
        await db.delete(matching_token)
        await db.commit()
        raise HTTPException(status_code=404, detail="User not found.")

    cast(Any, user).password = hash_password(req.password)
    db.add(user)

    await db.delete(matching_token)
    await db.commit()

    return {"message": "Password reset successful."}


@auth_api.post("/change-password", dependencies=[Depends(csrf_protect)])
async def change_password(
    request: Request,
    old_password: str = Form(...),
    new_password: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(old_password, cast(str, current_user.password)):
        return await redirect_with_flash(request.session, "/change-password", "danger", "Old password is incorrect.")

    if len(new_password) < 4:
        return await redirect_with_flash(
            request.session,
            "/change-password",
            "danger",
            "New password must be at least 4 characters long.",
        )

    cast(Any, current_user).password = hash_password(new_password)
    db.add(current_user)
    await db.commit()

    return await redirect_with_flash(
        request.session,
        "/change-password",
        "success",
        "Password changed successfully.",
    )