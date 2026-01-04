# src/backend/routes/project_admin_pages.py
from __future__ import annotations

import math
from typing import Optional, Dict, Any, cast

from fastapi import (
    APIRouter,
    File,
    Request,
    Depends,
    HTTPException,
    Form,
    Query,
    UploadFile,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from src.backend.utils.database import get_db
from src.backend.utils.auth import get_current_user
from src.backend.models.user import User
from src.backend.utils.view import render
from src.backend.utils.flash import flash_popall, redirect_with_flash
from src.backend.utils import csrf as csrf_mod

from src.backend.utils.common_context import add_common, require_admin
from src.backend.utils.permissions import (
    require_view,
    require_create,
    require_edit,
    require_delete,
)

from src.backend.crud.project import (
    list_projects,
    get_project,
    create_project,
    update_project,
    delete_project,
    list_branches_all,
    list_employees_active,
)

from src.backend.schemas.project import ProjectCreate, ProjectUpdate
from src.backend.utils.image_media import save_media_with_id, delete_media_file

router = APIRouter(prefix="/admin/projects", tags=["Admin Projects"])


# ============================================================
# Helpers
# ============================================================
def _to_int(v: Optional[str]) -> Optional[int]:
    """Convert Form str to int or None (safe)."""
    if v is None:
        return None
    s = v.strip()
    if s == "":
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _to_int0(v: Optional[str]) -> int:
    """Convert Form str to int; default 0."""
    x = _to_int(v)
    return x if x is not None else 0


# Allow modern image formats
ALLOWED_IMG_TYPES = frozenset(
    {"image/jpeg", "image/jpg", "image/png", "image/avif", "image/webp"}
)
ALLOWED_BROCHURE_TYPES = frozenset(
    {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/avif",
        "image/webp",
        "application/pdf",
    }
)


# ============================================================
#                       LIST
# ============================================================
@router.get("", dependencies=[Depends(require_view)])
async def list_page(
    request: Request,
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=5, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    offset = (page - 1) * size
    rows, total = await list_projects(db, q=q, limit=size, offset=offset)

    # Enrich with branch/employee names
    branches = await list_branches_all(db)
    emps = await list_employees_active(db)

    br_map = {b.br_id: b.br_name for b in branches}
    emp_map = {e.emp_id: e.emp_name for e in emps}

    for r in rows:
        br_id = getattr(r, "br_id", None)
        setattr(r, "br_name", br_map.get(str(br_id)) if br_id is not None else None)
        emp_id = getattr(r, "emp_id", None)
        setattr(r, "emp_name", emp_map.get(str(emp_id)) if emp_id is not None else None)

    pages = math.ceil(total / size) if size else 1

    ctx: Dict[str, Any] = {
        "request": request,
        "title": "Projects",
        "rows": rows,
        "q": q or "",
        "page": page,
        "pages": pages,
        "size": size,
        "total": total,
        "flashes": await flash_popall(request.session),
    }
    await add_common(ctx, db, current_user, request=request)
    return await render("admin/projects/index.html", ctx)


# ============================================================
#                       NEW (GET)
# ============================================================
@router.get("/new", dependencies=[Depends(require_create)])
async def new_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    branches = await list_branches_all(db)
    emps = await list_employees_active(db)

    ctx: Dict[str, Any] = {
        "request": request,
        "title": "Create Project",
        "mode": "create",
        "form": {
            "status": "ongoing",
            "ptype": "residential",
            "progress_pct": 0,
            "published": "Yes",
        },
        "branches": branches,
        "employees": emps,
        "flashes": await flash_popall(request.session),
    }
    await add_common(ctx, db, current_user, request=request)
    return await render("admin/projects/form.html", ctx)


# ============================================================
#                       EDIT (GET)
# ============================================================
@router.get("/{pid}/edit", dependencies=[Depends(require_edit)])
async def edit_page(
    request: Request,
    pid: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    row = await get_project(db, pid)
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")

    branches = await list_branches_all(db)
    emps = await list_employees_active(db)

    ctx: Dict[str, Any] = {
        "request": request,
        "title": f"Edit Project {row.slug}",
        "mode": "edit",
        "form": {
            "id": row.id,
            "slug": row.slug,
            "title": row.title,
            "tagline": row.tagline,
            "status": row.status,
            "ptype": row.ptype,
            "location": row.location,
            "progress_pct": row.progress_pct,
            "handover_date": (row.handover_date.isoformat() if row.handover_date else ""),
            "land_area_sft": row.land_area_sft,
            "floors": row.floors,
            "units_total": row.units_total,
            "parking_spaces": row.parking_spaces,
            "frontage_ft": row.frontage_ft,
            "orientation": row.orientation,
            "size_range": row.size_range,
            "brochure_url": row.brochure_url,
            "hero_image_url": row.hero_image_url,
            "video_url": row.video_url,
            "short_desc": row.short_desc,
            "highlights": row.highlights,
            "partners": row.partners,
            "br_id": row.br_id,
            "emp_id": row.emp_id,
            "published": row.published,
        },
        "branches": branches,
        "employees": emps,
        "flashes": await flash_popall(request.session),
    }
    await add_common(ctx, db, current_user, request=request)
    return await render("admin/projects/form.html", ctx)


# ============================================================
#                       CREATE (POST)
# ============================================================
@router.post("", dependencies=[Depends(csrf_mod.csrf_protect), Depends(require_create)])
async def create_action(
    request: Request,
    slug: str = Form(...),
    title: str = Form(...),
    tagline: Optional[str] = Form(None),
    status: Optional[str] = Form("ongoing"),
    ptype: Optional[str] = Form("residential"),
    location: Optional[str] = Form(None),

    progress_pct: Optional[str] = Form("0"),
    handover_date: Optional[str] = Form(None),

    land_area_sft: Optional[str] = Form(None),
    floors: Optional[str] = Form(None),
    units_total: Optional[str] = Form(None),
    parking_spaces: Optional[str] = Form(None),
    frontage_ft: Optional[str] = Form(None),
    orientation: Optional[str] = Form(None),
    size_range: Optional[str] = Form(None),

    hero_image_file: Optional[UploadFile] = File(None),
    brochure_file: Optional[UploadFile] = File(None),

    published: str = Form("Yes"),
    video_url: Optional[str] = Form(None),
    short_desc: Optional[str] = Form(None),
    highlights: Optional[str] = Form(None),
    partners: Optional[str] = Form(None),

    br_id: Optional[str] = Form(None),
    emp_id: Optional[str] = Form(None),

    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    progress_int = _to_int0(progress_pct)

    payload_no_media = ProjectCreate(
        slug=slug,
        title=title,
        tagline=tagline,
        status=status,
        ptype=ptype,
        location=location,

        progress_pct=progress_int,
        handover_date=handover_date,

        land_area_sft=_to_int(land_area_sft),
        floors=_to_int(floors),
        units_total=_to_int(units_total),
        parking_spaces=_to_int(parking_spaces),
        frontage_ft=_to_int(frontage_ft),

        orientation=orientation,
        size_range=size_range,

        brochure_url="",
        hero_image_url="",
        video_url=video_url,
        short_desc=short_desc,
        highlights=highlights,
        partners=partners,

        br_id=br_id,
        emp_id=emp_id,
        published=published,
    )

    try:
        created_by = cast(str, getattr(current_user, "login_id", "System")) or "System"
        row = await create_project(db, payload_no_media, created_by=created_by)
    except IntegrityError:
        branches = await list_branches_all(db)
        emps = await list_employees_active(db)
        ctx: Dict[str, Any] = {
            "request": request,
            "title": "Create Project",
            "mode": "create",
            "form": payload_no_media.model_dump(),
            "branches": branches,
            "employees": emps,
            "error": "Project slug already exists or invalid data.",
            "flashes": await flash_popall(request.session),
        }
        await add_common(ctx, db, current_user, request=request)
        return await render("admin/projects/form.html", ctx)

    hero_image_url = ""
    brochure_url = ""

    # Save hero image (supports avif/webp/jpg/png)
    if hero_image_file and hero_image_file.filename:
        hero_image_url = save_media_with_id(
            subdir="projects",
            upload=hero_image_file,
            record_id=row.id,
            allowed_types=ALLOWED_IMG_TYPES,
        )

    # Save brochure (supports pdf + images)
    if brochure_file and brochure_file.filename:
        brochure_url = save_media_with_id(
            subdir="projects/brochures",
            upload=brochure_file,
            record_id=row.id,
            allowed_types=ALLOWED_BROCHURE_TYPES,
        )

    update_payload = ProjectUpdate(
        slug=slug,
        title=title,
        tagline=tagline,
        status=status,
        ptype=ptype,
        location=location,

        progress_pct=progress_int,
        handover_date=handover_date,

        land_area_sft=_to_int(land_area_sft),
        floors=_to_int(floors),
        units_total=_to_int(units_total),
        parking_spaces=_to_int(parking_spaces),
        frontage_ft=_to_int(frontage_ft),

        orientation=orientation,
        size_range=size_range,

        brochure_url=brochure_url,
        hero_image_url=hero_image_url,
        video_url=video_url,
        short_desc=short_desc,
        highlights=highlights,
        partners=partners,

        br_id=br_id,
        emp_id=emp_id,
        published=published,
    )

    await update_project(db, row.id, update_payload, updated_by=created_by)

    return await redirect_with_flash(
        request.session,
        "/admin/projects",
        "success",
        f"Project {row.slug} created",
    )


# ============================================================
#                       UPDATE (POST)
# ============================================================
@router.post("/{pid}", dependencies=[Depends(csrf_mod.csrf_protect), Depends(require_edit)])
async def update_action(
    request: Request,
    pid: int,
    slug: Optional[str] = Form(None),
    title: str = Form(...),
    tagline: Optional[str] = Form(None),
    status: Optional[str] = Form("ongoing"),
    ptype: Optional[str] = Form("residential"),
    location: Optional[str] = Form(None),

    progress_pct: Optional[str] = Form("0"),
    handover_date: Optional[str] = Form(None),

    land_area_sft: Optional[str] = Form(None),
    floors: Optional[str] = Form(None),
    units_total: Optional[str] = Form(None),
    parking_spaces: Optional[str] = Form(None),
    frontage_ft: Optional[str] = Form(None),
    orientation: Optional[str] = Form(None),
    size_range: Optional[str] = Form(None),

    hero_image_file: Optional[UploadFile] = File(None),
    brochure_file: Optional[UploadFile] = File(None),

    video_url: Optional[str] = Form(None),
    short_desc: Optional[str] = Form(None),
    highlights: Optional[str] = Form(None),
    partners: Optional[str] = Form(None),

    br_id: Optional[str] = Form(None),
    emp_id: Optional[str] = Form(None),
    published: str = Form(...),

    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    existing = await get_project(db, pid)
    if not existing:
        return await redirect_with_flash(
            request.session, "/admin/projects", "danger", "Project not found"
        )

    progress_int = _to_int0(progress_pct)

    hero_image_url_str = existing.hero_image_url or ""
    brochure_url_str = existing.brochure_url or ""

    if hero_image_file and hero_image_file.filename:
        hero_image_url_str = save_media_with_id(
            subdir="projects",
            upload=hero_image_file,
            record_id=pid,
            allowed_types=ALLOWED_IMG_TYPES,
        )

    if brochure_file and brochure_file.filename:
        brochure_url_str = save_media_with_id(
            subdir="projects/brochures",
            upload=brochure_file,
            record_id=pid,
            allowed_types=ALLOWED_BROCHURE_TYPES,
        )

    payload = ProjectUpdate(
        slug=slug or existing.slug,
        title=title,
        tagline=tagline,
        status=status,
        ptype=ptype,
        location=location,

        progress_pct=progress_int,
        handover_date=handover_date,

        land_area_sft=_to_int(land_area_sft),
        floors=_to_int(floors),
        units_total=_to_int(units_total),
        parking_spaces=_to_int(parking_spaces),
        frontage_ft=_to_int(frontage_ft),

        orientation=orientation,
        size_range=size_range,

        brochure_url=brochure_url_str,
        hero_image_url=hero_image_url_str,
        video_url=video_url,
        short_desc=short_desc,
        highlights=highlights,
        partners=partners,

        br_id=br_id,
        emp_id=emp_id,
        published=published,
    )

    updated_by = cast(str, getattr(current_user, "login_id", "System")) or "System"
    row = await update_project(db, pid, payload, updated_by=updated_by)
    if not row:
        return await redirect_with_flash(
            request.session, "/admin/projects", "danger", "Project not found"
        )

    return await redirect_with_flash(
        request.session, "/admin/projects", "success", f"Project {row.slug} updated"
    )


# ============================================================
#                       DELETE
# ============================================================
@router.post("/{pid}/delete", dependencies=[Depends(csrf_mod.csrf_protect), Depends(require_delete)])
async def delete_action(
    request: Request,
    pid: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    row = await get_project(db, pid)
    if not row:
        return await redirect_with_flash(
            request.session, "/admin/projects", "danger", "Project not found"
        )

    if row.hero_image_url:
        try:
            delete_media_file(row.hero_image_url)
        except Exception:
            pass

    if row.brochure_url:
        try:
            delete_media_file(row.brochure_url)
        except Exception:
            pass

    await delete_project(db, pid)

    return await redirect_with_flash(
        request.session, "/admin/projects", "success", f"Project #{pid} deleted"
    )


# ============================================================
#                       JSON OPTIONS
# ============================================================
@router.get("/options/branches", dependencies=[Depends(require_view)])
async def branches_options(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)
    items = await list_branches_all(db)
    return [{"br_id": x.br_id, "br_name": x.br_name} for x in items]


@router.get("/options/employees", dependencies=[Depends(require_view)])
async def employees_options(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)
    items = await list_employees_active(db)
    return [{"emp_id": x.emp_id, "emp_name": x.emp_name} for x in items]