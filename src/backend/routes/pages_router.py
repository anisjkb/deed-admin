# src/backend/routes/pages_router.py
from __future__ import annotations
from typing import Optional, Dict, Any
from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.backend.utils.auth import get_current_user
from src.backend.utils.database import get_db
from src.backend.models.user import User
from src.backend.utils.flash import flash_popall
from src.backend.utils.view import render  # adds no-cache headers
# ✅ shared context builder (display_name + menu_tree) for header/sidebar
from src.backend.utils.common_context import add_common

router = APIRouter()

@router.get("/")
async def landing_page(request: Request):
    return await render("home.html", {"request": request, "title": "Home"})

@router.get("/login")
async def login_page(request: Request, error: Optional[str] = None):
    return await render("login.html", {"request": request, "title": "Login", "error": error})

@router.get("/register")
async def register_page(request: Request):
    return await render("register.html", {"request": request, "title": "Register"})

@router.get("/admin/master")
async def master_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx: Dict[str, Any] = {
        "request": request,
        "title": "Master",
    }
    # Sidebar + header name
    await add_common(ctx, db, current_user)
    return await render("admin/master.html", ctx)

@router.get("/forgot-username")
async def get_forgot_username(request: Request):
    return await render(
        "forgot_username.html",
        {
            "request": request,
            "title": "Forgot Username",
            "flashes": await flash_popall(request.session),
        },
    )

@router.get("/forgot-password")
async def forgot_password_page(request: Request):
    return await render("forgot_password.html", {"request": request, "title": "Forgot Password"})

@router.get("/reset-password/{token}")
async def reset_password_page(request: Request, token: str):
    return await render(
        "reset_password.html",
        {"request": request, "title": "Reset Password", "reset_token": token},
    )

@router.get("/change-password")
async def change_password_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx: Dict[str, Any] = {
        "request": request,
        "title": "Change Password",
        "flashes": await flash_popall(request.session),
    }
    # Ensure header display_name + sidebar menu render on this page, too
    await add_common(ctx, db, current_user)
    return await render("admin/security/change_password.html", ctx)
