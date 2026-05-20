"""Build itineraries leg-by-leg from validated local route candidates."""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from database.database import SessionLocal

from .llm_client import call_llm_api
from .place_matching import (
    place_matches_candidate,
    place_used_in_plan,
    prioritize_requested_places,
    split_place_label,
)
from .prompt_common import language_name, preferences_line, stepwise_next_stop_prompt
from .route_candidates import (
    annotate_distances,
    build_candidates,
    ground_transport_between_airports,
    rank_candidates,
)


def _finalize_segment_days_and_dates(
    plan: List[Dict[str, Any]], start_date: str, end_date: str, travel_length: int
) -> None:
    """Align stop days to the requested trip length and recompute dates."""
    if len(plan) < 2:
        return

    stops = plan[:-1]
    if not stops:
        return

    current_total = sum(max(1, int(stop.get("days") or 1)) for stop in stops)
    if current_total != int(travel_length):
        delta = int(travel_length) - current_total
        stops[-1]["days"] = max(1, int(stops[-1].get("days") or 1) + delta)

    walker = datetime.strptime(start_date, "%Y-%m-%d")
    for stop in stops:
        days = max(1, int(stop.get("days") or 1))
        stop["days"] = days
        stop["arrivalDate"] = walker.strftime("%Y-%m-%d")
        walker = walker + timedelta(days=days)
        stop["departureDate"] = walker.strftime("%Y-%m-%d")

    plan[-1]["arrivalDate"] = end_date
    plan[-1]["departureDate"] = end_date
    plan[-1]["days"] = 0


def _pick_candidate(candidates: List[dict], strategy: str, has_requested_places: bool) -> dict:
    if has_requested_places:
        return candidates[0]

    window_size = 5 if strategy == "random" else 3
    return random.choice(candidates[: min(window_size, len(candidates))])


def _prefer_next_transport(candidates: List[dict], previous_transport: Optional[str]) -> List[dict]:
    flights = [c for c in candidates if (c.get("transport") or "flight") == "flight"]
    ground = [c for c in candidates if (c.get("transport") or "flight") != "flight"]
    if not flights or not ground:
        return candidates

    ordered = flights + ground[:3]

    seen: set[int] = set()
    out = []
    for candidate in ordered + candidates:
        marker = id(candidate)
        if marker in seen:
            continue
        seen.add(marker)
        out.append(candidate)
    return out


def _requested_candidate_matches(
    candidates: List[dict],
    requested_places: List[str],
    plan: List[Dict[str, Any]],
) -> List[dict]:
    remaining_places = [
        place for place in requested_places if not place_used_in_plan(place, plan)
    ]
    return [
        candidate
        for candidate in candidates
        if any(place_matches_candidate(place, candidate) for place in remaining_places)
    ]


def _merge_requested_with_ranked(requested_matches: List[dict], ranked: List[dict]) -> List[dict]:
    out = []
    seen: set[str] = set()
    for candidate in requested_matches + ranked:
        iata = (candidate.get("iata") or "").strip().upper()
        if not iata or iata in seen:
            continue
        seen.add(iata)
        out.append(candidate)
    return out


def _flight_candidates(candidates: List[dict]) -> List[dict]:
    return [
        candidate
        for candidate in candidates
        if (candidate.get("transport") or "flight") == "flight"
    ]


def _format_candidates(candidates: List[dict]) -> str:
    lines = []
    for candidate in candidates:
        distance = (
            f", {candidate.get('distance_km')} km"
            if candidate.get("distance_km") is not None
            else ""
        )
        lines.append(
            "- "
            f"{candidate.get('city')}, {candidate.get('country') or ''} "
            f"(IATA: {candidate.get('iata')}, "
            f"transport: {candidate.get('transport') or 'flight'}{distance})"
        )
    return "\n".join(lines)


