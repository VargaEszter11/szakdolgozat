"""Cache-first direct destinations: read from DB, fall back to Amadeus and backfill."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from database import crud
from utils.nearest_airport import get_direct_destinations


async def get_direct_destinations_cached(
    db: Optional[Session],
    origin_airport_code: str,
) -> List[Dict[str, Any]]:
    """Return direct destinations like ``get_direct_destinations``.

    If ``db`` is set: try active rows in ``direct_routes`` / ``airports`` first.
    On cache miss or DB error, call Amadeus ``get_direct_destinations`` and
    ``sync_direct_routes_for_origin`` when persistence succeeds.
    If ``db`` is ``None``, only the Amadeus path runs (original behaviour).
    """
    code = (origin_airport_code or "").strip().upper()
    if not code:
        return []

    if db is not None:
        try:
            cached = crud.list_active_destinations_from_origin(db, code)
            if cached:
                return cached
        except Exception:
            pass

    raw = await get_direct_destinations(code)
    if not raw:
        return []

    if db is not None:
        try:
            crud.sync_direct_routes_for_origin(db, code, raw)
        except Exception:
            pass

    return raw
