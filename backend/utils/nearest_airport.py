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


def nearest_airport(
    lat,
    lng,
    db: Optional[Session] = None,
    distance_km: Optional[float] = None,
) -> Optional[dict[str, Any]]:
    """Return the nearest airport to given coordinates using cached DB airport coordinates."""
    if db is None:
        logger.warning("Database session missing; nearest airport lookup skipped")
        return None
    try:
        origin_lat = float(lat)
        origin_lng = float(lng)
    except (TypeError, ValueError):
        logger.warning("Invalid coordinates for nearest airport lookup: %s, %s", lat, lng)
        return None

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
        return None

    closest = None
    closest_distance = None
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
        if closest_distance is None or distance < closest_distance:
            closest = airport
            closest_distance = distance

    if closest is None or closest_distance is None:
        return None

    if distance_km is not None and closest_distance > float(distance_km):
        logger.info(
            "Nearest cached airport %s is %.1f km away, outside %.1f km preferred radius; using it anyway",
            closest.iata,
            closest_distance,
            float(distance_km),
        )

    logger.info(
        "Closest airport found: %s (%s, %s) %.2f km from %.6f, %.6f",
        cast(Any, closest).iata,
        cast(Any, closest).city or "unknown city",
        cast(Any, closest).country_code or "unknown country",
        closest_distance,
        origin_lat,
        origin_lng,
    )

    closest_row = cast(Any, closest)
    return {
        "name": closest_row.name,
        "iata": closest_row.iata,
        "icao": closest_row.icao,
        "city": closest_row.city,
        "country": closest_row.country_code,
        "distance_km": round(closest_distance, 2),
    }

