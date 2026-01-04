# src/backend/routes/admin_employees_pages.py
from __future__ import annotations

import math
from typing import Optional, Dict, Any, cast

from fastapi import (
    APIRouter,
    Request,
    Depends,
    HTTPException,
    Form,
    Query,
    UploadFile,
    File,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from src.backend.utils.database import get_db
from src.backend.utils.auth import get_current_user
from src.backend.models.user import User
from src.backend.utils.view import render
from src.backend.utils.flash import flash_popall, redirect_with_flash
from src.backend.utils import csrf as csrf_mod

# shared context & permission system
from src.backend.utils.common_context import add_common, require_admin
from src.backend.utils.permissions import require_view, require_create, require_edit, require_delete

from src.backend.crud.employee import (
    list_employees,
    get_employee,
    create_employee,
    update_employee,
    delete_employee,
    list_groups,
    list_orgs,
    list_zones,
    list_branches,
    list_designations,
)

from src.backend.schemas.employee import EmployeeCreate, EmployeeUpdate, EMP_TYPE_VALUES
from src.backend.schemas.employee_pg_dropdown import OrgOut, ZoneOut, BranchOut, DesigOut

from src.backend.utils.image_media import save_media_with_key, delete_media_file

router = APIRouter(prefix="/admin/employees", tags=["Admin Employees"])

TEAM_SUBDIR = "team"
ALLOWED_TEAM_TYPES = frozenset({
    "image/avif", "image/webp", "image/png", "image/jpeg", "image/jpg",
})
MAX_TEAM_MB = 2


def _strip(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    s = v.strip()
    return s if s else None


async def _load_dropdowns_for_form(db: AsyncSession, *, group_id: Optional[str], org_id: Optional[str], zone_id: Optional[str]):
    groups = await list_groups(db)
    desigs = await list_designations(db)
    orgs = await list_orgs(db, group_id) if group_id else []
    zones = await list_zones(db, org_id) if org_id else []
    branches = await list_branches(db, zone_id) if zone_id else []
    return groups, orgs, zones, branches, desigs


# ----------------------------------------------------------
# LIST PAGE
# ----------------------------------------------------------
@router.get("", dependencies=[Depends(require_view)])
async def list_page(
    request: Request,
    q: Optional[str] = Query(None),
    emp_type: Optional[str] = Query("all"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=5, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    offset = (page - 1) * size
    if emp_type not in ("all", *EMP_TYPE_VALUES):
        emp_type = "all"

    rows, total = await list_employees(db, q=q, emp_type=emp_type, limit=size, offset=offset)
    pages = math.ceil(total / size) if size else 1

    ctx: Dict[str, Any] = {
        "request": request,
        "title": "Manage Employees",
        "rows": rows,
        "q": q or "",
        "page": page,
        "pages": pages,
        "size": size,
        "total": total,
        "emp_types": EMP_TYPE_VALUES,
        "selected_emp_type": emp_type,
        "flashes": await flash_popall(request.session),
    }
    await add_common(ctx, db, current_user, request=request)
    return await render("admin/employees/index.html", ctx)


# ----------------------------------------------------------
# NEW FORM
# ----------------------------------------------------------
@router.get("/new", dependencies=[Depends(require_create)])
async def new_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    groups, orgs, zones, branches, desigs = await _load_dropdowns_for_form(
        db, group_id=None, org_id=None, zone_id=None
    )

    ctx: Dict[str, Any] = {
        "request": request,
        "title": "Create Employee",
        "mode": "create",
        "form": {
            "emp_id": "",
            "emp_name": "",
            "gender": "",
            "dob": "",
            "mobile": "",
            "email": "",
            "join_date": "",
            "group_id": "",
            "org_id": "",
            "zone_id": "",
            "br_id": "",
            "desig_id": "",
            "nid": "",
            "blood_group": "",
            "address": "",
            "emergency_phone": "",
            "photo_url": "",
            "status": "active",
            "emp_type": "Contractual",
            "bio": "",
            "linkedin_url": "",
            "sort_order": None,
            "bio_details": "",
        },
        "groups": groups,
        "orgs": orgs,
        "zones": zones,
        "branches": branches,
        "designations": desigs,
        "emp_types": EMP_TYPE_VALUES,
        "flashes": await flash_popall(request.session),
    }

    await add_common(ctx, db, current_user, request=request)
    return await render("admin/employees/form.html", ctx)


# ----------------------------------------------------------
# EDIT FORM
# ----------------------------------------------------------
@router.get("/{emp_id}/edit", dependencies=[Depends(require_edit)])
async def edit_page(
    request: Request,
    emp_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    row = await get_employee(db, emp_id)
    if not row:
        raise HTTPException(status_code=404, detail="Employee not found")

    group_id = _strip(getattr(row, "group_id", None))
    org_id = _strip(getattr(row, "org_id", None))
    zone_id = _strip(getattr(row, "zone_id", None))

    groups, orgs, zones, branches, desigs = await _load_dropdowns_for_form(
        db, group_id=group_id, org_id=org_id, zone_id=zone_id
    )

    title_name = (getattr(row, "emp_name", None) or "").strip() or "Employee"

    ctx: Dict[str, Any] = {
        "request": request,
        "title": f"Edit Employee — {title_name} ({emp_id})",
        "mode": "edit",
        "form": {
            "emp_id": row.emp_id,
            "emp_name": row.emp_name,
            "gender": row.gender,
            "dob": str(row.dob) if row.dob else "",
            "mobile": row.mobile,
            "email": row.email,
            "join_date": str(row.join_date) if row.join_date else "",

            "group_id": row.group_id,
            "org_id": row.org_id,
            "zone_id": row.zone_id,
            "br_id": row.br_id,
            "desig_id": row.desig_id,

            "nid": row.nid,
            "blood_group": row.blood_group,
            "address": row.address,
            "emergency_phone": row.emergency_phone,
            "photo_url": row.photo_url,

            "status": row.status or "active",

            # NEW
            "emp_type": row.emp_type or "Contractual",
            "bio": row.bio,
            "linkedin_url": row.linkedin_url,
            "sort_order": row.sort_order,
            "bio_details": row.bio_details,
        },
        "groups": groups,
        "orgs": orgs,
        "zones": zones,
        "branches": branches,
        "designations": desigs,
        "emp_types": EMP_TYPE_VALUES,
        "flashes": await flash_popall(request.session),
    }

    await add_common(ctx, db, current_user, request=request)
    return await render("admin/employees/form.html", ctx)


# ----------------------------------------------------------
# CREATE ACTION
# ----------------------------------------------------------
@router.post("", dependencies=[Depends(csrf_mod.csrf_protect), Depends(require_create)])
async def create_action(
    request: Request,
    emp_id: str = Form(...),
    emp_name: str = Form(...),
    gender: Optional[str] = Form(None),
    dob: Optional[str] = Form(None),
    mobile: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    join_date: Optional[str] = Form(None),

    group_id: Optional[str] = Form(None),
    org_id: Optional[str] = Form(None),
    zone_id: Optional[str] = Form(None),
    br_id: Optional[str] = Form(None),
    desig_id: Optional[str] = Form(None),

    nid: Optional[str] = Form(None),
    blood_group: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    emergency_phone: Optional[str] = Form(None),

    # upload
    photo_file: Optional[UploadFile] = File(None),
    photo_url: Optional[str] = Form(None),

    status: Optional[str] = Form("active"),

    # NEW
    emp_type: Optional[str] = Form("Contractual"),
    bio: Optional[str] = Form(None),
    linkedin_url: Optional[str] = Form(None),
    sort_order: Optional[int] = Form(None),
    bio_details: Optional[str] = Form(None),

    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)
    created_by = cast(str, getattr(current_user, "login_id", "System")) or "System"

    # Start from manual URL (if provided)
    final_photo_url = (photo_url or "").strip() or None

    # If an upload is provided, it wins
    if photo_file is not None and (photo_file.filename or "").strip():
        try:
            final_photo_url = save_media_with_key(
                subdir=TEAM_SUBDIR,
                upload=photo_file,
                record_key=emp_id,  # keep leading zeros
                allowed_types=ALLOWED_TEAM_TYPES,
                max_size_mb=MAX_TEAM_MB,
            )
        except HTTPException as e:
            groups, orgs, zones, branches, desigs = await _load_dropdowns_for_form(
                db, group_id=_strip(group_id), org_id=_strip(org_id), zone_id=_strip(zone_id)
            )
            ctx: Dict[str, Any] = {
                "request": request,
                "title": "Create Employee",
                "mode": "create",
                "error": f"Error saving photo: {e.detail}",
                "flashes": await flash_popall(request.session),
                "form": {
                    "emp_id": emp_id,
                    "emp_name": emp_name,
                    "gender": gender,
                    "dob": dob,
                    "mobile": mobile,
                    "email": email,
                    "join_date": join_date,

                    "group_id": group_id,
                    "org_id": org_id,
                    "zone_id": zone_id,
                    "br_id": br_id,
                    "desig_id": desig_id,

                    "nid": nid,
                    "blood_group": blood_group,
                    "address": address,
                    "emergency_phone": emergency_phone,
                    "photo_url": final_photo_url or "",

                    "status": status,
                    "emp_type": emp_type,
                    "bio": bio,
                    "linkedin_url": linkedin_url,
                    "sort_order": sort_order,
                    "bio_details": bio_details,
                },
                "groups": groups,
                "orgs": orgs,
                "zones": zones,
                "branches": branches,
                "designations": desigs,
                "emp_types": EMP_TYPE_VALUES,
            }
            await add_common(ctx, db, current_user, request=request)
            return await render("admin/employees/form.html", ctx)

    payload = EmployeeCreate(
        emp_id=emp_id,
        emp_name=emp_name,
        gender=gender,
        dob=dob,
        mobile=mobile,
        email=email,
        join_date=join_date,

        group_id=group_id,
        org_id=org_id,
        zone_id=zone_id,
        br_id=br_id,
        desig_id=desig_id,

        nid=nid,
        blood_group=blood_group,
        address=address,
        emergency_phone=emergency_phone,
        photo_url=final_photo_url,

        status=status,

        emp_type=emp_type,
        bio=bio,
        linkedin_url=linkedin_url,
        sort_order=sort_order,
        bio_details=bio_details,
    )

    try:
        row = await create_employee(db, payload, created_by=created_by)
        return await redirect_with_flash(
            request.session, "/admin/employees", "success", f"Employee {row.emp_id} created"
        )
    except IntegrityError:
        # If DB failed and we uploaded a file, delete it to avoid orphan files
        if final_photo_url and final_photo_url.startswith("/images/"):
            try:
                delete_media_file(final_photo_url)
            except Exception:
                pass

        groups, orgs, zones, branches, desigs = await _load_dropdowns_for_form(
            db, group_id=_strip(group_id), org_id=_strip(org_id), zone_id=_strip(zone_id)
        )
        ctx: Dict[str, Any] = {
            "request": request,
            "title": "Create Employee",
            "mode": "create",
            "form": payload.model_dump(),
            "groups": groups,
            "orgs": orgs,
            "zones": zones,
            "branches": branches,
            "designations": desigs,
            "emp_types": EMP_TYPE_VALUES,
            "error": "Employee already exists or invalid data.",
            "flashes": await flash_popall(request.session),
        }
        await add_common(ctx, db, current_user, request=request)
        return await render("admin/employees/form.html", ctx)


# ----------------------------------------------------------
# UPDATE ACTION
# ----------------------------------------------------------
@router.post("/{emp_id}", dependencies=[Depends(csrf_mod.csrf_protect), Depends(require_edit)])
async def update_action(
    request: Request,
    emp_id: str,
    emp_name: str = Form(...),
    gender: Optional[str] = Form(None),
    dob: Optional[str] = Form(None),
    mobile: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    join_date: Optional[str] = Form(None),

    group_id: Optional[str] = Form(None),
    org_id: Optional[str] = Form(None),
    zone_id: Optional[str] = Form(None),
    br_id: Optional[str] = Form(None),
    desig_id: Optional[str] = Form(None),

    nid: Optional[str] = Form(None),
    blood_group: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    emergency_phone: Optional[str] = Form(None),

    # upload
    photo_file: Optional[UploadFile] = File(None),
    photo_url: Optional[str] = Form(None),
    deletePhotoFlag: Optional[str] = Form(None),

    status: Optional[str] = Form("active"),

    # NEW
    emp_type: Optional[str] = Form("Contractual"),
    bio: Optional[str] = Form(None),
    linkedin_url: Optional[str] = Form(None),
    sort_order: Optional[int] = Form(None),
    bio_details: Optional[str] = Form(None),

    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)
    updated_by = cast(str, getattr(current_user, "login_id", "System")) or "System"

    existing = await get_employee(db, emp_id)
    if not existing:
        return await redirect_with_flash(request.session, "/admin/employees", "danger", "Employee not found")

    existing_url = (getattr(existing, "photo_url", None) or "").strip()
    final_photo_url = (photo_url or "").strip() or existing_url or None

    # Delete request
    if deletePhotoFlag == "1":
        if existing_url and existing_url.startswith("/images/"):
            try:
                delete_media_file(existing_url)
            except Exception:
                pass
        final_photo_url = None

    # Replace with uploaded file
    if photo_file is not None and (photo_file.filename or "").strip():
        # delete old stored image first
        if existing_url and existing_url.startswith("/images/"):
            try:
                delete_media_file(existing_url)
            except Exception:
                pass

        try:
            final_photo_url = save_media_with_key(
                subdir=TEAM_SUBDIR,
                upload=photo_file,
                record_key=emp_id,
                allowed_types=ALLOWED_TEAM_TYPES,
                max_size_mb=MAX_TEAM_MB,
            )
        except HTTPException as e:
            # re-render edit page with error
            groups, orgs, zones, branches, desigs = await _load_dropdowns_for_form(
                db, group_id=_strip(group_id), org_id=_strip(org_id), zone_id=_strip(zone_id)
            )
            title_name = (getattr(existing, "emp_name", None) or "").strip() or "Employee"
            ctx: Dict[str, Any] = {
                "request": request,
                "title": f"Edit Employee — {title_name} ({emp_id})",
                "mode": "edit",
                "error": f"Error saving photo: {e.detail}",
                "flashes": await flash_popall(request.session),
                "form": {
                    "emp_id": emp_id,
                    "emp_name": emp_name,
                    "gender": gender,
                    "dob": dob,
                    "mobile": mobile,
                    "email": email,
                    "join_date": join_date,

                    "group_id": group_id,
                    "org_id": org_id,
                    "zone_id": zone_id,
                    "br_id": br_id,
                    "desig_id": desig_id,

                    "nid": nid,
                    "blood_group": blood_group,
                    "address": address,
                    "emergency_phone": emergency_phone,
                    "photo_url": existing_url,  # keep old in UI

                    "status": status,
                    "emp_type": emp_type,
                    "bio": bio,
                    "linkedin_url": linkedin_url,
                    "sort_order": sort_order,
                    "bio_details": bio_details,
                },
                "groups": groups,
                "orgs": orgs,
                "zones": zones,
                "branches": branches,
                "designations": desigs,
                "emp_types": EMP_TYPE_VALUES,
            }
            await add_common(ctx, db, current_user, request=request)
            return await render("admin/employees/form.html", ctx)

    payload = EmployeeUpdate(
        emp_name=emp_name,
        gender=gender,
        dob=dob,
        mobile=mobile,
        email=email,
        join_date=join_date,

        group_id=group_id,
        org_id=org_id,
        zone_id=zone_id,
        br_id=br_id,
        desig_id=desig_id,

        nid=nid,
        blood_group=blood_group,
        address=address,
        emergency_phone=emergency_phone,
        photo_url=final_photo_url,

        status=status,

        emp_type=emp_type,
        bio=bio,
        linkedin_url=linkedin_url,
        sort_order=sort_order,
        bio_details=bio_details,
    )

    row = await update_employee(db, emp_id, payload, updated_by=updated_by)
    if not row:
        return await redirect_with_flash(request.session, "/admin/employees", "danger", "Employee not found")

    return await redirect_with_flash(request.session, "/admin/employees", "success", f"Employee {emp_id} updated")


# ----------------------------------------------------------
# DELETE ACTION
# ----------------------------------------------------------
@router.post("/{emp_id}/delete", dependencies=[Depends(csrf_mod.csrf_protect), Depends(require_delete)])
async def delete_action(
    request: Request,
    emp_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    # also delete stored image if exists
    existing = await get_employee(db, emp_id)
    if existing:
        existing_url = (getattr(existing, "photo_url", None) or "").strip()
        if existing_url and existing_url.startswith("/images/"):
            try:
                delete_media_file(existing_url)
            except Exception:
                pass

    await delete_employee(db, emp_id)
    return await redirect_with_flash(request.session, "/admin/employees", "success", f"Employee {emp_id} deleted")


# ----------------------------------------------------------
# JSON options for orgs/zones/branches/designations
# ----------------------------------------------------------
@router.get("/options/orgs", response_model=list[OrgOut])
async def get_orgs_by_group(
    group_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    orgs = await list_orgs(db, group_id)
    return [OrgOut(org_id=o.org_id, org_name=o.org_name) for o in orgs]


@router.get("/options/zones", response_model=list[ZoneOut])
async def get_zones_by_org(
    org_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    zones = await list_zones(db, org_id)
    return [ZoneOut(zone_id=z.zone_id, zone_name=z.zone_name) for z in zones]


@router.get("/options/branches", response_model=list[BranchOut])
async def get_branches_by_zone(
    zone_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    branches = await list_branches(db, zone_id)
    return [BranchOut(br_id=b.br_id, br_name=b.br_name) for b in branches]


@router.get("/options/designations", response_model=list[DesigOut])
async def get_designations(
    db: AsyncSession = Depends(get_db),
):
    desigs = await list_designations(db)
    return [DesigOut(desig_id=d.desig_id, desig_name=d.desig_name) for d in desigs]