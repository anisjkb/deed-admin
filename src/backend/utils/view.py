# src/backend/utils/view.py
import os
from typing import Dict, Any
from fastapi.templating import Jinja2Templates
from starlette.responses import Response

from src.backend.config import settings  # <-- add this import

_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.abspath(os.path.join(_current_dir, "../../.."))
_templates_path = os.path.join(_project_root, "frontend", "templates")
templates = Jinja2Templates(directory=_templates_path)

# Ensure the version is available to ALL templates rendered via this helper
templates.env.globals["static_version"] = settings.STATIC_VERSION

def _no_cache(resp: Response) -> Response:
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp

async def render(template_name: str, ctx: Dict[str, Any]) -> Response:
    # Fallback in case a template references {{ static_version }} directly
    ctx.setdefault("static_version", settings.STATIC_VERSION)
    resp = templates.TemplateResponse(template_name, ctx)
    return _no_cache(resp)