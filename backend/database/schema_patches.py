"""Runtime DDL fixes for existing PostgreSQL databases (idempotent)."""

import logging

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from database.database import engine

logger = logging.getLogger(__name__)


def apply_startup_schema_patches() -> None:
    """
    Older DBs had UNIQUE(visited_place_id) on `images`, allowing only one photo per place.
    Drop that constraint so multiple gallery rows per visited place are allowed.
    """
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE images DROP CONSTRAINT IF EXISTS images_visited_place_id_key"
                )
            )
    except SQLAlchemyError as exc:
        logger.warning("Could not apply images multi-photo schema patch: %s", exc)
