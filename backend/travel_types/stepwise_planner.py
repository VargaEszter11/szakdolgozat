"""Build itineraries leg-by-leg: each hop loads Amadeus direct destinations from the *current* airport."""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from utils.nearest_airport import get_direct_destinations

from .llm_client import call_llm_api
from .prompt_common import language_name, preferences_line, stepwise_next_stop_prompt


def _split_place_label(label: str):
    parts = [p.strip() for p in label.split(",") if p.strip()]
    if len(parts) >= 2:
        return parts[0], parts[-1]
    return (label.strip(), "")


def _extract_city(place_str: str) -> str:
    return place_str.split(",")[0].strip().lower()


def _is_forbidden(city_name: str, country_name: str, visited_cities: set, visited_full: list) -> bool:
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


def _filter_visited(dests: List[dict], visited_places: List[str]) -> List[dict]:
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


def _filter_unvisited(dests: List[dict], forbidden_places: List[str]) -> List[dict]:
    visited_cities = {_extract_city(p) for p in forbidden_places}
    visited_full = [p.lower() for p in forbidden_places]
    out: List[dict] = []
    seen: set[str] = set()
    for d in dests:
        city = d.get("city") or ""
        country = d.get("country") or ""
        iata = d.get("iata")
        if not city or not iata:
            continue
        if _is_forbidden(city, country, visited_cities, visited_full):
            continue
        if iata not in seen:
            seen.add(iata)
            out.append(d)
    return out


def _filter_random(dests: List[dict]) -> List[dict]:
    out: List[dict] = []
    seen: set[str] = set()
    for d in dests:
        if d.get("city") and d.get("iata"):
            i = d["iata"]
            if i not in seen:
                seen.add(i)
                out.append(d)
    return out


def _format_candidates(dests: List[dict]) -> str:
    lines = []
    for d in dests:
        c, co, i = d.get("city"), d.get("country"), d.get("iata")
        if c and i:
            lines.append(f"- {c}, {co} (IATA: {i})")
    return "\n".join(lines) if lines else "(no direct destinations from this airport)"


def _finalize_segment_days_and_dates(
    plan: List[Dict[str, Any]], start_date: str, end_date: str, travel_length: int
) -> None:
    """Align intermediate ``days`` to ``travel_length`` and recompute dates."""
    if len(plan) < 2:
        return
    mids = plan[:-1]
    if not mids:
        return
    for _ in range(12):
        s = sum(max(1, int(x.get("days") or 1)) for x in mids)
        if s == int(travel_length):
            break
        dlt = int(travel_length) - s
        last = mids[-1]
        last["days"] = max(1, int(last.get("days") or 1) + dlt)
    walker = datetime.strptime(start_date, "%Y-%m-%d")
    for seg in mids:
        d = max(1, int(seg.get("days") or 1))
        seg["days"] = d
        seg["arrivalDate"] = walker.strftime("%Y-%m-%d")
        walker = walker + timedelta(days=d)
        seg["departureDate"] = walker.strftime("%Y-%m-%d")
    plan[-1]["arrivalDate"] = end_date
    plan[-1]["departureDate"] = end_date
    plan[-1]["days"] = 0


