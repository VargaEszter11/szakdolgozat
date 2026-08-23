import base64
import os
import secrets
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional, cast

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from database import models, schemas, get_db, crud
from utils.place_image_upload import PLACE_IMAGES_DIR, ensure_place_images_dir
from utils.feedback_image_upload import FEEDBACK_IMAGES_DIR, ensure_feedback_images_dir

router = APIRouter()

_EXPORT_MODELS = [
    ("users", models.User),
    ("password_reset_tokens", models.PasswordResetToken),
    ("airlines", models.Airline),
    ("airports", models.Airport),
    ("direct_routes", models.DirectRoute),
    ("planned_trips", models.PlannedTrip),
    ("visited_places", models.VisitedPlace),
    ("planned_trip_stops", models.PlannedTripStop),
    ("images", models.Image),
    ("trip_share_links", models.TripShareLink),
    ("trip_share_invitations", models.TripShareInvitation),
    ("feedbacks", models.Feedback),
]

_SEQUENCE_TABLES = [
    name for name, model in _EXPORT_MODELS if name not in ("airlines", "airports")
]


def require_admin(x_admin_secret: str = Header(default="")) -> None:
    configured = os.getenv("ADMIN_SECRET", "").strip()
    if not configured:
        raise HTTPException(status_code=503, detail="Admin access is not configured on the server.")
    if not secrets.compare_digest(x_admin_secret.strip(), configured):
        raise HTTPException(status_code=401, detail="Invalid admin secret.")


@router.get("/admin/ping")
def admin_ping(_: None = Depends(require_admin)):
    return {"ok": True}


def _json_safe(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _row_to_dict(row: Any) -> dict:
    mapper = inspect(row).mapper
    return {attr.key: _json_safe(getattr(row, attr.key)) for attr in mapper.column_attrs}


def _collect_uploaded_files(rows: list[dict], path_key: str, images_dir: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in rows:
        filename = os.path.basename(row.get(path_key) or "")
        if not filename or filename in out:
            continue
        file_path = images_dir / filename
        if file_path.is_file():
            out[filename] = base64.b64encode(file_path.read_bytes()).decode("ascii")
    return out


def _write_uploaded_files(image_files: dict[str, str], images_dir: Path) -> None:
    images_dir.mkdir(parents=True, exist_ok=True)
    for filename, b64content in image_files.items():
        safe_name = os.path.basename(filename)
        if not safe_name:
            continue
        (images_dir / safe_name).write_bytes(base64.b64decode(b64content))


@router.get("/admin/export")
def admin_export(db: Session = Depends(get_db), _: None = Depends(require_admin)):
    data: dict[str, Any] = {"version": 1}
    for table_name, model in _EXPORT_MODELS:
        rows = db.query(model).all()
        data[table_name] = [_row_to_dict(row) for row in rows]

    ensure_place_images_dir()
    ensure_feedback_images_dir()
    data["image_files"] = _collect_uploaded_files(
        data.get("images") or [], "image_path", PLACE_IMAGES_DIR
    )
    data["feedback_image_files"] = _collect_uploaded_files(
        data.get("feedbacks") or [], "image_path", FEEDBACK_IMAGES_DIR
    )

    return data


def _parse_value(model: Any, key: str, value: Any) -> Any:
    if value is None:
        return None
    try:
        column = inspect(model).columns[key]
    except KeyError:
        return value

    type_name = type(column.type).__name__
    if type_name == "Date" and isinstance(value, str):
        return date.fromisoformat(value)
    if type_name == "DateTime" and isinstance(value, str):
        return datetime.fromisoformat(value)
    if type_name == "Numeric" and isinstance(value, (int, float, str)):
        return Decimal(str(value))
    return value


@router.post("/admin/import")
def admin_import(
    payload: dict,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    if not isinstance(payload, dict) or "version" not in payload:
        raise HTTPException(status_code=400, detail="Invalid export file.")

    try:
        for table_name, _model in _EXPORT_MODELS:
            db.execute(text(f'TRUNCATE TABLE "{table_name}" RESTART IDENTITY CASCADE'))

        counts: dict[str, int] = {}
        for table_name, model in _EXPORT_MODELS:
            rows = payload.get(table_name) or []
            for row_data in rows:
                clean = {k: _parse_value(model, k, v) for k, v in row_data.items()}
                db.add(model(**clean))
            db.flush()
            counts[table_name] = len(rows)

        for table_name in _SEQUENCE_TABLES:
            db.execute(
                text(
                    f"""
                    DO $$
                    DECLARE seq_name text;
                    BEGIN
                        seq_name := pg_get_serial_sequence('"{table_name}"', 'id');
                        IF seq_name IS NOT NULL THEN
                            PERFORM setval(seq_name, COALESCE((SELECT MAX(id) FROM "{table_name}"), 1));
                        END IF;
                    END $$;
                    """
                )
            )

        ensure_place_images_dir()
        ensure_feedback_images_dir()
        _write_uploaded_files(payload.get("image_files") or {}, PLACE_IMAGES_DIR)
        _write_uploaded_files(payload.get("feedback_image_files") or {}, FEEDBACK_IMAGES_DIR)

        db.commit()
        return {"success": True, "counts": counts}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Import failed: {exc}") from exc


@router.get("/admin/feedback", response_model=list[schemas.FeedbackResponse])
def admin_list_feedback(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    rows = crud.list_feedbacks(db)
    out: list[schemas.FeedbackResponse] = []
    for raw_row in rows:
        row = cast(Any, raw_row)
        user = cast(Any, crud.get_user(db, int(row.user_id)))
        out.append(
            schemas.FeedbackResponse(
                id=int(row.id),
                user_id=int(row.user_id),
                username=str(user.username) if user else f"user#{row.user_id}",
                email=str(user.email) if user and user.email else None,
                message=str(row.message),
                image_path=row.image_path,
                created_at=row.created_at,
            )
        )
    return out


@router.delete("/admin/feedback/{feedback_id}")
def admin_delete_feedback(
    feedback_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    ok = crud.delete_feedback(db, feedback_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Feedback not found.")
    return {"success": True}
