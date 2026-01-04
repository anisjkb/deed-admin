# src/backend/routes/users_api.py
from __future__ import annotations
from typing import Optional, cast
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from src.backend.utils.database import get_db
from src.backend.utils.auth import get_current_user
from src.backend.models.user import User as UserModel
from src.backend.utils.security import hash_password
from src.backend.schemas.user import UserCreate, UserUpdate
from src.backend.crud.users import (
    create_user,
    update_user,
    delete_user,
    list_emp_role_pairs,
)

router = APIRouter(prefix="/api/users", tags=["Users"])

def require_admin(u: UserModel):
    # mirror your branch checks; adjust as needed
    if not getattr(u, "role_id", None):
        raise HTTPException(status_code=403, detail="Forbidden")

@router.post("")
async def api_create_user(
    payload: UserCreate,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    try:
        user = await create_user(
            db=db,
            emp_id=payload.emp_id,
            login_id=payload.login_id,
            role_id=payload.role_id,
            email=str(payload.email).lower() if payload.email else "",
            password=hash_password(payload.password.get_secret_value()),
            created_by=cast(str, getattr(current_user, "login_id", "System")) or "System",
        )
        return {"message": "created", "login_id": user.login_id}
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Employee/Login ID/Email already exists")

@router.patch("/{login_id}")
async def api_update_user(
    login_id: str,
    payload: UserUpdate,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    # If password provided, hash it to keep parity with your flows
    if payload.password is not None:
        payload.password = payload.password.__class__(hash_password(payload.password.get_secret_value()))

    row = await update_user(
        db=db,
        login_id=login_id,
        data=payload,
        updated_by=cast(str, getattr(current_user, "login_id", "System")) or "System",
    )
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "updated", "login_id": login_id}

@router.delete("/{login_id}")
async def api_delete_user(
    login_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)
    ok, reason = await delete_user(db, login_id=login_id)
    if not ok:
        raise HTTPException(status_code=409, detail=reason or "Cannot delete user")
    return {"message": "deleted", "login_id": login_id}

@router.get("/emp-role-pairs")
async def api_emp_role_pairs(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)
    return await list_emp_role_pairs(db)