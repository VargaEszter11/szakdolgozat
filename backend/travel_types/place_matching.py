"""Place matching and strategy filters for route planning."""

from __future__ import annotations

from typing import Any, Dict, List


def split_place_label(label: str):
    parts = [p.strip() for p in label.split(",") if p.strip()]
    if len(parts) >= 2:
        return parts[0], parts[-1]
    return (label.strip(), "")


def extract_city(place_str: str) -> str:
    return place_str.split(",")[0].strip().lower()


def is_forbidden(city_name: str, country_name: str, visited_cities: set, visited_full: list) -> bool:
    city_lower = city_name.lower()
    if city_lower in visited_cities:
        return True
    full_str = f"{city_lower}, {country_name.lower()}" if country_name else city_lower
    for visited in visited_full:
        if city_lower in visited or visited in city_lower:
            return True
        if visited in full_str or full_str in visited:
            return True
    return False


def place_matches_candidate(place: str, candidate: dict) -> bool:
    place_city = extract_city(place)
    if not place_city:
        return False
    city = (candidate.get("city") or "").strip().lower()
    country = (candidate.get("country") or "").strip().lower()
    full = f"{city}, {country}" if country else city
    return bool(city and (place_city in city or city in place_city or place_city in full))


def place_used_in_plan(place: str, plan: List[Dict[str, Any]]) -> bool:
    place_city = extract_city(place)
    if not place_city:
        return True
    for stop in plan:
        city = (stop.get("city") or "").strip().lower()
        country = (stop.get("country") or "").strip().lower()
        full = f"{city}, {country}" if country else city
        if city and (place_city in city or city in place_city or place_city in full):
            return True
    return False


def prioritize_requested_places(
    candidates: List[dict],
    requested_places: List[str],
    plan: List[Dict[str, Any]],
) -> List[dict]:
    remaining_places = [
        place for place in requested_places if not place_used_in_plan(place, plan)
    ]
    if not remaining_places:
        return candidates

    def score(candidate: dict) -> tuple:
        for index, place in enumerate(remaining_places):
            if place_matches_candidate(place, candidate):
                return (0, index)
        return (1, len(remaining_places))

    return sorted(candidates, key=score)


def filter_visited(dests: List[dict], visited_places: List[str]) -> List[dict]:
    out: List[dict] = []
    seen: set[str] = set()
    for place in visited_places:
        place_lower = place.lower()
        for d in dests:
            city_key = (d.get("city") or "").lower()
            iata = d.get("iata")
            if not city_key or not iata:
                continue
            if city_key and (place_lower in city_key or city_key in place_lower):
                if iata not in seen:
                    seen.add(iata)
                    out.append(d)
    return out


def filter_unvisited(dests: List[dict], forbidden_places: List[str]) -> List[dict]:
    visited_cities = {extract_city(p) for p in forbidden_places}
    visited_full = [p.lower() for p in forbidden_places]
    out: List[dict] = []
    seen: set[str] = set()
    for d in dests:
        city = d.get("city") or ""
        country = d.get("country") or ""
        iata = d.get("iata")
        if not city or not iata:
            continue
        if is_forbidden(city, country, visited_cities, visited_full):
            continue
        if iata not in seen:
            seen.add(iata)
            out.append(d)
    return out


def filter_random(dests: List[dict]) -> List[dict]:
    out: List[dict] = []
    seen: set[str] = set()
    for d in dests:
        if d.get("city") and d.get("iata"):
            iata = d["iata"]
            if iata not in seen:
                seen.add(iata)
                out.append(d)
    return out


def filter_strategy_candidates(
    strategy: str,
    raw_dests: List[dict],
    visited_places: List[str],
    forbidden_places: List[str],
) -> List[dict]:
    if strategy == "visited":
        return filter_visited(raw_dests, visited_places)
    if strategy == "unvisited":
        return filter_unvisited(raw_dests, forbidden_places)
    return filter_random(raw_dests)
