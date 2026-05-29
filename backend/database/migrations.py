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
            conn.execute(
                text(
                    """
                    ALTER TABLE direct_routes
                    ADD COLUMN IF NOT EXISTS is_seasonal BOOLEAN NULL,
                    ADD COLUMN IF NOT EXISTS effective_from DATE NULL,
                    ADD COLUMN IF NOT EXISTS effective_to DATE NULL
                    """
                )
            )
            conn.execute(
                text(
                    """
                    ALTER TABLE planned_trips
                    ADD COLUMN IF NOT EXISTS people INTEGER DEFAULT 1
                    """
                )
            )
            conn.execute(text("UPDATE planned_trips SET people = 1 WHERE people IS NULL"))
            conn.execute(text("ALTER TABLE planned_trips ALTER COLUMN people SET DEFAULT 1"))
            conn.execute(text("ALTER TABLE planned_trips ALTER COLUMN people SET NOT NULL"))
            conn.execute(
                text(
                    """
                    ALTER TABLE planned_trip_stops
                    ADD COLUMN IF NOT EXISTS booking_url TEXT NULL,
                    ADD COLUMN IF NOT EXISTS flight_availability_verified BOOLEAN NULL
                    """
                )
            )
            conn.execute(
                text(
                    """
                    ALTER TABLE planned_trip_stops
                    DROP COLUMN IF EXISTS origin_airport_iata,
                    DROP COLUMN IF EXISTS destination_airport_iata,
                    DROP COLUMN IF EXISTS airline_iata,
                    DROP COLUMN IF EXISTS airline_name
                    """
                )
            )
            conn.execute(
                text(
                    """
                    DELETE FROM route_days rd
                    USING direct_routes duplicate, direct_routes keep
                    WHERE rd.route_id = duplicate.id
                      AND COALESCE(duplicate.airline_iata, '') = COALESCE(keep.airline_iata, '')
                      AND duplicate.origin_iata = keep.origin_iata
                      AND duplicate.destination_iata = keep.destination_iata
                      AND duplicate.id > keep.id
                    """
                )
            )
            conn.execute(
                text(
                    """
                    DELETE FROM route_prices rp
                    USING direct_routes duplicate, direct_routes keep
                    WHERE rp.route_id = duplicate.id
                      AND COALESCE(duplicate.airline_iata, '') = COALESCE(keep.airline_iata, '')
                      AND duplicate.origin_iata = keep.origin_iata
                      AND duplicate.destination_iata = keep.destination_iata
                      AND duplicate.id > keep.id
                    """
                )
            )
            conn.execute(
                text(
                    """
                    DELETE FROM direct_routes duplicate
                    USING direct_routes keep
                    WHERE COALESCE(duplicate.airline_iata, '') = COALESCE(keep.airline_iata, '')
                      AND duplicate.origin_iata = keep.origin_iata
                      AND duplicate.destination_iata = keep.destination_iata
                      AND duplicate.id > keep.id
                    """
                )
            )
            conn.execute(text("DROP INDEX IF EXISTS uniq_route"))
            conn.execute(text("DROP INDEX IF EXISTS uniq_route_airline_origin_destination"))
            conn.execute(
                text(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS uniq_route
                    ON direct_routes (COALESCE(airline_iata, ''), origin_iata, destination_iata)
                    """
                )
            )
    except SQLAlchemyError as exc:
        logger.warning("Could not apply startup schema patch: %s", exc)
