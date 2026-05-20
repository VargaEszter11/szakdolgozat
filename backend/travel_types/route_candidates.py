"""Route candidate construction and ranking for stepwise planning."""

from __future__ import annotations

import math
import re
from typing import List, Optional

from database import crud, models
from utils.direct_destinations_cache import get_direct_destinations_cached

from .place_matching import filter_strategy_candidates


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
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


def is_plannable_place_label(label: Optional[str]) -> bool:
    text = (label or "").strip().lower()
    if not text:
        return False

    blocked_patterns = (
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
    return not any(re.search(pattern, text) for pattern in blocked_patterns)


def airport_distance(db, origin_iata: str, destination_iata: str) -> Optional[float]:
    origin = db.query(models.Airport).filter(models.Airport.iata == (origin_iata or "").strip().upper()).first()
    destination = (
        db.query(models.Airport)
        .filter(models.Airport.iata == (destination_iata or "").strip().upper())
        .first()
    )
    if (
        not origin
        or not destination
        or origin.latitude is None
        or origin.longitude is None
        or destination.latitude is None
        or destination.longitude is None
    ):
        return None
    return haversine_km(
        float(origin.latitude),
        float(origin.longitude),
        float(destination.latitude),
        float(destination.longitude),
    )


def ground_transport_between_airports(db, origin_iata: str, destination_iata: str) -> Optional[str]:
    origin = db.query(models.Airport).filter(models.Airport.iata == (origin_iata or "").strip().upper()).first()
    destination = (
        db.query(models.Airport)
        .filter(models.Airport.iata == (destination_iata or "").strip().upper())
        .first()
    )
    if (
        not origin
        or not destination
        or origin.latitude is None
        or origin.longitude is None
        or destination.latitude is None
        or destination.longitude is None
        or not can_use_ground_transport(origin, destination)
    ):
        return None

    distance = haversine_km(
        float(origin.latitude),
        float(origin.longitude),
        float(destination.latitude),
        float(destination.longitude),
    )
    if distance is not None and distance <= 650:
        return transport_for_ground_distance(distance)
    return None


def ground_candidates_from_airport(
    db,
    origin_iata: str,
    *,
    excluded_iatas: set[str],
    max_distance_km: float = 650,
    limit: int = 12,
) -> List[dict]:
    origin_code = (origin_iata or "").strip().upper()
    origin = db.query(models.Airport).filter(models.Airport.iata == origin_code).first()
    if not origin or origin.latitude is None or origin.longitude is None:
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
        iata = (airport.iata or "").strip().upper()
        if not iata or iata == origin_code or iata in excluded_iatas:
            continue
        city = airport.city or crud._airport_name_as_city(airport.name, airport.iata)
        if not is_plannable_place_label(city):
            continue
        if not can_use_ground_transport(origin, airport):
            continue
        distance = haversine_km(
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


def with_transport(candidates: List[dict], transport: str) -> List[dict]:
    out = []
    for c in candidates:
        item = dict(c)
        item.setdefault("transport", transport)
        out.append(item)
    return out


def dedupe_candidates(candidates: List[dict]) -> List[dict]:
    out = []
    seen_iatas: set[str] = set()
    seen_places: set[tuple[str, str]] = set()
    for candidate in candidates:
        iata = (candidate.get("iata") or "").strip().upper()
        city = (candidate.get("city") or "").strip().lower()
        country = (candidate.get("country") or "").strip().upper()
        place_key = (city, country)

        if iata and iata in seen_iatas:
            continue
        if city and place_key in seen_places:
            continue

        if iata:
            seen_iatas.add(iata)
        if city:
            seen_places.add(place_key)
        out.append(candidate)
    return out


def annotate_distances(db, origin_iata: str, candidates: List[dict]) -> List[dict]:
    out = []
    for c in candidates:
        item = dict(c)
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
    limit: int = 18,
) -> List[dict]:
    def score(c: dict) -> tuple:
        distance = c.get("distance_km")
        distance_score = distance if distance is not None else 10**9
        backtrack_penalty = 0
        if previous_iata and (c.get("iata") or "").strip().upper() == previous_iata:
            backtrack_penalty = 10**9
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
) -> List[dict]:
    candidate_strategy = "random" if strategy == "visited" else strategy
    direct_dests = await get_direct_destinations_cached(db, current_airport)
    flight_candidates = with_transport(
        filter_strategy_candidates(candidate_strategy, direct_dests, visited_places, forbidden_places),
        "flight",
    )

    excluded_iatas = set(used_iatas)
    excluded_iatas.add((hub_iata or "").strip().upper())
    excluded_iatas.add((current_airport or "").strip().upper())

    ground_candidates = filter_strategy_candidates(
        candidate_strategy,
        ground_candidates_from_airport(db, current_airport, excluded_iatas=excluded_iatas),
        visited_places,
        forbidden_places,
    )

    candidates = [
        c
        for c in ground_candidates + flight_candidates
        if c.get("iata")
        and is_plannable_place_label(c.get("city"))
        and (c.get("iata") or "").strip().upper() != (hub_iata or "").strip().upper()
        and (c.get("iata") or "").strip().upper() not in used_iatas
    ]
    return dedupe_candidates(candidates)


