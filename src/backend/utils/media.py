# src/backend/utils/media.py

import os
import logging
from pathlib import Path
from fastapi import UploadFile, HTTPException

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# GLOBAL MEDIA ROOT = deed-media
# -------------------------------------------------------------------

MEDIA_ROOT = Path(
    os.getenv("MEDIA_ROOT", r"E:/Data Science/Agentic AI/deed-media")
).resolve()

MEDIA_URL = "/deed-media"  # Public URL prefix


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def get_media_root() -> Path:
    """
    Ensure the root directory exists and return it.
    """
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    return MEDIA_ROOT


def normalize_subdir(subdir: str) -> str:
    """
    Clean input directory (strip slashes).
    """
    return subdir.strip().strip("/")


def ensure_subdir(subdir: str) -> Path:
    """
    Ensure subdirectory exists inside MEDIA_ROOT.
    """
    folder = get_media_root() / normalize_subdir(subdir)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


# ---------------------------------------------------------
#    SAVE FILE USING RULE: subdir + id + ext
# ---------------------------------------------------------
def save_media_with_id(
    subdir: str,
    upload: UploadFile,
    *,
    record_id: int,
    allowed_types: set[str] = {"image/jpeg", "image/png", "image/jpg"},
    max_size_mb: int = 5,
) -> str:
    """
    Save media using naming rule:
        subdirName + ID + ext
        Example:
            subdir="images/awards"
            -> images_awards1.jpg

    Returns PUBLIC URL:
        /deed-media/images/awards/images_awards1.jpg
    """

    if upload is None or upload.filename is None:
        raise HTTPException(status_code=400, detail="No file uploaded")

    # Validate MIME type
    if not upload.content_type or upload.content_type.lower() not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type")

    # Read file (bytes)
    data: bytes = upload.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    # Validate file size
    if len(data) / (1024 * 1024) > max_size_mb:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds max size {max_size_mb} MB"
        )

    # Prepare folder
    subdir_clean = normalize_subdir(subdir)
    folder: Path = ensure_subdir(subdir_clean)

    # ---- SAFELY EXTRACT EXT ----
    original_name: str = upload.filename or "file"
    ext = os.path.splitext(original_name)[1].lower()

    if ext == ".jpeg":
        ext = ".jpg"
    if ext not in [".jpg", ".png"]:
        ext = ".jpg"

    # FINAL FILE NAME RULE
    # replace "/" to "_" to avoid illegal filenames
    safe_name_prefix = subdir_clean.replace("/", "_")

    filename = f"{safe_name_prefix}{record_id}{ext}"

    # FULL PATH
    file_path: Path = folder / filename

    # SAVE FILE
    try:
        file_path.write_bytes(data)
    except Exception as e:
        logger.exception(f"Failed to write media file {file_path}: {e}")
        raise HTTPException(status_code=500, detail="Could not save the file")

    logger.info(f"Saved media file: {file_path}")

    # RETURN PUBLIC URL
    return f"{MEDIA_URL}/{subdir_clean}/{filename}"

# ---------------------------------------------------------
#    DELETE MEDIA FILE
# ---------------------------------------------------------
            
def delete_media_file(url: str):
    """
    Delete media files.
    Example URL: /deed-media/images/awards/awards1.jpg
    """
    if not url or not url.startswith(MEDIA_URL):
        raise HTTPException(status_code=400, detail="Invalid media URL")

    # Remove the base URL part and then convert to file system path
    rel_path = url[len(MEDIA_URL):].lstrip("/")
    full_path = get_media_root() / rel_path.replace("/", os.sep)

    if full_path.exists():
        try:
            full_path.unlink()  # Remove the file
            logger.info(f"Deleted media file: {full_path}")
        except Exception as e:
            logger.error(f"Error deleting media file {full_path}: {e}")
            raise HTTPException(status_code=500, detail="Error deleting media file")
