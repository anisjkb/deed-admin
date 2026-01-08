# src/backend/routes/auth_api.py
import os
import secrets
from typing import cast, Any
from datetime import timedelta

from fastapi import (
    APIRouter,
    Form,
    Request,
    Depends,
    HTTPException,
    BackgroundTasks,
)
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
)
from src.backend.utils.view import render
from src.backend.utils.csrf import csrf_protect
from src.backend.utils.flash import redirect_with_flash
from src.backend.utils.email_notifier import send_email
from src.backend.utils.security import (
    hash_password,
    verify_password,
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
    emp_id_norm = emp_id.strip()
    login_id_norm = login_id.strip()
    role_id_norm = role_id.strip()
    email_norm = email.strip().lower()

    if not all([emp_id_norm, login_id_norm, role_id_norm, email_norm]):
        raise HTTPException(
            status_code=400,
            detail="emp_id, login_id, role_id, and email are required.",
        )

    if await get_user_by_emp_id(db, emp_id_norm):
        raise HTTPException(status_code=409, detail="Employee ID already registered.")
    if await get_user_by_login_id(db, login_id_norm):
        raise HTTPException(status_code=409, detail="Login ID already in use.")
    if await check_email_exist(db, email_norm):
        raise HTTPException(status_code=409, detail="Email already in use.")

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
        raise HTTPException(status_code=409, detail="Duplicate registration data.")

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
    raw_refresh = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_refresh:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = await db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == _hmac_hash(raw_refresh),
            RefreshToken.is_revoked.is_(False),
        )
    )

    if not token or token.expires_at < now_local():
        await revoke_refresh_response(db, request)
        raise HTTPException(status_code=401, detail="Not authenticated")

    session_start = _get_session_start_from_token_row(token)
    _enforce_hard_session_limit_if_enabled(session_start)

    return await rotate_refresh_response(db, request)


@auth_api.post("/logout", dependencies=[Depends(csrf_protect)])
async def logout(request: Request, db: AsyncSession = Depends(get_db)):
    return await revoke_refresh_response(db, request)


@auth_api.get("/me", dependencies=[Depends(csrf_protect)])
async def me(current_user: User = Depends(get_current_user)):
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
# Forgot Username — dual-mode + background email
# -----------------------------------------------------------------------------

@auth_api.post("/forgot-username", dependencies=[Depends(csrf_protect)])
async def forgot_username(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    ctype = (request.headers.get("content-type") or "").lower()
    is_json = "application/json" in ctype

    email_raw = ""
    if is_json:
        try:
            data = await request.json()
            email_raw = (data.get("email") or "").strip()
        except Exception:
            email_raw = ""
    else:
        form = await request.form()
        email_raw = form.get("email")
        if isinstance(email_raw, str):
            email_raw = email_raw.strip()
        else:
            email_raw = ""

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
        return await redirect_with_flash(
            request.session, "/forgot-username", "danger", msg
        )

    # 🔹 Email sent in background (non-blocking, failure-safe)
    background_tasks.add_task(
        send_email,
        to=cast(str, user.email),
        subject="Your Login ID",
        body=(
            "Hello,\n\n"
            f"Your login ID is: {user.login_id}\n\n"
            "If you didn't request this, please ignore this email."
        ),
    )

    if is_json:
        return {"message": "The login ID has been sent to your email address."}

    return await redirect_with_flash(
        request.session,
        "/login",
        "success",
        "The login ID has been sent to your email address.",
    )

# -----------------------------------------------------------------------------
# Forgot / Reset Password (JSON)
# -----------------------------------------------------------------------------

class ForgotPasswordRequest(BaseModel):
    login_id: str
    email: EmailStr


@auth_api.post("/link-forgot-password", dependencies=[Depends(csrf_protect)])
async def forgot_password(
    request: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    user = await db.scalar(
        select(User).where(
            User.login_id == request.login_id.strip(),
            User.email == request.email,
        )
    )

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    reset_token = secrets.token_urlsafe(32)
    hashed_token = hash_password(reset_token)

    token_entry = PasswordResetToken(
        login_id=user.login_id,
        token_hash=hashed_token,
        expires_at=now_local() + timedelta(minutes=15),
    )
    db.add(token_entry)
    await db.commit()

    api_url = os.getenv("API_URL", "http://localhost:8000")
    reset_link = f"{api_url.rstrip('/')}/reset-password/{reset_token}"

    background_tasks.add_task(
        send_email,
        to=cast(str, user.email),
        subject="Password Reset Request",
        body=(
            "You requested a password reset.\n\n"
            f"Reset link (15 min): {reset_link}\n\n"
            "If you did not request this, ignore this email."
        ),
    )

    return {"message": "Password reset link has been sent to your email."}


class ResetPasswordRequest(BaseModel):
    reset_code: str
    password: str


@auth_api.post("/reset-password", dependencies=[Depends(csrf_protect)])
async def reset_password(req: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    now_dt = now_local()

    res = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.expires_at >= now_dt
        )
    )
    tokens = list(res.scalars())

    matching = next(
        (t for t in tokens if verify_password(req.reset_code, t.token_hash)),
        None,
    )
    if not matching:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

    user = await db.scalar(select(User).where(User.login_id == matching.login_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.password = hash_password(req.password)
    await db.delete(matching)
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
    if not verify_password(old_password, current_user.password):
        return await redirect_with_flash(
            request.session,
            "/change-password",
            "danger",
            "Old password is incorrect.",
        )

    if len(new_password) < 4:
        return await redirect_with_flash(
            request.session,
            "/change-password",
            "danger",
            "New password must be at least 4 characters long.",
        )

    current_user.password = hash_password(new_password)
    await db.commit()

    return await redirect_with_flash(
        request.session,
        "/change-password",
        "success",
        "Password changed successfully.",
    )