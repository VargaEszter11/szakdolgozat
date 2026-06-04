from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from database.database import SessionLocal

from .booking import (
    available_flight_candidates,
    flight_booking_details,
    refresh_booking_details,
    seasonality_status,
)
from .llm_client import call_llm_api
from .place_matching import (
    place_matches_candidate,
    place_used_in_plan,
    prioritize_requested_places,
    split_place_label,
)
from .common import language_name, next_stop_prompt, preferences_line
from .route_candidates import (
    annotate_distances,
    build_candidates,
    ferry_transport_between_airports,
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


def _minimum_stop_days(remaining_days: int) -> int:
    return 2 if remaining_days >= 2 else 1


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


def _allowed_transport_modes(preferred_transport: str) -> Optional[set[str]]:
    preference = (preferred_transport or "allModes").strip()
    if preference == "flight":
        return {"flight"}
    if preference == "trainBus":
        return {"train", "bus"}
    if preference == "trainBusFerry":
        return {"train", "bus", "ferry"}
    return None


def _filter_by_preferred_transport(
    candidates: List[dict],
    preferred_transport: str,
) -> List[dict]:
    allowed = _allowed_transport_modes(preferred_transport)
    if allowed is None:
        return candidates
    return [
        candidate
        for candidate in candidates
        if (candidate.get("transport") or "flight") in allowed
    ]


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


def _merge_place_lists(*groups: Optional[List[str]]) -> List[str]:
    seen = set()
    out: List[str] = []
    for group in groups:
        for place in group or []:
            text = str(place).strip()
            if not text:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(text)
    return out


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


def _format_candidates(candidates: List[dict]) -> str:
    lines = []
    for candidate in candidates:
        distance = (
            f", {candidate.get('distance_km')} km"
            if candidate.get("distance_km") is not None
            else ""
        )
        effective_from = candidate.get("effective_from") or "unknown"
        effective_to = candidate.get("effective_to") or "unknown"
        lines.append(
            "- "
            f"{candidate.get('city')}, {candidate.get('country') or ''} "
            f"(IATA: {candidate.get('iata')}, "
            f"transport: {candidate.get('transport') or 'flight'}, "
            f"airline: {candidate.get('airline_iata') or 'n/a'}, "
            f"seasonality: {seasonality_status(candidate.get('is_seasonal'))}, "
            f"effective: {effective_from} to {effective_to}{distance})"
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
    minimum_days = _minimum_stop_days(remaining_days)
    days = max(minimum_days, min(days, remaining_days))
    leftover_days = remaining_days - days
    if 0 < leftover_days < minimum_days:
        return remaining_days
    return days


async def _ask_ai_to_pick_candidate(
    *,
    candidates: List[dict],
    strategy: str,
    current_airport: str,
    current_city_label: str,
    remaining_days: int,
    preferences: List[str],
    plan: List[Dict[str, Any]],
    requested_places: List[str],
    forbidden_places: List[str],
    extra_places: List[str],
    preferred_transport: str,
    language: str,
    llm_provider: str,
) -> Optional[Dict[str, Any]]:
    prompt = next_stop_prompt(
        strategy=strategy,
        lang_name=language_name(language),
        current_airport=current_airport,
        current_city_label=current_city_label,
        prefs=preferences_line(preferences),
        remaining_days=remaining_days,
        min_stop_days=_minimum_stop_days(remaining_days),
        cand_block=_format_candidates(candidates),
        avoid=", ".join(str(stop.get("city") or "") for stop in plan) or "none",
        requested_places=requested_places,
        forbidden_places=forbidden_places,
        extra_places=extra_places,
        preferred_transport=preferred_transport,
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
        "airline_iata": candidate.get("airline_iata"),
        "airline_name": candidate.get("airline_name"),
        "is_seasonal_route": candidate.get("is_seasonal"),
        "seasonality_status": seasonality_status(candidate.get("is_seasonal")),
        "effective_from": candidate.get("effective_from"),
        "effective_to": candidate.get("effective_to"),
    }


def _used_iatas(plan: List[Dict[str, Any]]) -> set[str]:
    return {
        (stop.get("iata") or "").strip().upper()
        for stop in plan
        if stop.get("iata")
    }


async def _ranked_step_candidates(
    db,
    *,
    strategy: str,
    current_airport: str,
    starting_airport_iata: str,
    plan: List[Dict[str, Any]],
    requested_places: List[str],
    forbidden_places: List[str],
    preferred_transport: str = "allModes",
) -> tuple[List[dict], List[dict]]:
    candidates = await build_candidates(
        db,
        strategy=strategy,
        current_airport=current_airport,
        hub_iata=starting_airport_iata,
        used_iatas=_used_iatas(plan),
        visited_places=requested_places,
        forbidden_places=forbidden_places,
        preferred_transport=preferred_transport,
    )
    candidates = annotate_distances(db, current_airport, candidates)

    requested_matches = []
    if strategy == "visited":
        requested_matches = _requested_candidate_matches(candidates, requested_places, plan)
        if not requested_matches:
            return [], []

    previous_iata = plan[-1].get("direct_flights_queried_from") if plan else None
    ranked = rank_candidates(
        candidates,
        previous_iata=(previous_iata or "").strip().upper() or None,
    )
    candidates = _merge_requested_with_ranked(requested_matches, ranked)

    if strategy == "visited":
        candidates = prioritize_requested_places(candidates, requested_places, plan)
    else:
        previous_transport = plan[-1].get("transportFromPreviousCity") if plan else None
        candidates = _prefer_next_transport(candidates, previous_transport)

    return candidates, requested_matches


def _candidate_choices_for_date(
    db,
    *,
    current_airport: str,
    candidates: List[dict],
    requested_matches: List[dict],
    departure_date: str,
) -> List[dict]:
    requested_flights = available_flight_candidates(
        db, current_airport, requested_matches, departure_date
    )
    available_flights = available_flight_candidates(
        db, current_airport, candidates, departure_date
    )
    if requested_flights:
        return requested_flights
    if requested_matches:
        return [
            candidate
            for candidate in requested_matches
            if (candidate.get("transport") or "flight") != "flight"
        ]
    if available_flights:
        return available_flights
    return [
        candidate
        for candidate in candidates
        if (candidate.get("transport") or "flight") != "flight"
    ]


def _fallback_choice(
    candidates: List[dict],
    *,
    strategy: str,
    remaining_days: int,
    has_requested_places: bool,
) -> Dict[str, Any]:
    candidate = _pick_candidate(
        candidates,
        strategy,
        has_requested_places=has_requested_places,
    )
    return {
        "city": candidate["city"],
        "country": candidate.get("country") or "",
        "iata": candidate["iata"],
        "days": _clamp_days(max(2, remaining_days // 2 or 1), remaining_days),
        "transportFromPreviousCity": candidate.get("transport") or "flight",
        "activities": ["City walk", "Local sights"],
        "airline_iata": candidate.get("airline_iata"),
        "airline_name": candidate.get("airline_name"),
        "is_seasonal_route": candidate.get("is_seasonal"),
        "seasonality_status": seasonality_status(candidate.get("is_seasonal")),
        "effective_from": candidate.get("effective_from"),
        "effective_to": candidate.get("effective_to"),
    }


def _stop_from_choice(
    db,
    *,
    choice: Dict[str, Any],
    current_airport: str,
    cursor: datetime,
    remaining_days: int,
) -> Optional[Dict[str, Any]]:
    days = _clamp_days(choice.get("days"), remaining_days)
    departure_date = cursor.strftime("%Y-%m-%d")
    booking_details = {}
    if (choice.get("transportFromPreviousCity") or "flight") == "flight":
        booking_details = flight_booking_details(
            db,
            current_airport,
            choice["iata"],
            departure_date,
            choice.get("airline_iata"),
        )
        if not booking_details:
            return None

    return {
        "city": choice["city"],
        "country": choice.get("country") or "",
        "iata": choice["iata"],
        "days": days,
        "arrivalDate": cursor.strftime("%Y-%m-%d"),
        "departureDate": (cursor + timedelta(days=days)).strftime("%Y-%m-%d"),
        "transportFromPreviousCity": choice.get("transportFromPreviousCity") or "flight",
        "activities": choice.get("activities") or [],
        "is_seasonal_route": choice.get("is_seasonal_route"),
        "seasonality_status": choice.get("seasonality_status"),
        "effective_from": choice.get("effective_from"),
        "effective_to": choice.get("effective_to"),
        "direct_flights_queried_from": current_airport,
        **booking_details,
    }


def _append_return_home(
    db,
    *,
    plan: List[Dict[str, Any]],
    starting_airport_iata: str,
    home_city: str,
    home_country: str,
    end_date: str,
    preferred_transport: str = "allModes",
) -> None:
    if not plan:
        return

    return_origin = plan[-1].get("iata")
    allowed_modes = _allowed_transport_modes(preferred_transport)
    return_transport = None
    return_flight_details = {}

    if allowed_modes is None or "flight" in allowed_modes:
        return_flight_details = (
            flight_booking_details(db, return_origin, starting_airport_iata, end_date)
            if return_origin
            else {}
        )
        if return_flight_details:
            return_transport = "flight"

    if return_transport is None and (allowed_modes is None or {"train", "bus"} & allowed_modes):
        ground_transport = ground_transport_between_airports(
            db, plan[-1].get("iata"), starting_airport_iata
        )
        if ground_transport and (allowed_modes is None or ground_transport in allowed_modes):
            return_transport = ground_transport

    if return_transport is None and (allowed_modes is None or "ferry" in allowed_modes):
        ferry_transport = ferry_transport_between_airports(
            db, plan[-1].get("iata"), starting_airport_iata
        )
        if ferry_transport:
            return_transport = ferry_transport

    if return_transport is None:
        return

    plan.append(
        {
            "city": home_city,
            "country": home_country,
            "iata": starting_airport_iata,
            "days": 0,
            "arrivalDate": end_date,
            "departureDate": end_date,
            "transportFromPreviousCity": return_transport,
            "activities": [],
            "direct_flights_queried_from": plan[-1].get("iata"),
            **return_flight_details,
        }
    )


def _missing_requested_places(
    *,
    strategy: str,
    requested_places: List[str],
    plan: List[Dict[str, Any]],
) -> List[str]:
    if strategy != "visited" or not requested_places:
        return []
    if any(place_used_in_plan(place, plan) for place in requested_places):
        return []
    return [
        place for place in requested_places if not place_used_in_plan(place, plan)
    ]


async def build_plan(
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
    extra_places: Optional[List[str]] = None,
    preferred_transport: str = "allModes",
) -> Dict[str, Any]:
    home_city, home_country = split_place_label(starting_point)
    requested_places = _merge_place_lists(visited_places, extra_places)
    visited_places = requested_places
    forbidden_places = forbidden_places or []
    extra_places = extra_places or []

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

            candidates, requested_matches = await _ranked_step_candidates(
                db,
                strategy=strategy,
                current_airport=current_airport,
                starting_airport_iata=starting_airport_iata,
                plan=plan,
                requested_places=requested_places,
                forbidden_places=forbidden_places,
                preferred_transport=preferred_transport,
            )
            if not candidates:
                break
            candidates = _filter_by_preferred_transport(candidates, preferred_transport)
            requested_matches = _filter_by_preferred_transport(
                requested_matches,
                preferred_transport,
            )
            if not candidates:
                break

            departure_date = cursor.strftime("%Y-%m-%d")
            choice_candidates = _candidate_choices_for_date(
                db,
                current_airport=current_airport,
                candidates=candidates,
                requested_matches=requested_matches,
                departure_date=departure_date,
            )
            if not choice_candidates:
                break

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
                requested_places=requested_places,
                forbidden_places=forbidden_places,
                extra_places=extra_places,
                preferred_transport=preferred_transport,
                language=language,
                llm_provider=llm_provider,
            )
            if not choice:
                choice = _fallback_choice(
                    choice_candidates,
                    strategy=strategy,
                    remaining_days=remaining_days,
                    has_requested_places=bool(requested_matches),
                )

            stop = _stop_from_choice(
                db,
                choice=choice,
                current_airport=current_airport,
                cursor=cursor,
                remaining_days=remaining_days,
            )
            if not stop:
                break

            plan.append(stop)
            remaining_days -= int(stop["days"])
            current_airport = str(stop["iata"])

        if remaining_days > 0 and plan:
            plan[-1]["days"] = int(plan[-1].get("days") or 1) + remaining_days

        _append_return_home(
            db,
            plan=plan,
            starting_airport_iata=starting_airport_iata,
            home_city=home_city,
            home_country=home_country,
            end_date=end_date,
            preferred_transport=preferred_transport,
        )
    finally:
        db.close()

    _finalize_segment_days_and_dates(plan, start_date, end_date, travel_length)
    db = SessionLocal()
    try:
        refresh_booking_details(db, plan, starting_airport_iata)
    finally:
        db.close()

    return {
        "startingPoint": starting_point,
        "startDate": start_date,
        "endDate": end_date,
        "tripLengthDays": travel_length,
        "strategy": strategy,
        "plan": plan,
        "requestedPlacesMissing": _missing_requested_places(
            strategy=strategy,
            requested_places=requested_places,
            plan=plan,
        ),
    }
