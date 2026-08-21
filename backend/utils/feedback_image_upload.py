"""Save uploaded feedback photos under `uploads/feedback_images`."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent
FEEDBACK_IMAGES_DIR = PROJECT_ROOT / "uploads" / "feedback_images"

ALLOWED_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/jpg": ".jpg"}
MAX_FILE_BYTES = 10 * 1024 * 1024


def ensure_feedback_images_dir() -> None:
    FEEDBACK_IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def save_feedback_image(content: bytes, content_type: str | None) -> str:
    raw = (content_type or "").split(";")[0].strip().lower()
    ext = ALLOWED_TYPES.get(raw)
    if not ext:
        raise ValueError("Unsupported image type; use JPEG or PNG.")
    if len(content) > MAX_FILE_BYTES:
        raise ValueError("File too large (max 10MB).")

    ensure_feedback_images_dir()
    name = f"{uuid.uuid4().hex}{ext}"
    (FEEDBACK_IMAGES_DIR / name).write_bytes(content)
    return f"/uploads/feedback_images/{name}"


def delete_feedback_image(public_path: str | None) -> None:
    if not public_path or not public_path.startswith("/uploads/feedback_images/"):
        return
    safe_name = os.path.basename(public_path)
    if not safe_name:
        return
    path = (FEEDBACK_IMAGES_DIR / safe_name).resolve()
    root = FEEDBACK_IMAGES_DIR.resolve()
    if root != path.parent or not path.is_file():
        return
    path.unlink()
