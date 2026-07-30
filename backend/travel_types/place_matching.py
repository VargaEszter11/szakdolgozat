"""Place matching and strategy filters for route planning."""

from __future__ import annotations

from typing import Any, Dict, List


COUNTRY_NAME_TO_CODE = {
    "albania": "AL",
    "andorra": "AD",
    "austria": "AT",
    "belgium": "BE",
    "bosnia and herzegovina": "BA",
    "bosnia": "BA",
    "bulgaria": "BG",
    "croatia": "HR",
    "cyprus": "CY",
    "czech republic": "CZ",
    "czechia": "CZ",
    "denmark": "DK",
    "estonia": "EE",
    "finland": "FI",
    "france": "FR",
    "germany": "DE",
    "greece": "GR",
    "hungary": "HU",
    "iceland": "IS",
    "ireland": "IE",
    "italy": "IT",
    "kosovo": "XK",
    "latvia": "LV",
    "liechtenstein": "LI",
    "lithuania": "LT",
    "luxembourg": "LU",
    "malta": "MT",
    "moldova": "MD",
    "monaco": "MC",
    "montenegro": "ME",
    "netherlands": "NL",
    "north macedonia": "MK",
    "norway": "NO",
    "poland": "PL",
    "portugal": "PT",
    "romania": "RO",
    "san marino": "SM",
    "serbia": "RS",
    "slovakia": "SK",
    "slovenia": "SI",
    "spain": "ES",
    "sweden": "SE",
    "switzerland": "CH",
    "united kingdom": "GB",
    "great britain": "GB",
    "uk": "GB",
    "england": "GB",
    "vatican city": "VA",
    "vatican": "VA",
}

COUNTRY_CODE_TO_NAME = {code: name for name, code in COUNTRY_NAME_TO_CODE.items()}


def split_place_label(label: str):
    parts = [p.strip() for p in label.split(",") if p.strip()]
    if len(parts) >= 2:
        return parts[0], parts[-1]
    return (label.strip(), "")


def extract_city(place_str: str) -> str:
    return place_str.split(",")[0].strip().lower()


def _country_code(value: str) -> str:
    text = (value or "").strip().lower()
    if not text:
        return ""
    if len(text) == 2:
        return text.upper()
    return COUNTRY_NAME_TO_CODE.get(text, "")


def _country_tokens(value: str) -> set[str]:
    code = _country_code(value)
    tokens = {code.lower()} if code else set()
    text = (value or "").strip().lower()
    if text:
        tokens.add(text)
    if code and COUNTRY_CODE_TO_NAME.get(code):
        tokens.add(COUNTRY_CODE_TO_NAME[code])
    return tokens


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
    requested = (candidate.get("requested_place") or "").strip()
    if requested and (
        candidate.get("off_airport")
        or candidate.get("is_ground_transfer")
        or candidate.get("via_place_access")
        or candidate.get("ground_transfer")
    ):
        requested_city = extract_city(requested)
        if requested_city and (
            place_city in requested_city
            or requested_city in place_city
            or place_city == requested_city
        ):
            return True
    city = (candidate.get("city") or "").strip().lower()
    country = (candidate.get("country") or "").strip().lower()
    full = f"{city}, {country}" if country else city
    if city and (place_city in city or city in place_city or place_city in full):
        return True

    place_country = _country_code(place_city)
    if not place_country:
        return False
    return place_country.lower() in _country_tokens(country)


def place_used_in_plan(place: str, plan: List[Dict[str, Any]]) -> bool:
    place_city = extract_city(place)
    if not place_city:
        return True
    for stop in plan:
        if place_matches_candidate(place, stop):
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
        for d in dests:
            iata = d.get("iata")
            if not iata:
                continue
            if place_matches_candidate(place, d):
                if iata not in seen:
                    seen.add(iata)
                    out.append(d)
    return out


def filter_unvisited(dests: List[dict], forbidden_places: List[str]) -> List[dict]:
    out: List[dict] = []
    seen: set[str] = set()
    for d in dests:
        city = d.get("city") or ""
        iata = d.get("iata")
        if not city or not iata:
            continue
        if any(place_matches_candidate(place, d) for place in forbidden_places):
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
