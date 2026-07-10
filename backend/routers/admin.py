"""Secret-protected data export/import for migrating between environments
(e.g. local dev -> a freshly deployed Coolify instance) via a JSON blob,
since the production database is intentionally not reachable directly.
"""
import base64
import os
import secrets
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from database import models, get_db
from utils.place_image_upload import PLACE_IMAGES_DIR, ensure_place_images_dir

router = APIRouter()

# Parent tables before the children that reference them (import insert order).
# Wipe uses TRUNCATE ... CASCADE so it doesn't need to respect this order.
_EXPORT_MODELS = [
    ("users", models.User),
    ("airlines", models.Airline),
    ("airports", models.Airport),
    ("direct_routes", models.DirectRoute),
    ("planned_trips", models.PlannedTrip),
    ("visited_places", models.VisitedPlace),
    ("planned_trip_stops", models.PlannedTripStop),
    ("images", models.Image),
    ("trip_share_links", models.TripShareLink),
    ("trip_share_invitations", models.TripShareInvitation),
]

# Tables with a plain integer "id" primary key whose sequence needs resetting
# after importing explicit id values. Airlines/airports use a natural (iata)
# primary key and have no sequence to reset.
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


@router.get("/admin/export")
def admin_export(db: Session = Depends(get_db), _: None = Depends(require_admin)):
    data: dict[str, Any] = {"version": 1}
    for table_name, model in _EXPORT_MODELS:
        rows = db.query(model).all()
        data[table_name] = [_row_to_dict(row) for row in rows]

    ensure_place_images_dir()
    image_files: dict[str, str] = {}
    for image_row in data["images"]:
        filename = os.path.basename(image_row.get("image_path") or "")
        if not filename:
            continue
        file_path = PLACE_IMAGES_DIR / filename
        if file_path.is_file():
            image_files[filename] = base64.b64encode(file_path.read_bytes()).decode("ascii")
    data["image_files"] = image_files

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
        image_files: dict[str, str] = payload.get("image_files") or {}
        for filename, b64content in image_files.items():
            safe_name = os.path.basename(filename)
            if not safe_name:
                continue
            (PLACE_IMAGES_DIR / safe_name).write_bytes(base64.b64decode(b64content))

        db.commit()
        return {"success": True, "counts": counts}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Import failed: {exc}") from exc
