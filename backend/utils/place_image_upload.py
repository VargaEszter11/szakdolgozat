"""Save uploaded visit photos under the project `uploads/place_images` folder."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent
PLACE_IMAGES_DIR = PROJECT_ROOT / "uploads" / "place_images"

ALLOWED_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/jpg": ".jpg"}
MAX_FILE_BYTES = 10 * 1024 * 1024


def ensure_place_images_dir() -> None:
    PLACE_IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def public_url_path(filename: str) -> str:
    return f"/uploads/place_images/{filename}"


def save_place_image(content: bytes, content_type: str | None) -> str:
    """
    Write bytes to disk and return the public URL path stored in the database
    (e.g. /uploads/place_images/<uuid>.jpg).
    """
    raw = (content_type or "").split(";")[0].strip().lower()
    ext = ALLOWED_TYPES.get(raw)
    if not ext:
        raise ValueError("Unsupported image type; use JPEG or PNG.")
    if len(content) > MAX_FILE_BYTES:
        raise ValueError("File too large (max 10MB).")

    ensure_place_images_dir()
    name = f"{uuid.uuid4().hex}{ext}"
    dest = PLACE_IMAGES_DIR / name
    dest.write_bytes(content)
    return public_url_path(name)


def delete_file_for_public_path(public_path: str | None) -> None:
    """Remove a file if public_path points to uploads/place_images under this project."""
    if not public_path or not public_path.startswith("/uploads/place_images/"):
        return
    safe_name = os.path.basename(public_path)
    if not safe_name or safe_name != public_path.rsplit("/", 1)[-1]:
        return
    path = (PLACE_IMAGES_DIR / safe_name).resolve()
    root = PLACE_IMAGES_DIR.resolve()
    if root != path.parent or not path.is_file():
        return
    path.unlink()
