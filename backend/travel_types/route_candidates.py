"""Route candidate construction and ranking for travel planning."""

from __future__ import annotations

import math
import re
from typing import List, Optional

from database import crud, models
from utils.direct_destinations_cache import get_direct_destinations_cached

from .place_matching import filter_strategy_candidates


EUROPE_COUNTRY_CODES = {
    "AL", "AD", "AT", "BE", "BA", "BG", "HR", "CY", "CZ", "DK",
    "EE", "FI", "FR", "DE", "GR", "HU", "IS", "IE", "IT", "XK",
    "LV", "LI", "LT", "LU", "MT", "MD", "MC", "ME", "NL", "MK",
    "NO", "PL", "PT", "RO", "SM", "RS", "SK", "SI", "ES", "SE",
    "CH", "GB", "VA",
}

GROUND_MAX_DISTANCE_KM = 650
FERRY_MAX_DISTANCE_KM = 450
GROUND_CANDIDATE_LIMIT = 12
RANKED_CANDIDATE_LIMIT = 18

BLOCKED_PLACE_PATTERNS = (
    r"\bairport\b",
    r"\baerodrome\b",
    r"\bheliport\b",
    r"\bhelipad\b",
    r"\bstation\b",
    r"\bterminal\b",
    r"\bferry\b",
    r"\bport\b",
    r"\bharbou?r\b",
    r"\bmarina\b",
)


def is_europe_country(country_code: Optional[str]) -> bool:
    return (country_code or "").strip().upper() in EUROPE_COUNTRY_CODES


def _iata(value: Optional[str]) -> str:
    return (value or "").strip().upper()


def _airport_by_iata(db, iata: str):
    return db.query(models.Airport).filter(models.Airport.iata == _iata(iata)).first()


def _has_coordinates(airport) -> bool:
    return bool(
        airport
        and airport.latitude is not None
        and airport.longitude is not None
    )


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


def transport_for_ground_distance(distance_km: float) -> str:
    return "bus" if distance_km <= 250 else "train"


def ground_area(airport) -> str:
    lat = float(airport.latitude)
    lng = float(airport.longitude)
    country = (airport.country_code or "").upper()

    # Keep this deliberately small: generated ground routes must stay on one land area.
    if 51.0 <= lat <= 56.5 and -11.0 <= lng <= -5.0:
        return "ireland"
    if 49.0 <= lat <= 59.0 and -6.5 <= lng <= 2.5:
        return "great_britain"
    if country in {"IS", "MT", "CY"}:
        return country
    return "mainland"


def can_use_ground_transport(origin, destination) -> bool:
    return ground_area(origin) == ground_area(destination)


def can_use_ferry_transport(origin, destination) -> bool:
    return ground_area(origin) != ground_area(destination)


def is_plannable_place_label(label: Optional[str]) -> bool:
    text = (label or "").strip().lower()
    if not text:
        return False
    return not any(re.search(pattern, text) for pattern in BLOCKED_PLACE_PATTERNS)


def airport_distance(db, origin_iata: str, destination_iata: str) -> Optional[float]:
    origin = _airport_by_iata(db, origin_iata)
    destination = _airport_by_iata(db, destination_iata)
    if not _has_coordinates(origin) or not _has_coordinates(destination):
        return None
    return calculate_distance_km(
        float(origin.latitude),
        float(origin.longitude),
        float(destination.latitude),
        float(destination.longitude),
    )


def ground_transport_between_airports(db, origin_iata: str, destination_iata: str) -> Optional[str]:
    origin = _airport_by_iata(db, origin_iata)
    destination = _airport_by_iata(db, destination_iata)
    if not _has_coordinates(origin) or not _has_coordinates(destination):
        return None
    if not can_use_ground_transport(origin, destination):
        return None

    distance = calculate_distance_km(
        float(origin.latitude),
        float(origin.longitude),
        float(destination.latitude),
        float(destination.longitude),
    )
    if distance <= GROUND_MAX_DISTANCE_KM:
        return transport_for_ground_distance(distance)
    return None


def ferry_transport_between_airports(db, origin_iata: str, destination_iata: str) -> Optional[str]:
    origin = _airport_by_iata(db, origin_iata)
    destination = _airport_by_iata(db, destination_iata)
    if not _has_coordinates(origin) or not _has_coordinates(destination):
        return None
    if not can_use_ferry_transport(origin, destination):
        return None

    distance = calculate_distance_km(
        float(origin.latitude),
        float(origin.longitude),
        float(destination.latitude),
        float(destination.longitude),
    )
    return "ferry" if distance <= FERRY_MAX_DISTANCE_KM else None


def ground_candidates_from_airport(
    db,
    origin_iata: str,
    *,
    excluded_iatas: set[str],
    max_distance_km: float = GROUND_MAX_DISTANCE_KM,
    limit: int = GROUND_CANDIDATE_LIMIT,
) -> List[dict]:
    origin_code = _iata(origin_iata)
    origin = _airport_by_iata(db, origin_code)
    if not _has_coordinates(origin):
        return []

    origin_lat = float(origin.latitude)
    origin_lng = float(origin.longitude)
    candidates = []
    airports = (
        db.query(models.Airport)
        .filter(
            models.Airport.latitude.isnot(None),
            models.Airport.longitude.isnot(None),
        )
        .all()
    )
    for airport in airports:
        iata = _iata(airport.iata)
        if (
            not iata
            or iata == origin_code
            or iata in excluded_iatas
            or not is_europe_country(airport.country_code)
            or not can_use_ground_transport(origin, airport)
        ):
            continue
        city = airport.city or crud._airport_name_as_city(airport.name, airport.iata)
        if not is_plannable_place_label(city):
            continue
        distance = calculate_distance_km(
            origin_lat,
            origin_lng,
            float(airport.latitude),
            float(airport.longitude),
        )
        if distance > max_distance_km:
            continue
        candidates.append(
            {
                "iata": airport.iata,
                "city": city,
                "country": airport.country_code,
                "transport": transport_for_ground_distance(distance),
                "distance_km": round(distance, 1),
            }
        )

    candidates.sort(key=lambda c: c["distance_km"])
    return candidates[:limit]


