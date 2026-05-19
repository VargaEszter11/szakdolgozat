"""Direct destinations loaded from the local route cache."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import logging
from sqlalchemy.orm import Session

from database import crud

logger = logging.getLogger("planner.routes")


async def get_direct_destinations_cached(
    db: Optional[Session],
    origin_airport_code: str,
) -> List[Dict[str, Any]]:
    """Return active direct destinations from ``direct_routes`` / ``airports``."""
    code = (origin_airport_code or "").strip().upper()
    if not code or db is None:
        return []

    try:
        destinations = crud.list_active_destinations_from_origin(db, code)
        logger.info("Loaded %d local direct destinations from %s", len(destinations), code)
        return destinations
    except Exception:
        logger.exception("Failed to load local direct destinations from %s", code)
        return []
