import logging
import math
from typing import Any, Optional, cast

from sqlalchemy.orm import Session

from database import models

logger = logging.getLogger("planner.airports")

def calculate_distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    earth_radius_km = 6371.0088
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return earth_radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _airport_to_dict(airport: Any, distance_km: float) -> dict[str, Any]:
    row = cast(Any, airport)
    return {
        "name": row.name,
        "iata": row.iata,
        "icao": row.icao,
        "city": row.city,
        "country": row.country_code,
        "distance_km": round(distance_km, 2),
    }


def nearest_airports(
    lat,
    lng,
    db: Optional[Session] = None,
    limit: int = 1,
) -> list[dict[str, Any]]:
    """Return up to ``limit`` airports closest to given coordinates, nearest first.

    Only airports with at least one active outbound direct route are considered,
    same as ``nearest_airport``. Used so the planner can retry with the next-
    nearest airport when the closest one's route network doesn't actually
    produce a usable trip (e.g. wrong transport mode, no reachable destinations).
    Purely distance-ordered - closest first, no other ranking.
    """
    if db is None:
        logger.warning("Database session missing; nearest airport lookup skipped")
        return []
    try:
        origin_lat = float(lat)
        origin_lng = float(lng)
    except (TypeError, ValueError):
        logger.warning("Invalid coordinates for nearest airport lookup: %s, %s", lat, lng)
        return []

    airports = (
        db.query(models.Airport)
        .join(
            models.DirectRoute,
            models.DirectRoute.origin_iata == models.Airport.iata,
        )
        .filter(
            models.Airport.latitude.isnot(None),
            models.Airport.longitude.isnot(None),
            models.DirectRoute.is_active.is_(True),
        )
        .distinct()
        .all()
    )
    if not airports:
        logger.warning("No cached route origins with coordinates available for nearest airport lookup")
        return []

    ranked: list[tuple[float, Any]] = []
    for airport in airports:
        airport_row = cast(Any, airport)
        try:
            distance = calculate_distance_km(
                origin_lat,
                origin_lng,
                float(airport_row.latitude),
                float(airport_row.longitude),
            )
        except (TypeError, ValueError):
            continue
        ranked.append((distance, airport))

    ranked.sort(key=lambda item: item[0])
    top = ranked[: max(1, limit)]

    if top:
        distance, closest = top[0]
        logger.info(
            "Closest airport found: %s (%s, %s) %.2f km from %.6f, %.6f",
            cast(Any, closest).iata,
            cast(Any, closest).city or "unknown city",
            cast(Any, closest).country_code or "unknown country",
            distance,
            origin_lat,
            origin_lng,
        )

    return [_airport_to_dict(airport, distance) for distance, airport in top]


def nearest_airport(
    lat,
    lng,
    db: Optional[Session] = None,
    distance_km: Optional[float] = None,
) -> Optional[dict[str, Any]]:
    """Return the single nearest airport to given coordinates. See ``nearest_airports``."""
    del distance_km
    results = nearest_airports(lat, lng, db=db, limit=1)
    return results[0] if results else None