def _parse_json_object(raw: str) -> Optional[dict]:
    text = (raw or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(line for line in lines if not line.strip().startswith("```"))
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _clamp_days(value: Any, remaining_days: int) -> int:
    try:
        days = int(value or 1)
    except (TypeError, ValueError):
        days = 1
    return max(1, min(days, remaining_days))


async def _ask_ai_to_pick_candidate(
    *,
    candidates: List[dict],
    strategy: str,
    current_airport: str,
    current_city_label: str,
    remaining_days: int,
    preferences: List[str],
    plan: List[Dict[str, Any]],
    language: str,
    llm_provider: str,
) -> Optional[Dict[str, Any]]:
    prompt = stepwise_next_stop_prompt(
        strategy=strategy,
        lang_name=language_name(language),
        current_airport=current_airport,
        current_city_label=current_city_label,
        prefs=preferences_line(preferences),
        remaining_days=remaining_days,
        cand_block=_format_candidates(candidates),
        avoid=", ".join(str(stop.get("city") or "") for stop in plan) or "none",
    )
    raw = await call_llm_api(prompt, llm_provider)
    choice = _parse_json_object(raw)
    if not choice:
        return None

    chosen_iata = (choice.get("iata") or "").strip().upper()
    candidate = next(
        (
            item
            for item in candidates
            if (item.get("iata") or "").strip().upper() == chosen_iata
        ),
        None,
    )
    if not candidate:
        return None

    days = _clamp_days(choice.get("days"), remaining_days)
    return {
        "city": candidate["city"],
        "country": candidate.get("country") or "",
        "iata": candidate["iata"],
        "days": days,
        "transportFromPreviousCity": candidate.get("transport") or "flight",
        "activities": choice.get("activities") or ["City walk", "Local sights"],
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
    home_city, home_country = split_place_label(starting_point)
    visited_places = visited_places or []
    forbidden_places = forbidden_places or []

    plan: List[Dict[str, Any]] = []
    current_airport = starting_airport_iata
    cursor = datetime.strptime(start_date, "%Y-%m-%d")
    remaining_days = int(travel_length)
    max_legs = min(24, max(1, remaining_days) + 8)

    db = SessionLocal()
    try:
        for _ in range(max_legs):
            if remaining_days <= 0:
                break

            used_iatas = {
                (stop.get("iata") or "").strip().upper()
                for stop in plan
                if stop.get("iata")
            }
            candidates = await build_candidates(
                db,
                strategy=strategy,
                current_airport=current_airport,
                hub_iata=starting_airport_iata,
                used_iatas=used_iatas,
                visited_places=visited_places,
                forbidden_places=forbidden_places,
            )
            previous_iata = plan[-1].get("direct_flights_queried_from") if plan else None
            candidates = annotate_distances(db, current_airport, candidates)
            requested_matches = []
            if strategy == "visited":
                requested_matches = _requested_candidate_matches(
                    candidates, visited_places, plan
                )
            ranked_candidates = rank_candidates(
                candidates,
                previous_iata=(previous_iata or "").strip().upper() or None,
            )
            candidates = _merge_requested_with_ranked(
                requested_matches, ranked_candidates
            )
            previous_transport = plan[-1].get("transportFromPreviousCity") if plan else None
            if not requested_matches:
                candidates = _prefer_next_transport(candidates, previous_transport)
            elif strategy == "visited":
                candidates = prioritize_requested_places(candidates, visited_places, plan)

            if not candidates:
                break

            requested_flights = _flight_candidates(requested_matches)
            available_flights = _flight_candidates(candidates)
            if requested_flights:
                choice_candidates = requested_flights
            elif requested_matches:
                choice_candidates = requested_matches
            elif available_flights:
                choice_candidates = available_flights
            else:
                choice_candidates = candidates

            current_city_label = (
                f"{plan[-1].get('city')}, {plan[-1].get('country')}"
                if plan
                else starting_point
            )
            choice = await _ask_ai_to_pick_candidate(
                candidates=choice_candidates,
                strategy=strategy,
                current_airport=current_airport,
                current_city_label=current_city_label,
                remaining_days=remaining_days,
                preferences=preferences,
                plan=plan,
                language=language,
                llm_provider=llm_provider,
            )
            if not choice:
                candidate = _pick_candidate(
                    choice_candidates,
                    strategy,
                    has_requested_places=bool(requested_matches),
                )
                choice = {
                    "city": candidate["city"],
                    "country": candidate.get("country") or "",
                    "iata": candidate["iata"],
                    "days": max(1, min(remaining_days, max(1, remaining_days // 2 or 1))),
                    "transportFromPreviousCity": candidate.get("transport") or "flight",
                    "activities": ["City walk", "Local sights"],
                }

            days = _clamp_days(choice.get("days"), remaining_days)
            departure_dt = cursor + timedelta(days=days)
            plan.append(
                {
                    "city": choice["city"],
                    "country": choice.get("country") or "",
                    "iata": choice["iata"],
                    "days": days,
                    "arrivalDate": cursor.strftime("%Y-%m-%d"),
                    "departureDate": departure_dt.strftime("%Y-%m-%d"),
                    "transportFromPreviousCity": choice.get("transportFromPreviousCity") or "flight",
                    "activities": choice.get("activities") or [],
                    "direct_flights_queried_from": current_airport,
                }
            )
            remaining_days -= days
            current_airport = str(choice["iata"])

        if remaining_days > 0 and plan:
            plan[-1]["days"] = int(plan[-1].get("days") or 1) + remaining_days

        return_transport = (
            ground_transport_between_airports(db, plan[-1].get("iata"), starting_airport_iata)
            if plan
            else None
        )
        plan.append(
            {
                "city": home_city,
                "country": home_country,
                "iata": starting_airport_iata,
                "days": 0,
                "arrivalDate": end_date,
                "departureDate": end_date,
                "transportFromPreviousCity": return_transport or "flight",
                "activities": [],
                "direct_flights_queried_from": plan[-1].get("iata") if plan else None,
            }
        )
    finally:
        db.close()

    _finalize_segment_days_and_dates(plan, start_date, end_date, travel_length)

    requested_missing = []
    if strategy == "visited":
        requested_missing = [
            place for place in visited_places if not place_used_in_plan(place, plan)
        ]

    return {
        "startingPoint": starting_point,
        "startDate": start_date,
        "endDate": end_date,
        "tripLengthDays": travel_length,
        "strategy": strategy,
        "plan": plan,
        "requestedPlacesMissing": requested_missing,
    }
