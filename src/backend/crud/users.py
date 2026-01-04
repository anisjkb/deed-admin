# src/backend/crud/users.py
from __future__ import annotations
from typing import Optional, Tuple, List, Sequence,Dict, Any
from sqlalchemy import select, or_, delete, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from src.backend.utils.security import hash_password
from src.backend.models.user import User
from src.backend.models.refresh_token import RefreshToken  # used in other flows
from src.backend.schemas.user import UserCreate, UserUpdate
from src.backend.models.org.emp_info import EmpInfo
from src.backend.models.security.role import Role
import secrets

class EmployeeNotFoundError(Exception): ...
class EmployeeEmailMissingError(Exception): ...
class DuplicateLoginIdError(Exception): ...
class DuplicateEmployeeUserError(Exception): ...
class DuplicateEmailError(Exception): ...

# -----------------------
# Basic getters / checks
# -----------------------

# --- list users with employee name for the table ---
async def list_users_with_emp_name(
    db: AsyncSession,
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Returns rows shaped for the users table, each with 'emp_name'.
    """
    stmt = (
        select(
            User.emp_id,
            User.login_id,
            User.role_id,
            User.email,
            User.status,
            EmpInfo.emp_name,
        )
        .select_from(User)
        .outerjoin(EmpInfo, EmpInfo.emp_id == User.emp_id)
    )
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                User.login_id.ilike(like),
                User.emp_id.ilike(like),
                User.role_id.ilike(like),
                User.email.ilike(like),
                User.status.ilike(like),
                EmpInfo.emp_name.ilike(like),
            )
        )

    # count (cheap enough for admin tables)
    res_count = await db.execute(
        stmt.with_only_columns(User.login_id).order_by(None)
    )
    total = len(res_count.scalars().all())

    res = await db.execute(stmt.order_by(User.login_id).limit(limit).offset(offset))
    rows: List[Dict[str, Any]] = []
    for emp_id, login_id, role_id, email, status, emp_name in res.all():
        rows.append(
            {
                "emp_id": emp_id,
                "login_id": login_id,
                "role_id": role_id,
                "email": email,
                "status": status,
                "emp_name": emp_name or "",
            }
        )
    return rows, total

# --- single employee name for the edit page ---
async def get_emp_name(db: AsyncSession, emp_id: str) -> str:
    name = await db.scalar(select(EmpInfo.emp_name).where(EmpInfo.emp_id == emp_id))
    return name or ""

async def get_user_by_emp_id(db: AsyncSession, emp_id: str) -> Optional[User]:
    return await db.scalar(select(User).where(User.emp_id == (emp_id or "").strip()))

async def get_user_by_login_id(db: AsyncSession, login_id: str) -> Optional[User]:
    return await db.scalar(select(User).where(User.login_id == (login_id or "").strip()))

async def check_email_exist(db: AsyncSession, email: str) -> bool:
    email_l = (email or "").strip().lower()
    exists = await db.scalar(select(User.login_id).where(User.email == email_l))
    return exists is not None

async def get_all_users(db: AsyncSession) -> List[User]:
    res = await db.execute(select(User))
    return list(res.scalars().all())

# -----------------------
# List + search + paging
# -----------------------
async def list_users(
    db: AsyncSession,
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[User], int]:
    stmt = select(User)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                User.login_id.ilike(like),
                User.emp_id.ilike(like),
                User.role_id.ilike(like),
                User.email.ilike(like),
            )
        )
    stmt = stmt.order_by(User.login_id)

    # count cheaply
    res_ids = await db.execute(stmt.with_only_columns(User.login_id).order_by(None))
    total = len(res_ids.scalars().all())

    page_res = await db.execute(stmt.limit(limit).offset(offset))
    return list(page_res.scalars().all()), total

# -----------------------
# Create / Update / Delete
# -----------------------
async def create_user(
    db: AsyncSession,
    *,
    emp_id: str,
    login_id: str,
    role_id: str,
    email: str,       # validated/required by caller
    password: str,    # already hashed
    created_by: Optional[str] = None,
) -> User:
    user = User(
        emp_id=(emp_id or "").strip(),
        login_id=(login_id or "").strip(),
        role_id=(role_id or "").strip(),
        email=(email or "").strip().lower(),
        password=password,
        status="A",
        created_by=created_by,
        updated_by=created_by,
    )
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError:
        await db.rollback()
        raise
    return user

async def update_user(
    db: AsyncSession,
    *,
    login_id: str,         # PK: we don't change it
    data: UserUpdate,
    updated_by: Optional[str] = None,
) -> Optional[User]:
    row = await get_user_by_login_id(db, login_id)
    if not row:
        return None

    # Optional updates:
    if data.role_id is not None:
        setattr(row, "role_id", data.role_id)
    if data.email is not None:
        setattr(row, "email", str(data.email).lower())
    if data.status is not None:
        setattr(row, "status", data.status)  # already normalized to 'A'/'I'
    if data.password is not None:
        # data.password is SecretStr; caller should pass a hashed value already,
        # or hash here if you prefer. Keeping parity with your auth flows:
        setattr(row, "password", data.password.get_secret_value())

    # user_name is UI-only (no column in user_info); ignore safely.

    setattr(row, "updated_by", (updated_by or row.updated_by))
    try:
        await db.commit()
        await db.refresh(row)
    except IntegrityError:
        await db.rollback()
        raise
    return row

async def _count_children_for_user(db: AsyncSession, login_id: str) -> int:
    """
    Checks for dependent rows that should block delete.
    Extend as needed.
    """
    # refresh_tokens
    q1 = await db.execute(text("SELECT COUNT(*) FROM refresh_tokens WHERE login_id = :lid"), {"lid": login_id})
    c1 = int(q1.scalar_one() or 0)

    # user_activity_log
    q2 = await db.execute(text("SELECT COUNT(*) FROM user_activity_log WHERE login_id = :lid"), {"lid": login_id})
    c2 = int(q2.scalar_one() or 0)

    return c1 + c2

async def delete_user(
    db: AsyncSession,
    *,
    login_id: str,
) -> Tuple[bool, str]:
    """
    Guarded delete: refuses to delete when child rows exist.
    Returns (ok, message).
    """
    total_children = await _count_children_for_user(db, login_id)
    if total_children > 0:
        return False, f"User has {total_children} dependent row(s) and cannot be deleted."

    await db.execute(delete(User).where(User.login_id == login_id))
    await db.commit()
    return True, ""

# -----------------------
# Convenience: (emp_id, role_id) list
# -----------------------
async def list_emp_role_pairs(db: AsyncSession) -> List[dict]:
    res = await db.execute(select(User.emp_id, User.role_id).order_by(User.emp_id))
    return [{"emp_id": e, "role_id": r} for (e, r) in res.all()]

# -----------------------
# Helpers expected by admin_users_pages.py
# -----------------------

async def list_role_ids(db: AsyncSession) -> List[str]:
    """
    Return list of role_id strings (active first by id).
    Kept here to satisfy existing import path from admin_users_pages.py.
    """
    stmt = select(Role.role_id).order_by(Role.role_id)
    res = await db.execute(stmt)
    return list(res.scalars().all())

# Create user from employee with proper password hashing
async def create_user_from_emp(
    db: AsyncSession,
    *,
    emp_id: str,
    login_id: str | None = None,
    role_id: str,
    status: str = "A",
    created_by: Optional[str] = None,
) -> User:
    emp_id_n = (emp_id or "").strip()
    login_id_n = (login_id or emp_id_n or "").strip()
    role_id_n  = (role_id or "").strip()
    status_1   = (status or "A").strip()[:1] or "A"

    # 1) employee exists?
    emp_row = await db.scalar(select(EmpInfo).where(EmpInfo.emp_id == emp_id_n))
    if not emp_row:
        raise EmployeeNotFoundError(f"Employee '{emp_id_n}' was not found.")

    # 2) employee has email?
    email = (getattr(emp_row, "email", "") or "").strip().lower()
    if not email:
        raise EmployeeEmailMissingError(f"Employee '{emp_id_n}' has no email on record.")

    # 3) duplicate user by employee?
    if await get_user_by_emp_id(db, emp_id_n):
        raise DuplicateEmployeeUserError(f"An account already exists for employee '{emp_id_n}'.")

    # 4) duplicate login id?
    if await get_user_by_login_id(db, login_id_n):
        raise DuplicateLoginIdError(f"Login ID '{login_id_n}' is already in use.")

    # 5) duplicate email?
    if await check_email_exist(db, email):
        raise DuplicateEmailError(f"Email '{email}' is already used by another account.")

    # create with hashed random initial password (policy-compliant)
    raw_temp_password = secrets.token_urlsafe(16)
    hashed_password = hash_password(raw_temp_password)

    user = User(
        emp_id=emp_id_n,
        login_id=login_id_n,
        role_id=role_id_n,
        email=email,
        password=hashed_password,
        status=status_1,
        created_by=created_by,
        updated_by=created_by,
    )
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError:
        await db.rollback()
        # fallback – if a race slips through, convert to clearer error
        raise DuplicateLoginIdError(f"Login ID '{login_id_n}' is already in use.")
    return user

async def update_user_role_status(
    db: AsyncSession,
    *,
    login_id: str,
    role_id: str,
    status: str,
    updated_by: Optional[str] = None,
) -> Optional[User]:
    """
    Minimal updater used by the edit form: only role_id + status (A/I).
    """
    row = await get_user_by_login_id(db, login_id)
    if not row:
        return None

    setattr(row, "role_id", (role_id or "").strip())
    setattr(row, "status", (status or "").strip()[:1] or "A")
    setattr(row, "updated_by", updated_by or row.updated_by)

    try:
        await db.commit()
        await db.refresh(row)
    except IntegrityError:
        await db.rollback()
        raise
    return row

async def delete_user_if_no_children(db: AsyncSession, login_id: str) -> bool:
    """
    Wrap your guarded delete; return bool for the route's simple branch.
    """
    ok, _ = await delete_user(db, login_id=login_id)
    return ok

async def search_employees_for_picklist(
    db: AsyncSession,
    *,
    q: Optional[str] = None,
    limit: int = 50,
) -> List[EmpInfo]:
    """
    Lightweight search for picklist. Returns EmpInfo rows with id, name, email.
    """
    stmt = select(EmpInfo)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                EmpInfo.emp_id.ilike(like),
                EmpInfo.emp_name.ilike(like),
                EmpInfo.email.ilike(like),
                EmpInfo.mobile.ilike(like),
            )
        )
    stmt = stmt.order_by(EmpInfo.emp_id).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())

async def count_user_dependents(db: AsyncSession, login_id: str) -> Dict[str, int]:
    q1 = await db.execute(text("SELECT COUNT(*) FROM refresh_tokens WHERE login_id = :lid"), {"lid": login_id})
    c1 = int(q1.scalar_one() or 0)
    q2 = await db.execute(text("SELECT COUNT(*) FROM user_activity_log WHERE login_id = :lid"), {"lid": login_id})
    c2 = int(q2.scalar_one() or 0)
    return {"refresh_tokens": c1, "activity_logs": c2, "total": c1 + c2}

