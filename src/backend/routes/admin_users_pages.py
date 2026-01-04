import os, math
from typing import Optional, Dict, Any, cast
from fastapi import APIRouter, Request, Depends, Query, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from src.backend.utils.database import get_db
from src.backend.utils.auth import get_current_user
from src.backend.models.user import User as UserModel
from src.backend.utils.view import render
from src.backend.utils.flash import flash_popall, redirect_with_flash
from src.backend.utils.csrf import csrf_protect
from src.backend.crud.role import list_roles_for_select
from src.backend.utils.common_context import add_common

# rights-aware guards
from src.backend.utils.permissions import (
    require_view,
    require_create,
    require_edit,
    require_delete,
)

from src.backend.crud.users import (
    list_users_with_emp_name,
    get_user_by_login_id,
    get_emp_name,
    create_user_from_emp,
    update_user_role_status,
    delete_user_if_no_children,
    search_employees_for_picklist,
    count_user_dependents,
    EmployeeNotFoundError,
    EmployeeEmailMissingError,
    DuplicateLoginIdError,
    DuplicateEmployeeUserError,
    DuplicateEmailError,
)

router = APIRouter(prefix="/admin/users", tags=["Admin Users"])

def _admin_guard(u: UserModel):
    # keep a quick admin-area check (role required); detailed rights handled by require_* deps
    if not getattr(u, "role_id", None):
        raise HTTPException(status_code=403, detail="Forbidden")

# -----------------------
# List (VIEW)
# -----------------------
@router.get("", dependencies=[Depends(require_view)])
async def list_page(
    request: Request,
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=5, le=100),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _admin_guard(current_user)

    offset = (page - 1) * size
    rows, total = await list_users_with_emp_name(db, q=q, limit=size, offset=offset)
    pages = math.ceil(total / size) if size else 1
    ctx: Dict[str, Any] = {
        "request": request,
        "title": "Manage Users",
        "rows": rows,
        "q": q or "",
        "page": page,
        "pages": pages,
        "size": size,
        "total": total,
        "flashes": await flash_popall(request.session),
    }

    await add_common(ctx, db, current_user, request=request)  # injects display_name, sidebar, perms
    return await render("admin/users/index.html", ctx)

# -----------------------
# Create page (CREATE)
# -----------------------
@router.get("/new", dependencies=[Depends(require_create)])
async def new_page(
    request: Request,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _admin_guard(current_user)
    roles = await list_roles_for_select(db)
    ctx = {
        "request": request,
        "title": "Create User",
        "mode": "create",
        "form": {"status": "A", "login_id": "", "emp_id": "", "role_id": "", "emp_name": "", "email": ""},
        "roles": roles,
        "flashes": await flash_popall(request.session),
    }
    await add_common(ctx, db, current_user, request=request)
    return await render("admin/users/form.html", ctx)

# -----------------------
# Edit page (EDIT)
# -----------------------
@router.get("/{login_id}/edit", dependencies=[Depends(require_edit)])
async def edit_page(
    request: Request,
    login_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _admin_guard(current_user)
    row = await get_user_by_login_id(db, login_id)
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    emp_name = await get_emp_name(db, cast(str, row.emp_id))
    roles = await list_roles_for_select(db)
    ctx = {
        "request": request,
        "title": f"Edit User {login_id}",
        "mode": "edit",
        "form": {
            "emp_id": row.emp_id,
            "emp_name": emp_name or "",
            "login_id": row.login_id,
            "role_id": row.role_id,
            "status": row.status or "A",
            "email": row.email or "",
        },
        "roles": roles,
        "flashes": await flash_popall(request.session),
    }
    await add_common(ctx, db, current_user, request=request)
    return await render("admin/users/form.html", ctx)

# -----------------------
# Create action (CREATE)
# -----------------------
@router.post("", dependencies=[Depends(require_create), Depends(csrf_protect)])
async def create_action(
    request: Request,
    emp_id: str = Form(...),
    login_id: str = Form(""),
    role_id: str = Form(...),
    status: str = Form("A"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _admin_guard(current_user)
    try:
        created = await create_user_from_emp(
            db,
            emp_id=emp_id,
            login_id=login_id or None,
            role_id=role_id,
            status=status,
            created_by=cast(str, getattr(current_user, "login_id", "System")) or "System",
        )
        return await redirect_with_flash(
            request.session, "/admin/users", "success", f"User '{created.login_id}' created."
        )

    except (EmployeeNotFoundError,
            EmployeeEmailMissingError,
            DuplicateEmployeeUserError,
            DuplicateLoginIdError,
            DuplicateEmailError) as e:
        error_msg = str(e)
    except IntegrityError:
        error_msg = "A unique constraint was violated while creating the user."
    except Exception as e:
        error_msg = f"Failed to create user: {e}"

    roles = await list_roles_for_select(db)
    ctx = {
        "request": request,
        "title": "Create User",
        "mode": "create",
        "form": {"emp_id": emp_id, "login_id": login_id, "role_id": role_id, "status": status},
        "roles": roles,
        "error": error_msg,
        "flashes": await flash_popall(request.session),
    }
    await add_common(ctx, db, current_user, request=request)
    return await render("admin/users/form.html", ctx)

# -----------------------
# Update action (EDIT)
# -----------------------
@router.post("/{login_id}", dependencies=[Depends(require_edit), Depends(csrf_protect)])
async def update_action(
    request: Request,
    login_id: str,
    role_id: str = Form(...),
    status: str = Form(...),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _admin_guard(current_user)
    row = await update_user_role_status(
        db,
        login_id=login_id,
        role_id=role_id,
        status=status,
        updated_by=cast(str, getattr(current_user, "login_id", "System")) or "System",
    )
    if not row:
        return await redirect_with_flash(request.session, "/admin/users", "danger", "User not found")
    return await redirect_with_flash(request.session, "/admin/users", "success", f"User '{login_id}' updated.")

# -----------------------
# Delete action (DELETE)
# -----------------------
@router.post("/{login_id}/delete", dependencies=[Depends(require_delete), Depends(csrf_protect)])
async def delete_action(
    request: Request,
    login_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _admin_guard(current_user)
    ok = await delete_user_if_no_children(db, login_id)
    if not ok:
        counts = await count_user_dependents(db, login_id)
        c_rt = counts.get("refresh_tokens", 0)
        c_al = counts.get("activity_logs", 0)
        total = counts.get("total", 0)

        parts = []
        if c_rt: parts.append(f"{c_rt} refresh token{'s' if c_rt != 1 else ''}")
        if c_al: parts.append(f"{c_al} activity log{'s' if c_al != 1 else ''}")
        detail = ", ".join(parts) if parts else "linked records"
        msg = f"Cannot delete user '{login_id}': {total} {detail} exist. Revoke tokens and clear logs first."

        return await redirect_with_flash(request.session, "/admin/users", "danger", msg)

    return await redirect_with_flash(request.session, "/admin/users", "success", f"User '{login_id}' deleted.")

# -----------------------
# JSON options for employee picklist (VIEW)
# -----------------------
@router.get("/options/employees", dependencies=[Depends(require_view)])
async def employee_options(
    q: Optional[str] = None,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _admin_guard(current_user)
    records = await search_employees_for_picklist(db, q=q, limit=50)
    return [
        {
            "emp_id": r.emp_id,
            "emp_name": r.emp_name,
            "email": r.email or "",
        }
        for r in records
    ]