"""Resolve typed places that are not airport hubs (geocode + ground vs airport access).

Used in visited mode when a requested place does not match any direct-route
candidate. Each resolution becomes an injectable planner candidate: either a
single off-airport ground leg or fly-to-hub + ground transfer (via_airport).
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Set

from utils.coordinates import geocode_place
from utils.nearest_airport import nearest_airport

from .place_matching import place_matches_candidate, place_used_in_plan, split_place_label
from .route_candidates import (
    GROUND_MAX_DISTANCE_KM,
    _airport_by_iata,
    _has_coordinates,
    _iata,
    calculate_distance_km,
    can_use_ground_transport,
    transport_for_ground_distance,
)

# Home is treated as off-hub when farther than this from the nearest airport.
HOME_HUB_MIN_TRANSFER_KM = 25.0



def _allowed_modes(preferred_transport: str) -> Optional[Set[str]]:
    preference = (preferred_transport or "allModes").strip()
    if preference == "flight":
        return {"flight"}
    if preference == "trainBus":
        return {"train", "bus"}
    if preference == "trainBusFerry":
        return {"train", "bus", "ferry"}
    return None


def _ground_allowed(preferred_transport: str) -> bool:
    allowed = _allowed_modes(preferred_transport)
    return allowed is None or bool(allowed & {"train", "bus"})


def _flight_allowed(preferred_transport: str) -> bool:
    allowed = _allowed_modes(preferred_transport)
    return allowed is None or "flight" in allowed


def _point(lat: float, lon: float, country_code: str = ""):
    return SimpleNamespace(latitude=lat, longitude=lon, country_code=country_code or None)


def _country_hint(place: str, nearest: Optional[dict]) -> str:
    _, country = split_place_label(place)
    if country and len(country.strip()) == 2:
        return country.strip().upper()
    if nearest and nearest.get("country"):
        return str(nearest["country"]).strip().upper()
    return (country or "").strip()[:2].upper() if country else ""


async def resolve_place_access(
    db,
    place: str,
    *,
    current_airport: str,
    preferred_transport: str = "allModes",
    language: str = "en",
    cache: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Decide how to reach a typed place that may not be an airport city.

    Returns:
    - direct_ground candidate (off-airport stop, hub iata = nearest airport to place)
    - via_airport descriptor (fly/bus to access airport, then ground to place)
    - None if unreachable under current transport preferences
    """
    text = (place or "").strip()
    if not text:
        return None

    cache_key = text.lower()
    if cache is not None and cache_key in cache:
        return cache[cache_key]

    origin = _airport_by_iata(db, current_airport)
    if not _has_coordinates(origin):
        if cache is not None:
            cache[cache_key] = None
        return None

    try:
        lat, lon = await geocode_place(text, language=language)
    except Exception:
        if cache is not None:
            cache[cache_key] = None
        return None

    nearest = nearest_airport(lat, lon, db=db)
    country = _country_hint(text, nearest)
    place_point = _point(lat, lon, country)

    distance_from_current = calculate_distance_km(
        float(origin.latitude),
        float(origin.longitude),
        lat,
        lon,
    )
    can_ground_from_current = (
        _ground_allowed(preferred_transport)
        and distance_from_current <= GROUND_MAX_DISTANCE_KM
        and can_use_ground_transport(origin, place_point)
    )

    hub_iata = _iata((nearest or {}).get("iata")) or _iata(current_airport)
    hub_country = (nearest or {}).get("country") or country or (origin.country_code or "")

    result: Optional[Dict[str, Any]] = None

    # Path A: reachable by ground from the current hub (same landmass, within range).
    if can_ground_from_current:
        transport = transport_for_ground_distance(distance_from_current)
        result = {            "kind": "direct_ground",
            "city": (split_place_label(text)[0] or text).strip().title(),
            "country": hub_country,
            "iata": hub_iata,
            "transport": transport,
            "distance_km": round(distance_from_current, 1),
            "requested_place": text,
            "off_airport": True,
            "latitude": lat,
            "longitude": lon,
        }
    # Path B: fly (or ground) to the airport nearest the typed place, then transfer.
    elif _flight_allowed(preferred_transport) and nearest and nearest.get("iata"):
        access_iata = _iata(nearest["iata"])
        access_airport = _airport_by_iata(db, access_iata)
        if not access_airport or not _has_coordinates(access_airport):
            result = None
        else:
            transfer_distance = calculate_distance_km(
                float(access_airport.latitude),
                float(access_airport.longitude),
                lat,
                lon,
            )
            if transfer_distance > GROUND_MAX_DISTANCE_KM:
                result = None
            elif access_iata == _iata(current_airport) and _ground_allowed(preferred_transport):
                # Already at the access airport: only the ground transfer remains.
                transport = transport_for_ground_distance(transfer_distance)
                result = {
                    "kind": "direct_ground",
                    "city": (split_place_label(text)[0] or text).strip().title(),
                    "country": nearest.get("country") or country,
                    "iata": access_iata,
                    "transport": transport,
                    "distance_km": round(transfer_distance, 1),
                    "requested_place": text,
                    "off_airport": True,
                    "latitude": lat,
                    "longitude": lon,
                }
            elif not _ground_allowed(preferred_transport) and transfer_distance > 1:
                # Flight-only cannot complete an off-airport place visit.
                result = None
            else:
                # Two-leg visit: flight candidate to access_iata carries ground_transfer
                # metadata; plan_builder merges them into one off-airport stop.
                transfer_transport = transport_for_ground_distance(transfer_distance)
                result = {                    "kind": "via_airport",
                    "access_iata": access_iata,
                    "access_city": nearest.get("city") or access_iata,
                    "access_country": nearest.get("country") or country,
                    "requested_place": text,
                    "ground_transfer": {
                        "city": (split_place_label(text)[0] or text).strip().title(),
                        "country": nearest.get("country") or country,
                        "iata": access_iata,
                        "transport": transfer_transport,
                        "distance_km": round(transfer_distance, 1),
                        "requested_place": text,
                        "off_airport": True,
                        "is_ground_transfer": True,
                        "latitude": lat,
                        "longitude": lon,
                    },
                }
    elif _ground_allowed(preferred_transport) and not _flight_allowed(preferred_transport):
        # Ground-only but too far / different land area.
        result = None
    else:
        result = None

    if cache is not None:
        cache[cache_key] = result
    return result


