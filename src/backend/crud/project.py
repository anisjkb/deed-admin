# src/backend/crud/project.py
from __future__ import annotations

from typing import Optional, Tuple, List
from datetime import date, datetime

from sqlalchemy import select, or_, delete, String, cast as sa_cast
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.models.ops.project_info import ProjectInfo, ProjectType, ProjectStatus
from src.backend.models.org.br_info import BranchInfo
from src.backend.models.org.emp_info import EmpInfo
from src.backend.schemas.project import ProjectCreate, ProjectUpdate
from src.backend.utils.timezone import now_local

def _s(v: Optional[str]) -> Optional[str]:
    v = (v or "").strip()
    return v if v else None

def _date(v: Optional[str]) -> Optional[date]:
    v = (v or "").strip()
    if not v:
        return None
    try:
        y, m, d = (int(x) for x in v.split("-"))
        return date(y, m, d)
    except Exception:
        return None

def _now_naive() -> datetime:
    dt = now_local()
    return dt.replace(tzinfo=None) if getattr(dt, "tzinfo", None) else dt

def _ptype(v: Optional[str]) -> ProjectType:
    """Map incoming string (or None) to ProjectType enum; default residential."""
    try:
        return ProjectType((v or "residential").strip().lower())
    except Exception:
        return ProjectType.residential

def _pstatus(v: Optional[str]) -> ProjectStatus:
    """Map incoming string (or None) to ProjectStatus enum; default ongoing."""
    try:
        return ProjectStatus((v or "ongoing").strip().lower())
    except Exception:
        return ProjectStatus.ongoing

# ---------- helpers for selects ----------

async def list_branches_all(db: AsyncSession) -> List[BranchInfo]:
    res = await db.execute(
        select(BranchInfo)
        .where(BranchInfo.status == "active")
        .order_by(BranchInfo.br_id)
    )
    return list(res.scalars().all())

async def list_employees_active(db: AsyncSession) -> List[EmpInfo]:
    res = await db.execute(
        select(EmpInfo)
        .where(EmpInfo.status == "active")
        .order_by(EmpInfo.emp_id)
    )
    return list(res.scalars().all())

# ---------- list/search ----------

async def list_projects(
    db: AsyncSession, q: Optional[str], limit: int, offset: int
) -> Tuple[List[ProjectInfo], int]:
    stmt = select(ProjectInfo)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                ProjectInfo.slug.ilike(like),
                ProjectInfo.title.ilike(like),
                ProjectInfo.location.ilike(like),
                sa_cast(ProjectInfo.status, String).ilike(like),
                sa_cast(ProjectInfo.ptype, String).ilike(like),
            )
        )

    stmt = stmt.order_by(ProjectInfo.id.asc())

    res_count = await db.execute(stmt.with_only_columns(ProjectInfo.id).order_by(None))
    total = len(res_count.scalars().all())

    res = await db.execute(stmt.limit(limit).offset(offset))
    rows = list(res.scalars().all())
    return rows, total

# ---------- single ----------

async def get_project(db: AsyncSession, pid: int) -> Optional[ProjectInfo]:
    res = await db.execute(select(ProjectInfo).where(ProjectInfo.id == pid))
    return res.scalar_one_or_none()

# ---------- create/update/delete ----------

async def create_project(
    db: AsyncSession,
    data: ProjectCreate,
    created_by: str,
) -> ProjectInfo:
    """
    Create project row.
    All media (hero_image_url / brochure_url) are already URLs passed from routes.
    """
    row = ProjectInfo(
        slug=data.slug,
        title=data.title,
        tagline=_s(data.tagline),

        # ✅ enum-safe
        status=_pstatus(data.status),
        ptype=_ptype(data.ptype),

        location=_s(data.location),

        progress_pct=data.progress_pct if data.progress_pct is not None else 0,
        handover_date=_date(data.handover_date),

        land_area_sft=data.land_area_sft,
        floors=data.floors,
        units_total=data.units_total,
        parking_spaces=data.parking_spaces,
        frontage_ft=data.frontage_ft,
        orientation=_s(data.orientation),
        size_range=_s(data.size_range),

        brochure_url=_s(data.brochure_url),
        hero_image_url=_s(data.hero_image_url),
        video_url=_s(data.video_url),

        short_desc=_s(data.short_desc),
        highlights=_s(data.highlights),
        partners=_s(data.partners),

        br_id=_s(data.br_id),
        emp_id=_s(data.emp_id),

        published=_s(data.published),

        created_by=created_by,
        updated_by=created_by,
        created_at=_now_naive(),
        updated_at=_now_naive(),
    )

    db.add(row)
    try:
        await db.commit()
        await db.refresh(row)
    except IntegrityError:
        await db.rollback()
        raise
    return row

async def update_project(
    db: AsyncSession,
    pid: int,
    data: ProjectUpdate,
    updated_by: str,
) -> Optional[ProjectInfo]:
    """
    Update existing project.
    Media URLs are passed in from routes after saving files.
    """
    row = await get_project(db, pid)
    if not row:
        return None

    # Basic fields
    if data.slug is not None:
        row.slug = data.slug
    if data.title is not None:
        row.title = data.title
    if data.tagline is not None:
        row.tagline = _s(data.tagline)

    # ✅ enum-safe
    if data.status is not None:
        row.status = _pstatus(data.status)
    if data.ptype is not None:
        row.ptype = _ptype(data.ptype)

    if data.location is not None:
        row.location = _s(data.location)

    if data.progress_pct is not None:
        row.progress_pct = data.progress_pct

    # handover_date: only update if provided and valid
    if data.handover_date is not None:
        parsed = _date(data.handover_date)
        if parsed is not None:
            row.handover_date = parsed

    # Numbers
    if data.land_area_sft is not None:
        row.land_area_sft = data.land_area_sft
    if data.floors is not None:
        row.floors = data.floors
    if data.units_total is not None:
        row.units_total = data.units_total
    if data.parking_spaces is not None:
        row.parking_spaces = data.parking_spaces
    if data.frontage_ft is not None:
        row.frontage_ft = data.frontage_ft
    if data.orientation is not None:
        row.orientation = _s(data.orientation)
    if data.size_range is not None:
        row.size_range = _s(data.size_range)

    # Media URLs
    if data.brochure_url is not None:
        row.brochure_url = _s(data.brochure_url)
    if data.hero_image_url is not None:
        row.hero_image_url = _s(data.hero_image_url)
    if data.video_url is not None:
        row.video_url = _s(data.video_url)

    # Copy
    if data.short_desc is not None:
        row.short_desc = _s(data.short_desc)
    if data.highlights is not None:
        row.highlights = _s(data.highlights)
    if data.partners is not None:
        row.partners = _s(data.partners)

    # Metadata
    if data.br_id is not None:
        row.br_id = _s(data.br_id)
    if data.emp_id is not None:
        row.emp_id = _s(data.emp_id)
    if data.published is not None:
        row.published = _s(data.published)

    row.updated_by = updated_by
    row.updated_at = _now_naive()

    try:
        await db.commit()
        await db.refresh(row)
    except IntegrityError:
        await db.rollback()
        raise
    return row

async def delete_project(db: AsyncSession, pid: int) -> bool:
    await db.execute(delete(ProjectInfo).where(ProjectInfo.id == pid))
    await db.commit()
    return True