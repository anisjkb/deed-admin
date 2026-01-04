# src/backend/utils/image_media.py

import os
import re
import logging
from pathlib import Path
from typing import FrozenSet
from fastapi import UploadFile, HTTPException

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# GLOBAL MEDIA ROOT
# -------------------------------------------------------------------
IMAGE_MEDIA_ROOT = Path(
    os.getenv("IMAGE_MEDIA_ROOT", r"E:/Data Science/Agentic AI/deed/src/backend/static/images")
).resolve()

IMAGE_MEDIA_URL = "/images"  # Public URL prefix


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def get_media_root() -> Path:
    IMAGE_MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    return IMAGE_MEDIA_ROOT


def normalize_subdir(subdir: str) -> str:
    return (subdir or "").strip().strip("/")


def ensure_subdir(subdir: str) -> Path:
    folder = get_media_root() / normalize_subdir(subdir)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _choose_extension(original_name: str, content_type: str) -> str:
    content_type = (content_type or "").lower()
    _, ext = os.path.splitext((original_name or "file").lower())

    if content_type == "application/pdf":
        return ".pdf"
    if content_type == "image/avif":
        return ".avif"
    if content_type == "image/webp":
        return ".webp"
    if content_type == "image/png":
        return ".png"
    if content_type in {"image/jpeg", "image/jpg"}:
        return ".jpg"

    if ext == ".jpeg":
        return ".jpg"
    if ext in {".avif", ".webp", ".png", ".jpg", ".pdf"}:
        return ext

    return ".jpg"


def _safe_key(s: str) -> str:
    # keep filenames safe on Windows
    s = (s or "").strip()
    s = re.sub(r"[^a-zA-Z0-9_-]+", "_", s)
    return s or "media"


# ---------------------------------------------------------
# SAVE FILE USING RULE: subdir + id + ext   (INT ID)
# ---------------------------------------------------------
def save_media_with_id(
    subdir: str,
    upload: UploadFile,
    *,
    record_id: int,
    allowed_types: FrozenSet[str] = frozenset({
        "image/avif", "image/webp", "image/png", "image/jpeg", "image/jpg",
        "application/pdf",
    }),
    max_size_mb: int = 5,
) -> str:
    if upload is None or upload.filename is None:
        raise HTTPException(status_code=400, detail="No file uploaded")

    content_type = (upload.content_type or "").lower()
    if content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type")

    data: bytes = upload.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    if len(data) / (1024 * 1024) > max_size_mb:
        raise HTTPException(status_code=400, detail=f"File exceeds max size {max_size_mb} MB")

    subdir_clean = normalize_subdir(subdir)
    folder: Path = ensure_subdir(subdir_clean)

    ext = _choose_extension(upload.filename or "file", content_type)

    safe_name_prefix = subdir_clean.replace("/", "_") or "media"
    filename = f"{safe_name_prefix}{record_id}{ext}"
    file_path: Path = folder / filename

    try:
        file_path.write_bytes(data)
    except Exception as e:
        logger.exception(f"Failed to write media file {file_path}: {e}")
        raise HTTPException(status_code=500, detail="Could not save the file")

    logger.info(f"Saved media file: {file_path}")
    return f"{IMAGE_MEDIA_URL}/{subdir_clean}/{filename}"


# ---------------------------------------------------------
# SAVE FILE USING RULE: subdir + key + ext  (STRING KEY)
# ---------------------------------------------------------
def save_media_with_key(
    subdir: str,
    upload: UploadFile,
    *,
    record_key: str,
    allowed_types: FrozenSet[str] = frozenset({
        "image/avif", "image/webp", "image/png", "image/jpeg", "image/jpg",
    }),
    max_size_mb: int = 5,
) -> str:
    """
    Example:
      subdir="team", record_key="000123" -> team_000123.avif
    """
    if upload is None or upload.filename is None:
        raise HTTPException(status_code=400, detail="No file uploaded")

    content_type = (upload.content_type or "").lower()
    if content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type")

    data: bytes = upload.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    if len(data) / (1024 * 1024) > max_size_mb:
        raise HTTPException(status_code=400, detail=f"File exceeds max size {max_size_mb} MB")

    subdir_clean = normalize_subdir(subdir)
    folder: Path = ensure_subdir(subdir_clean)

    ext = _choose_extension(upload.filename or "file", content_type)

    safe_name_prefix = subdir_clean.replace("/", "_") or "media"
    safe_key = (record_key or "").strip().replace("/", "_")
    filename = f"{safe_name_prefix}{safe_key}{ext}"

    file_path: Path = folder / filename

    try:
        file_path.write_bytes(data)
    except Exception as e:
        logger.exception(f"Failed to write media file {file_path}: {e}")
        raise HTTPException(status_code=500, detail="Could not save the file")

    logger.info(f"Saved media file: {file_path}")
    return f"{IMAGE_MEDIA_URL}/{subdir_clean}/{filename}"

# ---------------------------------------------------------
# DELETE MEDIA FILE
# ---------------------------------------------------------
def delete_media_file(url: str):
    if not url or not url.startswith(IMAGE_MEDIA_URL):
        raise HTTPException(status_code=400, detail="Invalid media URL")

    url_no_qs = url.split("?", 1)[0]
    rel_path = url_no_qs[len(IMAGE_MEDIA_URL):].lstrip("/")
    full_path = get_media_root() / rel_path.replace("/", os.sep)

    if full_path.exists():
        try:
            full_path.unlink()
            logger.info(f"Deleted media file: {full_path}")
        except Exception as e:
            logger.error(f"Error deleting media file {full_path}: {e}")
            raise HTTPException(status_code=500, detail="Error deleting media file")
    else:
        logger.warning(f"Delete requested but file not found: {full_path}")