def candidates_for_unmatched_places(
    resolutions: List[Dict[str, Any]],
    *,
    reachable_iatas: Set[str],
    current_airport: str,
) -> List[dict]:
    """Turn place-access resolutions into planner candidates for this step.

    via_airport entries only appear when the access hub is the current airport
    or has a direct route from it; otherwise the leg is skipped this turn.
    """
    current = _iata(current_airport)
    out: List[dict] = []
    seen: Set[str] = set()

    for resolution in resolutions:
        if not resolution:
            continue
        kind = resolution.get("kind")
        if kind == "direct_ground":
            key = f"place:{(resolution.get('requested_place') or '').lower()}"
            if key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    "city": (split_place_label(resolution.get("requested_place") or resolution["city"])[0] or resolution["city"]).strip().title(),
                    "country": resolution.get("country") or "",
                    "iata": resolution["iata"],
                    "transport": resolution.get("transport") or "bus",
                    "distance_km": resolution.get("distance_km"),
                    "requested_place": resolution.get("requested_place"),
                    "off_airport": True,
                }
            )
            continue

        if kind != "via_airport":
            continue

        access = _iata(resolution.get("access_iata"))
        if not access:
            continue
        if access != current and access not in reachable_iatas:
            continue

        if access == current and resolution.get("ground_transfer"):
            # Already at the hub — emit only the ground leg to the typed place.
            transfer = dict(resolution["ground_transfer"])
            key = f"place:{(transfer.get('requested_place') or '').lower()}"
            if key in seen:                continue
            seen.add(key)
            out.append(
                {
                    "city": (transfer.get("city") or transfer.get("requested_place") or "").strip().title(),
                    "country": transfer.get("country") or "",
                    "iata": transfer["iata"],
                    "transport": transfer.get("transport") or "bus",
                    "distance_km": transfer.get("distance_km"),
                    "requested_place": transfer.get("requested_place"),
                    "off_airport": True,
                }
            )
            continue

        key = f"access:{access}:{(resolution.get('requested_place') or '').lower()}"
        if key in seen:
            continue
        seen.add(key)
        # Hub visit city is access_city; ground_transfer holds the real destination.
        candidate = {            "city": resolution.get("access_city") or access,
            "country": resolution.get("access_country") or "",
            "iata": access,
            "transport": "flight",
            "requested_place": resolution.get("requested_place"),
            "via_place_access": True,
        }
        if resolution.get("ground_transfer"):
            candidate["ground_transfer"] = dict(resolution["ground_transfer"])
        out.append(candidate)

    return out


def home_hub_transfer_from_coords(
    db,
    *,
    home_lat: float,
    home_lon: float,
    hub_iata: str,
    preferred_transport: str = "allModes",
) -> Optional[Dict[str, Any]]:
    """Return ground transfer home ↔ hub airport when home is meaningfully off-airport."""
    if not _ground_allowed(preferred_transport):
        return None
    hub = _airport_by_iata(db, hub_iata)
    if not _has_coordinates(hub):
        return None
    distance = calculate_distance_km(
        float(home_lat),
        float(home_lon),
        float(hub.latitude),
        float(hub.longitude),
    )
    if distance < HOME_HUB_MIN_TRANSFER_KM:
        return None
    if distance > GROUND_MAX_DISTANCE_KM:
        return None
    home_point = _point(home_lat, home_lon, getattr(hub, "country_code", None) or "")
    if not can_use_ground_transport(hub, home_point):
        return None
    return {
        "access_iata": _iata(hub_iata),
        "access_city": (getattr(hub, "city", None) or _iata(hub_iata) or "").strip(),
        "access_country": (getattr(hub, "country_code", None) or "").strip(),
        "local_transport": transport_for_ground_distance(distance),
        "distance_km": round(distance, 1),
    }


async def resolve_home_hub_transfer(
    db,
    starting_point: str,
    *,
    starting_airport_iata: str,
    preferred_transport: str = "allModes",
    language: str = "en",
) -> Optional[Dict[str, Any]]:
    """Geocode the starting place and decide if a home↔hub ground transfer is needed."""
    text = (starting_point or "").strip()
    hub = _iata(starting_airport_iata)
    if not text or not hub:
        return None
    try:
        lat, lon = await geocode_place(text, language=language)
    except Exception:
        return None
    return home_hub_transfer_from_coords(
        db,
        home_lat=lat,
        home_lon=lon,
        hub_iata=hub,
        preferred_transport=preferred_transport,
    )


def remaining_unmatched_places(
    requested_places: List[str],
    plan: List[Dict[str, Any]],
    airport_candidates: List[dict],
) -> List[str]:
    """Requested places not yet in the plan and not covered by route candidates."""
    remaining = [
        place for place in requested_places if place and not place_used_in_plan(place, plan)
    ]
    matched = []
    for place in remaining:
        if any(place_matches_candidate(place, candidate) for candidate in airport_candidates):
            continue
        matched.append(place)
    return matched
