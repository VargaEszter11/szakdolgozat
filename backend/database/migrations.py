"""Runtime DDL fixes for existing PostgreSQL databases (idempotent)."""

import logging

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from database.airport_city import CITY_OVERRIDES_BY_IATA, airport_name_as_city
from database.airport_regions import EUROPE_COUNTRY_CODES
from database.database import engine

logger = logging.getLogger(__name__)

EUROPE_COUNTRY_SQL = ", ".join(f"'{code}'" for code in sorted(EUROPE_COUNTRY_CODES))


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
                    ALTER TABLE users
                    DROP COLUMN IF EXISTS profile_picture_url,
                    DROP COLUMN IF EXISTS use_travel_log_in_planner
                    """
                )
            )
            conn.execute(
                text(
                    """
                    ALTER TABLE users
                    ADD COLUMN IF NOT EXISTS home_city TEXT NULL
                    """
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
            conn.execute(text("DROP TABLE IF EXISTS route_days"))
            conn.execute(text("DROP TABLE IF EXISTS route_prices"))
            conn.execute(text("DROP TABLE IF EXISTS route_refresh_runs"))
            conn.execute(
                text(
                    """
                    ALTER TABLE planned_trips
                    ADD COLUMN IF NOT EXISTS people INTEGER DEFAULT 1,
                    ADD COLUMN IF NOT EXISTS is_booked BOOLEAN DEFAULT FALSE
                    """
                )
            )
            conn.execute(text("UPDATE planned_trips SET people = 1 WHERE people IS NULL"))
            conn.execute(text("ALTER TABLE planned_trips ALTER COLUMN people SET DEFAULT 1"))
            conn.execute(text("ALTER TABLE planned_trips ALTER COLUMN people SET NOT NULL"))
            conn.execute(text("UPDATE planned_trips SET is_booked = FALSE WHERE is_booked IS NULL"))
            conn.execute(text("ALTER TABLE planned_trips ALTER COLUMN is_booked SET DEFAULT FALSE"))
            conn.execute(text("ALTER TABLE planned_trips ALTER COLUMN is_booked SET NOT NULL"))
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

            airport_rows = conn.execute(
                text(
                    """
                    SELECT iata, name
                    FROM airports
                    WHERE city IS NULL OR btrim(city) = '' OR city = iata
                    """
                )
            ).mappings()
            for airport in airport_rows:
                city = airport_name_as_city(airport["name"], airport["iata"])
                if city:
                    conn.execute(
                        text(
                            """
                            UPDATE airports
                            SET city = :city,
                                updated_at = NOW()
                            WHERE iata = :iata
                              AND (city IS NULL OR btrim(city) = '' OR city = iata)
                            """
                        ),
                        {"city": city, "iata": airport["iata"]},
                    )

            for iata, city in CITY_OVERRIDES_BY_IATA.items():
                conn.execute(
                    text(
                        """
                        UPDATE airports
                        SET city = :city,
                            updated_at = NOW()
                        WHERE iata = :iata
                          AND city IS DISTINCT FROM :city
                        """
                    ),
                    {"city": city, "iata": iata},
                )

            def non_europe_airport_condition(alias: str) -> str:
                return (
                    f"{alias}.country_code IS NULL "
                    f"OR upper({alias}.country_code) NOT IN ({EUROPE_COUNTRY_SQL})"
                )

            conn.execute(
                text(
                    f"""
                    DELETE FROM direct_routes route
                    USING airports origin, airports destination
                    WHERE origin.iata = route.origin_iata
                      AND destination.iata = route.destination_iata
                      AND (
                        {non_europe_airport_condition("origin")}
                        OR {non_europe_airport_condition("destination")}
                      )
                    """
                )
            )
            conn.execute(text(f"DELETE FROM airports airport WHERE {non_europe_airport_condition('airport')}"))
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS trip_share_links (
                        id SERIAL PRIMARY KEY,
                        trip_id INTEGER NOT NULL REFERENCES planned_trips(id) ON DELETE CASCADE,
                        created_by_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        share_token TEXT NOT NULL UNIQUE,
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS idx_trip_share_links_trip_active
                    ON trip_share_links (trip_id, is_active)
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS trip_share_invitations (
                        id SERIAL PRIMARY KEY,
                        source_trip_id INTEGER NOT NULL REFERENCES planned_trips(id) ON DELETE CASCADE,
                        from_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        to_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        status TEXT NOT NULL DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT NOW(),
                        responded_at TIMESTAMP NULL,
                        result_trip_id INTEGER NULL REFERENCES planned_trips(id) ON DELETE SET NULL
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS idx_trip_share_invitations_to_status
                    ON trip_share_invitations (to_user_id, status)
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS uniq_trip_share_invitation_pending
                    ON trip_share_invitations (source_trip_id, to_user_id)
                    WHERE status = 'pending'
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS password_reset_tokens (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        token_hash TEXT NOT NULL UNIQUE,
                        expires_at TIMESTAMP NOT NULL,
                        used_at TIMESTAMP NULL,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                    """
                )
            )
    except SQLAlchemyError as exc:
        logger.warning("Could not apply startup schema patch: %s", exc)
