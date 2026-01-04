# src/backend/routes/routes_testimonials.py
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any, cast
from src.backend.utils.database import get_db
from src.backend.utils.auth import get_current_user
from src.backend.models.user import User
from src.backend.utils.view import render
from src.backend.utils.flash import flash_popall, redirect_with_flash
from src.backend.utils.common_context import add_common, require_admin
from src.backend.utils.permissions import require_view, require_create, require_edit, require_delete
from src.backend.crud.testimonial import (
    list_testimonials, get_testimonial, create_testimonial, 
    update_testimonial, delete_testimonial, list_projects,get_project_title_by_id
    )
from src.backend.schemas.testimonial_schema import TestimonialCreate, TestimonialUpdate
from src.backend.utils import csrf as csrf_mod
from sqlalchemy.exc import IntegrityError
import logging

router = APIRouter(prefix="/admin/testimonials", tags=["Admin Testimonials"])

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

# List testimonials
@router.get("", dependencies=[Depends(require_view)])
async def list_testimonials_page(
    request: Request,
    q: Optional[str] = None,
    page: int = 1,
    size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    q = q or ""
    offset = (page - 1) * size
    try:
        rows = await list_testimonials(db, q=q, limit=size, offset=offset)
        total = len(rows)
        pages = (total // size) + 1 if size else 1

        ctx: Dict[str, Any] = {
            "request": request,
            "title": "Manage Testimonials",
            "rows": rows,
            "q": q,
            "page": page,
            "pages": pages,
            "size": size,
            "total": total,
            "flashes": await flash_popall(request.session),
        }
        await add_common(ctx, db, current_user, request=request)
        return await render("admin/testimonials/index.html", ctx)
    except Exception as e:
        logger.error(f"Error listing testimonials: {e}")
        raise HTTPException(status_code=500, detail="Error fetching testimonials")

# Create testimonial
@router.get("/new", dependencies=[Depends(require_create)])
async def new_testimonial_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)
    # Fetch projects from the database
    projects = await list_projects(db)
    ctx: Dict[str, Any] = {
        "request": request,
        "title": "Create Testimonial",
        "mode": "create",
        "form": {
            "name": "",
            "role": "",
            "project_id": "",
            "project_title": "",
            "quote": "",
            "video_url": "",
            "sort_order": 0,
            "published": "Yes",  # Default to 'Yes'
        },
        "projects": projects,  # Pass the list of projects to the template
        "flashes": await flash_popall(request.session),
    }
    await add_common(ctx, db, current_user, request=request)
    return await render("admin/testimonials/form.html", ctx)

# Create testimonial action
@router.post("/new", dependencies=[Depends(require_create), Depends(csrf_mod.csrf_protect)])
async def create_testimonial_action(
    request: Request,
    name: str = Form(...),
    role: Optional[str] = Form(None),
    project_id: int = Form(...),
    quote: str = Form(...),
    video_url: Optional[str] = Form(None),
    sort_order: int = Form(...),
    published: bool = Form(...),  # Expecting a bool value
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    # Get the project title using the project_id
    project_title = await get_project_title_by_id(db, project_id)
    # Convert bool to 'Yes'/'No' before passing to model
    published_str = 'Yes' if published else 'No'
    
    # Prepare the payload
    payload = TestimonialCreate(
        name=name,
        role=role,
        project_id=project_id,
        project_title=project_title,
        quote=quote,
        video_url=video_url,
        sort_order=sort_order,
        published=published_str,  # Use 'Yes'/'No' string
    )

    # Get the login_id of the current user for tracking who created the testimonial
    created_by = cast(str, getattr(current_user, "login_id", "System")) or "System"
    
    try:
        # Create the testimonial
        await create_testimonial(db, payload, created_by=created_by)
        return await redirect_with_flash(
            request.session, "/admin/testimonials", "success", f"Testimonial created"
        )
    except IntegrityError as e:
        logger.error(f"Integrity error creating testimonial: {e}")
        # Fetch projects from the database
        project=await list_projects(db)
        ctx: Dict[str, Any] = {
            "request": request,
            "title": "Create Testimonial",
            "projects": project,
            "mode": "create",
            "form": payload.model_dump(),
            "error": f"Error creating testimonial: {e}",
            "flashes": await flash_popall(request.session),
        }
        await add_common(ctx, db, current_user, request=request)
        return await render("admin/testimonials/form.html", ctx)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        project=await list_projects(db)
        ctx: Dict[str, Any] = {
            "request": request,
            "title": "Create Testimonial",
            "projects": project,
            "mode": "create",
            "form": payload.model_dump(),
            "error": f"Unexpected error: {e}",
            "flashes": await flash_popall(request.session),
        }
        await add_common(ctx, db, current_user, request=request)
        return await render("admin/testimonials/form.html", ctx)

# Edit testimonial page
@router.get("/{testimonial_id}/edit", dependencies=[Depends(require_edit)])
async def edit_testimonial_page(
    request: Request,
    testimonial_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)
    # Fetch projects from the database
    projects = await list_projects(db)
    testimonial = await get_testimonial(db, testimonial_id)
    if not testimonial:
        raise HTTPException(status_code=404, detail="Testimonial not found")

    ctx: Dict[str, Any] = {
        "request": request,
        "title": f"Edit Testimonial — {testimonial_id}",
        "mode": "edit",
        "form": {
            "id": testimonial.id,
            "name": testimonial.name,
            "role": testimonial.role,
            "project_id": testimonial.project_id,
            "project_title": testimonial.project_title,
            "quote": testimonial.quote,
            "video_url": testimonial.video_url,
            "sort_order": testimonial.sort_order,
            "published": testimonial.published,
        },
        "projects": projects,  # Pass the list of projects to the template
        "flashes": await flash_popall(request.session),
    }

    await add_common(ctx, db, current_user, request=request)
    return await render("admin/testimonials/form.html", ctx)

# Update testimonial action
@router.post("/{testimonial_id}/edit", dependencies=[Depends(require_edit), Depends(csrf_mod.csrf_protect)])
async def update_testimonial_action(
    request: Request,
    testimonial_id: int,
    name: str = Form(...),
    role: Optional[str] = Form(None),
    project_id: int = Form(...),
    quote: str = Form(...),
    video_url: Optional[str] = Form(None),
    sort_order: Optional[int] = Form(None),
    published: Optional[bool] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    # Get the project title using the project_id
    project_title = await get_project_title_by_id(db, project_id)
    # Convert bool to 'Yes'/'No' for published
    published_str = 'Yes' if published else 'No' if published is not None else None
    
    testimonial_update = TestimonialUpdate(
        name=name,
        role=role,
        project_id=project_id,
        project_title=project_title,
        quote=quote,
        video_url=video_url,
        sort_order=sort_order,
        published=published_str,  # Use 'Yes'/'No' string
    )

    # Get the login_id of the current user for tracking who updated the testimonial
    updated_by = cast(str, getattr(current_user, "login_id", "System")) or "System"

    try:
        updated_testimonial = await update_testimonial(db, testimonial_id, testimonial_update, updated_by=updated_by)
    except Exception as e:
        # Capture the error and send it back to the user for debugging purposes
        logger.error(f"Error updating testimonial {testimonial_id}: {e}")
        return {"error": str(e)}

    if not updated_testimonial:
        raise HTTPException(status_code=404, detail="Testimonial not found")

    return await redirect_with_flash(request.session, "/admin/testimonials", "success", f"Testimonial updated")

# Delete testimonial action
@router.post("/{testimonial_id}/delete", dependencies=[Depends(require_delete), Depends(csrf_mod.csrf_protect)])
async def delete_testimonial_action(
    request: Request,
    testimonial_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_admin(current_user)

    deleted = await delete_testimonial(db, testimonial_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Testimonial not found")

    return await redirect_with_flash(request.session, "/admin/testimonials", "success", "Testimonial deleted")