def ferry_candidates_from_airport(
    db,
    origin_iata: str,
    *,
    excluded_iatas: set[str],
    max_distance_km: float = FERRY_MAX_DISTANCE_KM,
    limit: int = GROUND_CANDIDATE_LIMIT,
) -> List[dict]:
    origin_code = _iata(origin_iata)
    origin = _airport_by_iata(db, origin_code)
    if not _has_coordinates(origin):
        return []

    origin_lat = float(origin.latitude)
    origin_lng = float(origin.longitude)
    candidates = []
    airports = (
        db.query(models.Airport)
        .filter(
            models.Airport.latitude.isnot(None),
            models.Airport.longitude.isnot(None),
        )
        .all()
    )
    for airport in airports:
        iata = _iata(airport.iata)
        if (
            not iata
            or iata == origin_code
            or iata in excluded_iatas
            or not is_europe_country(airport.country_code)
            or not can_use_ferry_transport(origin, airport)
        ):
            continue
        city = airport.city or crud._airport_name_as_city(airport.name, airport.iata)
        if not is_plannable_place_label(city):
            continue
        distance = calculate_distance_km(
            origin_lat,
            origin_lng,
            float(airport.latitude),
            float(airport.longitude),
        )
        if distance > max_distance_km:
            continue
        candidates.append(
            {
                "iata": airport.iata,
                "city": city,
                "country": airport.country_code,
                "transport": "ferry",
                "distance_km": round(distance, 1),
            }
        )

    candidates.sort(key=lambda c: c["distance_km"])
    return candidates[:limit]


def with_transport(candidates: List[dict], transport: str) -> List[dict]:
    out = []
    for candidate in candidates:
        item = dict(candidate)
        item.setdefault("transport", transport)
        out.append(item)
    return out


def europe_candidates(candidates: List[dict]) -> List[dict]:
    return [candidate for candidate in candidates if is_europe_country(candidate.get("country"))]


def dedupe_candidates(candidates: List[dict]) -> List[dict]:
    out = []
    seen_iatas: set[str] = set()
    seen_places: set[tuple[str, str]] = set()
    for candidate in candidates:
        iata = _iata(candidate.get("iata"))
        city = (candidate.get("city") or "").strip().lower()
        country = _iata(candidate.get("country"))
        airline = _iata(candidate.get("airline_iata"))
        place_key = (airline, city, country)

        iata_key = f"{airline}:{iata}"
        if iata and iata_key in seen_iatas:
            continue
        if city and place_key in seen_places:
            continue

        if iata:
            seen_iatas.add(iata_key)
        if city:
            seen_places.add(place_key)
        out.append(candidate)
    return out


def annotate_distances(db, origin_iata: str, candidates: List[dict]) -> List[dict]:
    out = []
    for candidate in candidates:
        item = dict(candidate)
        if item.get("distance_km") is None:
            distance = airport_distance(db, origin_iata, item.get("iata"))
            if distance is not None:
                item["distance_km"] = round(distance, 1)
        out.append(item)
    return out


def rank_candidates(
    candidates: List[dict],
    *,
    previous_iata: Optional[str] = None,
    limit: int = RANKED_CANDIDATE_LIMIT,
) -> List[dict]:
    previous = _iata(previous_iata)

    def score(candidate: dict) -> tuple:
        distance = candidate.get("distance_km")
        distance_score = distance if distance is not None else 10**9
        backtrack_penalty = 10**9 if previous and _iata(candidate.get("iata")) == previous else 0
        return (distance_score + backtrack_penalty, distance_score)

    return sorted(candidates, key=score)[:limit]


async def build_candidates(
    db,
    *,
    strategy: str,
    current_airport: str,
    hub_iata: str,
    used_iatas: set[str],
    visited_places: List[str],
    forbidden_places: List[str],
    preferred_transport: str = "allModes",
) -> List[dict]:
    candidate_strategy = "random" if strategy == "visited" else strategy
    include_flights = preferred_transport not in {"trainBus", "trainBusFerry"}
    flight_candidates = []
    if include_flights:
        flight_candidates = with_transport(
            filter_strategy_candidates(
                candidate_strategy,
                europe_candidates(await get_direct_destinations_cached(db, current_airport)),
                visited_places,
                forbidden_places,
            ),
            "flight",
        )

    ground_candidates = filter_strategy_candidates(
        candidate_strategy,
        ground_candidates_from_airport(
            db,
            current_airport,
            excluded_iatas={*used_iatas, _iata(hub_iata), _iata(current_airport)},
        ),
        visited_places,
        forbidden_places,
    )
    ferry_candidates = filter_strategy_candidates(
        candidate_strategy,
        ferry_candidates_from_airport(
            db,
            current_airport,
            excluded_iatas={*used_iatas, _iata(hub_iata), _iata(current_airport)},
        ),
        visited_places,
        forbidden_places,
    )

    candidates = [
        c
        for c in ground_candidates + ferry_candidates + flight_candidates
        if c.get("iata")
        and is_plannable_place_label(c.get("city"))
        and _iata(c.get("iata")) != _iata(hub_iata)
        and _iata(c.get("iata")) not in used_iatas
    ]
    return dedupe_candidates(candidates)