def _parse_json_object(raw: str) -> Optional[Dict[str, Any]]:
    text = (raw or "").strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def _pick_fallback(candidates: List[dict], remaining_days: int) -> Dict[str, Any]:
    d = random.choice(candidates)
    days = max(1, min(remaining_days, max(1, remaining_days // 2 or 1)))
    return {
        "city": d.get("city"),
        "country": d.get("country") or "",
        "iata": d.get("iata"),
        "days": days,
        "transportFromPreviousCity": "flight",
        "activities": ["City walk", "Local sights"],
    }


async def _llm_pick_next_stop(
    *,
    strategy: str,
    lang_name: str,
    current_airport: str,
    current_city_label: str,
    candidates: List[dict],
    remaining_days: int,
    preferences: List[str],
    avoid_labels: List[str],
    llm_provider: str,
) -> Optional[Dict[str, Any]]:
    cand_block = _format_candidates(candidates)
    avoid = ", ".join(avoid_labels[-8:]) if avoid_labels else "none"
    prefs = preferences_line(preferences)
    prompt = stepwise_next_stop_prompt(
        strategy=strategy,
        lang_name=lang_name,
        current_airport=current_airport,
        current_city_label=current_city_label,
        prefs=prefs,
        remaining_days=remaining_days,
        cand_block=cand_block,
        avoid=avoid,
    )
    raw = await call_llm_api(prompt, llm_provider)
    obj = _parse_json_object(raw)
    if not obj:
        return None
    iata = (obj.get("iata") or "").strip().upper()
    allowed_map = {(d.get("iata") or "").strip().upper(): d for d in candidates if d.get("iata")}
    if iata not in allowed_map:
        return None
    d = allowed_map[iata]
    days = int(obj.get("days") or 0)
    if days < 1:
        days = 1
    if days > remaining_days:
        days = remaining_days
    acts = obj.get("activities") or ["City exploration"]
    if not isinstance(acts, list):
        acts = [str(acts)]
    acts = [str(a) for a in acts if a][:3]
    return {
        "city": d.get("city") or obj.get("city"),
        "country": d.get("country") or obj.get("country") or "",
        "iata": d.get("iata"),
        "days": days,
        "transportFromPreviousCity": obj.get("transportFromPreviousCity") or "flight",
        "activities": acts or ["City exploration"],
    }


async def build_plan_stepwise(
    *,
    strategy: str,
    starting_point: str,
    starting_airport_iata: str,
    travel_length: int,
    preferences: List[str],
    start_date: str,
    end_date: str,
    language: str,
    llm_provider: str,
    visited_places: Optional[List[str]] = None,
    forbidden_places: Optional[List[str]] = None,
) -> Dict[str, Any]:
    lang_name = language_name(language)
    home_city, home_country = _split_place_label(starting_point)
    plan: List[Dict[str, Any]] = []
    current_airport = starting_airport_iata
    cursor = datetime.strptime(start_date, "%Y-%m-%d")
    remaining = int(travel_length)
    avoid_labels: List[str] = [home_city.lower()]
    max_legs = min(24, max(1, remaining) + 8)

    visited_places = visited_places or []
    forbidden_places = forbidden_places or []

    for _ in range(max_legs):
        if remaining <= 0:
            break

        raw_dests = await get_direct_destinations(current_airport)
        if strategy == "visited":
            candidates = _filter_visited(raw_dests, visited_places)
        elif strategy == "unvisited":
            candidates = _filter_unvisited(raw_dests, forbidden_places)
        else:
            candidates = _filter_random(raw_dests)

        # Do not bounce back to the same IATA as home hub mid-trip (return leg is separate).
        hub = (starting_airport_iata or "").strip().upper()
        candidates = [
            c for c in candidates if c.get("iata") and (c.get("iata") or "").strip().upper() != hub
        ]

        # Drop already visited IATAs on this trip
        used_iata = {(p.get("iata") or "").strip().upper() for p in plan if p.get("iata")}
        candidates = [c for c in candidates if (c.get("iata") or "").strip().upper() not in used_iata]

        if not candidates:
            break

        choice = None
        for _attempt in range(2):
            choice = await _llm_pick_next_stop(
                strategy=strategy,
                lang_name=lang_name,
                current_airport=current_airport,
                current_city_label=starting_point if not plan else f"{plan[-1].get('city')}, {plan[-1].get('country')}",
                candidates=candidates,
                remaining_days=remaining,
                preferences=preferences,
                avoid_labels=avoid_labels,
                llm_provider=llm_provider,
            )
            if choice:
                break
        if not choice:
            choice = _pick_fallback(candidates, remaining)

        days = int(choice.get("days") or 1)
        days = max(1, min(days, remaining))

        arrival = cursor.strftime("%Y-%m-%d")
        departure_dt = cursor + timedelta(days=days)
        departure = departure_dt.strftime("%Y-%m-%d")

        plan.append(
            {
                "city": choice["city"],
                "country": choice.get("country") or "",
                "iata": choice["iata"],
                "days": days,
                "arrivalDate": arrival,
                "departureDate": departure,
                "transportFromPreviousCity": choice.get("transportFromPreviousCity") or "flight",
                "activities": choice.get("activities") or [],
                "direct_flights_queried_from": current_airport,
            }
        )
        avoid_labels.append(str(choice.get("city") or "").lower())
        cursor = departure_dt
        remaining -= days
        current_airport = choice["iata"]

    if remaining > 0 and plan:
        plan[-1]["days"] = int(plan[-1].get("days") or 1) + remaining

    # Return leg to hub
    plan.append(
        {
            "city": home_city,
            "country": home_country,
            "iata": starting_airport_iata,
            "days": 0,
            "arrivalDate": end_date,
            "departureDate": end_date,
            "transportFromPreviousCity": "flight",
            "activities": [],
            "direct_flights_queried_from": None,
        }
    )

    _finalize_segment_days_and_dates(plan, start_date, end_date, travel_length)

    return {
        "startingPoint": starting_point,
        "startDate": start_date,
        "endDate": end_date,
        "tripLengthDays": travel_length,
        "strategy": strategy,
        "plan": plan,
    }
