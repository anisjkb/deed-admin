# src/backend/app.py
import os
import secrets
import mimetypes

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException as FastAPIHTTPException

from starlette.middleware.sessions import SessionMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.backend.config import settings
from src.backend.utils.error_handler import custom_exception_handler
from src.backend.utils.csrf import ensure_csrf_cookie

from src.backend.routes.pages_router import router as pages_router
from src.backend.routes.auth_api import auth_api
from src.backend.routes.role_admin_pages import router as role_admin_router
from src.backend.routes.menu_admin_pages import router as menu_admin_router
from src.backend.routes.rights import router as rights_router
from src.backend.routes.group_admin_pages import router as groups_router
from src.backend.routes.org_admin_pages import router as orgs_router
from src.backend.routes.zone_admin_pages import router as zones_router
from src.backend.routes.branch_admin_pages import router as branches_router
from src.backend.routes.desig_admin_pages import router as desigs_router
from src.backend.routes.admin_employees_pages import router as employees_router
from src.backend.routes import admin_users_pages, users_api
from src.backend.routes.my_profile_page_router import router as profile_router
from src.backend.routes.project_admin_pages import router as projects_router
from src.backend.routes.routes_award_pages import router as awards_router
from src.backend.routes.routes_banner_pages import router as banners_router
from src.backend.routes.routes_testimonials import router as testimonials_router
from src.backend.routes.routers_image_editor import router as image_editor_router
from src.backend.routes.routes_feedback_pages import router as feedbacks_router

# ─────────────────────────────────────────────────────────
# Ensure modern image types return correct Content-Type
# ─────────────────────────────────────────────────────────
mimetypes.add_type("image/avif", ".avif")
mimetypes.add_type("image/webp", ".webp")

app = FastAPI(title="deed-admin", version="1.0")

# ----------------------------------------------------------
# ABSOLUTE PATHS
# ----------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))            # src/backend
project_root = os.path.abspath(os.path.join(current_dir, "../../")) # repo root
frontend_static_path = os.path.join(project_root, "frontend", "static")
frontend_template_path = os.path.join(project_root, "frontend", "templates")

# ----------------------------------------------------------
# GLOBAL MEDIA ROOT - always used by deed-web + deed-admin
# ----------------------------------------------------------
IMAGE_MEDIA_URL = "/images"  # Public URL prefix
IMAGE_MEDIA_ROOT = r"E:/Data Science/Agentic AI/deed/src/backend/static/images"
os.makedirs(IMAGE_MEDIA_ROOT, exist_ok=True)

# Make MEDIA_ROOT available to media.py
os.environ["IMAGE_MEDIA_ROOT"] = IMAGE_MEDIA_ROOT

# ----------------------------------------------------------
# VERIFY PATHS
# ----------------------------------------------------------
if not os.path.exists(frontend_static_path):
    raise RuntimeError(f"Static folder not found: {frontend_static_path}")
if not os.path.exists(frontend_template_path):
    raise RuntimeError(f"Templates folder not found: {frontend_template_path}")

# ----------------------------------------------------------
# STATIC FILES
# ----------------------------------------------------------
# Admin static (CSS/JS)
app.mount("/static", StaticFiles(directory=frontend_static_path), name="static")

# Global media system (shared between deed-web & deed-admin)
app.mount(IMAGE_MEDIA_URL, StaticFiles(directory=IMAGE_MEDIA_ROOT), name="images")

# ----------------------------------------------------------
# Jinja Templates
# ----------------------------------------------------------
templates = Jinja2Templates(directory=frontend_template_path)
templates.env.globals["static_version"] = settings.STATIC_VERSION

# ----------------------------------------------------------
# SESSION
# ----------------------------------------------------------
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET,
    same_site=(
        settings.SESSION_SAMESITE
        if settings.SESSION_SAMESITE in ("lax", "strict", "none")
        else "lax"
    ),
    https_only=settings.SESSION_HTTPS_ONLY,  # True in prod (requires HTTPS)
)

# ----------------------------------------------------------
# CSP & SECURITY HEADERS
# ----------------------------------------------------------
@app.middleware("http")
async def csp_nonce_and_headers(request: Request, call_next):
    nonce = secrets.token_urlsafe(16)
    request.state.csp_nonce = nonce

    response = await call_next(request)

    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        f"script-src 'self' 'nonce-{nonce}'; "
        "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
        "img-src 'self' data: blob:; "
        "font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
        "connect-src 'self'; "
        "frame-src 'self' blob:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "object-src 'self' blob:;"
    )
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")

    return response

# ----------------------------------------------------------
# GLOBAL XSRF TOKEN SEEDING
# ----------------------------------------------------------
@app.middleware("http")
async def seed_xsrf_cookie(request: Request, call_next):
    resp = await call_next(request)
    if request.method == "GET" and "text/html" in (resp.headers.get("content-type") or ""):
        ensure_csrf_cookie(resp, request)
    return resp

# ----------------------------------------------------------
# CUSTOM ERROR HANDLERS (clean coverage)
# ----------------------------------------------------------
# 1) Starlette HTTPException (routing 404 etc.)
app.add_exception_handler(StarletteHTTPException, custom_exception_handler)

# 2) FastAPI HTTPException (ones you raise yourself)
app.add_exception_handler(FastAPIHTTPException, custom_exception_handler)

# 3) Validation errors
app.add_exception_handler(RequestValidationError, custom_exception_handler)

# 4) Catch-all (recommended)
app.add_exception_handler(Exception, custom_exception_handler)

# ----------------------------------------------------------
# ROUTERS
# ----------------------------------------------------------
app.include_router(pages_router)
app.include_router(auth_api, prefix="/auth")
app.include_router(role_admin_router)
app.include_router(menu_admin_router)
app.include_router(rights_router)
app.include_router(groups_router)
app.include_router(orgs_router)
app.include_router(zones_router)
app.include_router(branches_router)
app.include_router(desigs_router)
app.include_router(employees_router)
app.include_router(admin_users_pages.router)
app.include_router(users_api.router)
app.include_router(profile_router)
app.include_router(projects_router)
app.include_router(awards_router)
app.include_router(banners_router)
app.include_router(testimonials_router)
app.include_router(image_editor_router)
app.include_router(feedbacks_router)
# ----------------------------------------------------------
# FAVICON & MANIFEST
# ----------------------------------------------------------
@app.get("/favicon.ico", include_in_schema=False)
async def favicon_ico():
    return FileResponse(os.path.join(frontend_static_path, "favicon", "favicon.ico"))

@app.get("/site.webmanifest", include_in_schema=False)
async def webmanifest():
    return FileResponse(os.path.join(frontend_static_path, "site.webmanifest"))