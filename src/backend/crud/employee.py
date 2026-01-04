# src/backend/crud/employee.py
from __future__ import annotations

from typing import Optional, Tuple, List
from datetime import date, datetime

from sqlalchemy import select, or_, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.models.org.emp_info import EmpInfo
from src.backend.models.org.br_info import BranchInfo
from src.backend.models.org.zone_info import ZoneInfo
from src.backend.models.org.org_info import OrgInfo
from src.backend.models.org.group_info import GroupInfo
from src.backend.models.org.desig_info import DesigInfo

from src.backend.schemas.employee import EmployeeCreate, EmployeeUpdate
from src.backend.utils.timezone import now_local


# -------------------------
# helpers
# -------------------------
def _s(v: Optional[str]) -> Optional[str]:
    """
    Normalize a string:
    - None -> None
    - "" / "   " -> None
    - else stripped string
    """
    if v is None:
        return None
    v = v.strip()
    return v if v else None


def _status(v: Optional[str]) -> str:
    """
    Status is stored as string; default to 'active' if empty.
    """
    return (_s(v) or "active")


def _parse_date(s: Optional[str]) -> Optional[date]:
    s = _s(s)
    if not s:
        return None
    try:
        y, m, d = (int(x) for x in s.split("-"))
        return date(y, m, d)
    except Exception:
        return None


def _now_naive() -> datetime:
    dt = now_local()
    return dt.replace(tzinfo=None) if getattr(dt, "tzinfo", None) else dt


# -------------------------
# Listing / Search
# -------------------------
async def list_employees(
    db: AsyncSession,
    q: Optional[str] = None,
    emp_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[EmpInfo], int]:
    stmt = select(EmpInfo)

    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                EmpInfo.emp_id.ilike(like),
                EmpInfo.emp_name.ilike(like),
                EmpInfo.mobile.ilike(like),
                EmpInfo.email.ilike(like),
                EmpInfo.status.ilike(like),
            )
        )

    if emp_type and emp_type != "all":
        stmt = stmt.where(EmpInfo.emp_type == emp_type)

    # sort for frontend display
    stmt = stmt.order_by(EmpInfo.sort_order.nulls_last(), EmpInfo.emp_id)

    # count
    res_count = await db.execute(stmt.with_only_columns(EmpInfo.emp_id).order_by(None))
    total = len(res_count.scalars().all())

    res = await db.execute(stmt.limit(limit).offset(offset))
    rows = list(res.scalars().all())
    return rows, total


# -------------------------
# Dropdown helpers
# -------------------------
async def list_groups(db: AsyncSession) -> List[GroupInfo]:
    res = await db.execute(
        select(GroupInfo).where(GroupInfo.status == "active").order_by(GroupInfo.group_id)
    )
    return list(res.scalars().all())


async def list_orgs(db: AsyncSession, group_id: Optional[str]) -> List[OrgInfo]:
    stmt = select(OrgInfo).where(OrgInfo.status == "active")
    if _s(group_id):
        stmt = stmt.where(OrgInfo.group_id == group_id)
    stmt = stmt.order_by(OrgInfo.org_id)
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def list_zones(db: AsyncSession, org_id: Optional[str]) -> List[ZoneInfo]:
    stmt = select(ZoneInfo).where(ZoneInfo.status == "active")
    if _s(org_id):
        stmt = stmt.where(ZoneInfo.org_id == org_id)
    stmt = stmt.order_by(ZoneInfo.zone_id)
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def list_branches(db: AsyncSession, zone_id: Optional[str]) -> List[BranchInfo]:
    stmt = select(BranchInfo).where(BranchInfo.status == "active")
    if _s(zone_id):
        stmt = stmt.where(BranchInfo.zone_id == zone_id)
    stmt = stmt.order_by(BranchInfo.br_id)
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def list_designations(db: AsyncSession) -> List[DesigInfo]:
    res = await db.execute(
        select(DesigInfo).where(DesigInfo.status == "active").order_by(DesigInfo.desig_id)
    )
    return list(res.scalars().all())


# -------------------------
# Single
# -------------------------
async def get_employee(db: AsyncSession, emp_id: str) -> Optional[EmpInfo]:
    emp_id = (emp_id or "").strip()
    res = await db.execute(select(EmpInfo).where(EmpInfo.emp_id == emp_id))
    return res.scalar_one_or_none()


# -------------------------
# Create / Update / Delete
# -------------------------
async def create_employee(
    db: AsyncSession,
    data: EmployeeCreate,
    created_by: str = "System",
) -> EmpInfo:
    row = EmpInfo(
        emp_id=(data.emp_id or "").strip(),
        emp_name=(data.emp_name or "").strip(),

        gender=_s(data.gender),
        dob=_parse_date(data.dob),
        mobile=_s(data.mobile),
        email=_s(data.email),
        join_date=_parse_date(data.join_date),

        desig_id=_s(data.desig_id),
        br_id=_s(data.br_id),
        zone_id=_s(data.zone_id),
        org_id=_s(data.org_id),
        group_id=_s(data.group_id),

        nid=_s(data.nid),
        blood_group=_s(data.blood_group),
        address=_s(data.address),
        emergency_phone=_s(data.emergency_phone),

        # ✅ this will be "/images/team/....avif" from your route
        photo_url=_s(data.photo_url),

        status=_status(data.status),

        created_by=_s(created_by) or "System",
        updated_by=_s(created_by) or "System",
        created_dt=_now_naive(),
        updated_dt=_now_naive(),

        emp_type=_s(data.emp_type) or "Contractual",
        bio=_s(data.bio),
        linkedin_url=_s(data.linkedin_url),
        sort_order=data.sort_order,
        bio_details=_s(data.bio_details),
    )

    db.add(row)
    try:
        await db.commit()
        await db.refresh(row)
    except IntegrityError:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise
    return row


async def update_employee(
    db: AsyncSession,
    emp_id: str,
    data: EmployeeUpdate,
    updated_by: str = "System",
) -> Optional[EmpInfo]:
    row = await get_employee(db, emp_id)
    if not row:
        return None

    row.emp_name = (data.emp_name or "").strip()

    row.gender = _s(data.gender)
    row.dob = _parse_date(data.dob)
    row.mobile = _s(data.mobile)
    row.email = _s(data.email)
    row.join_date = _parse_date(data.join_date)

    row.desig_id = _s(data.desig_id)
    row.br_id = _s(data.br_id)
    row.zone_id = _s(data.zone_id)
    row.org_id = _s(data.org_id)
    row.group_id = _s(data.group_id)

    row.nid = _s(data.nid)
    row.blood_group = _s(data.blood_group)
    row.address = _s(data.address)
    row.emergency_phone = _s(data.emergency_phone)

    # ✅ route decides delete/replace; CRUD only stores final URL
    row.photo_url = _s(data.photo_url)

    row.status = _status(data.status)
    row.updated_by = _s(updated_by) or "System"
    row.updated_dt = _now_naive()

    row.emp_type = _s(data.emp_type) or "Contractual"
    row.bio = _s(data.bio)
    row.linkedin_url = _s(data.linkedin_url)
    row.sort_order = data.sort_order
    row.bio_details = _s(data.bio_details)

    try:
        await db.commit()
        await db.refresh(row)
    except IntegrityError:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise
    return row


async def delete_employee(db: AsyncSession, emp_id: str) -> bool:
    emp_id = (emp_id or "").strip()
    await db.execute(delete(EmpInfo).where(EmpInfo.emp_id == emp_id))
    await db.commit()
    return True