# src/backend/routes/profile.py
from __future__ import annotations

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.utils.database import get_db
from src.backend.utils.auth import get_current_user
from src.backend.utils.view import render
from src.backend.utils.flash import flash_popall
from src.backend.utils.common_context import add_common

from src.backend.models.user import User as UserModel
# adjust these imports to match your actual model paths
from src.backend.models.org.emp_info import EmpInfo
from src.backend.models.org.group_info import GroupInfo
from src.backend.models.org.org_info import OrgInfo
from src.backend.models.org.zone_info import ZoneInfo
from src.backend.models.org.br_info import BranchInfo
from src.backend.models.security.role import Role as RoleInfo  # adjust path if you keep roles elsewhere
from src.backend.models.org.desig_info import DesigInfo  # same for designation table


router = APIRouter(prefix="/profile", tags=["Profile"])

@router.get("")
async def my_profile(
    request: Request,
    current_user: UserModel = Depends(get_current_user),   # <-- login required
    db: AsyncSession = Depends(get_db),
):
    # Load employee row (optional, if your user may not have emp_id)
    emp: Optional[EmpInfo] = None
    if getattr(current_user, "emp_id", None):
        emp = await db.scalar(select(EmpInfo).where(EmpInfo.emp_id == current_user.emp_id))

    # Resolve org chain
    group = org = zone = branch = None
    if emp and emp.group_id:
        group = await db.scalar(select(GroupInfo).where(GroupInfo.group_id == emp.group_id))
    if emp and emp.org_id:
        org = await db.scalar(select(OrgInfo).where(OrgInfo.org_id == emp.org_id))
    if emp and emp.zone_id:
        zone = await db.scalar(select(ZoneInfo).where(ZoneInfo.zone_id == emp.zone_id))
    if emp and emp.br_id:
        branch = await db.scalar(select(BranchInfo).where(BranchInfo.br_id == emp.br_id))

    role = None
    desig = None

    # ---- role ----
    if getattr(current_user, "role_id", None):
        result = await db.execute(select(RoleInfo).where(RoleInfo.role_id == current_user.role_id))
        role = result.scalar_one_or_none()

    # ---- designation ----
    if emp and getattr(emp, "desig_id", None):
        result = await db.execute(select(DesigInfo).where(DesigInfo.desig_id == emp.desig_id))
        desig = result.scalar_one_or_none()
    
    ctx: Dict[str, Any] = {
        "request": request,
        "title": "My Profile",
        "user": current_user,   # <-- so template can use {{ user }} (and it will fallback to current_user anyway)
        "emp": emp,
        "group": group,
        "org": org,
        "zone": zone,
        "branch": branch,
        "role": role,           # optional nice-to-have (role name)
        "desig": desig,         # optional nice-to-have (designation name)
        "flashes": await flash_popall(request.session),
    }
    # This will still build the sidebar based on whatever admin rights the user has.
    # If they have none, sidebar simply shows nothing special, which is fine.
    await add_common(ctx, db, current_user)
    return await render("admin/profile/index.html", ctx)
