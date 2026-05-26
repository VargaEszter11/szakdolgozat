"""Build itineraries leg-by-leg from validated local route candidates."""

from __future__ import annotations

import json
import random
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from database import models
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


def _seasonality_status(is_seasonal: Optional[bool]) -> str:
    if is_seasonal is True:
        return "seasonal"
    if is_seasonal is False:
        return "year_round"
    return "unknown"


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
            f"seasonality: {_seasonality_status(candidate.get('is_seasonal'))}, "
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


def _booking_url(airline_iata: Optional[str], origin: str, destination: str, date: str) -> Optional[str]:
    airline = (airline_iata or "").strip().upper()
    origin = (origin or "").strip().upper()
    destination = (destination or "").strip().upper()
    if not airline or not origin or not destination or not date:
        return None

    if airline == "FR":
        return (
            "https://www.ryanair.com/gb/en/trip/flights/select"
            f"?adults=1&teens=0&children=0&infants=0&dateOut={date}"
            f"&originIata={origin}&destinationIata={destination}"
            "&isConnectedFlight=false&discount=0&promoCode="
        )
    if airline == "W6":
        return (
            "https://wizzair.com/en-gb/booking/select-flight/"
            f"{origin}/{destination}/{date}/null/1/0/0/null"
        )
    if airline == "KL":
        return (
            "https://www.klm.com/search/offers"
            f"?origin={origin}&destination={destination}&departureDate={date}"
        )
    if airline == "LH":
        return (
            "https://www.lufthansa.com/xx/en/flight-search"
            f"?origin={origin}&destination={destination}&departureDate={date}"
        )
    return None


def _direct_route_for_leg(db, origin: str, destination: str, airline_iata: Optional[str] = None):
    query = (
        db.query(models.DirectRoute)
        .filter(
            models.DirectRoute.origin_iata == (origin or "").strip().upper(),
            models.DirectRoute.destination_iata == (destination or "").strip().upper(),
            models.DirectRoute.is_active.is_(True),
        )
    )
    airline = (airline_iata or "").strip().upper()
    if airline:
        query = query.filter(models.DirectRoute.airline_iata == airline)
    return query.order_by(models.DirectRoute.airline_iata.is_(None), models.DirectRoute.airline_iata).first()


def _route_operates_on_date(route, departure_date: str) -> bool:
    if not route:
        return False
    try:
        parsed_date = date.fromisoformat(departure_date)
    except (TypeError, ValueError):
        return False

    if route.effective_from and parsed_date < route.effective_from:
        return False
    if route.effective_to and parsed_date > route.effective_to:
        return False

    operating_days = list(route.operating_days or [])
    if not operating_days:
        return True

    return any(day.weekday == parsed_date.isoweekday() for day in operating_days)


def _route_availability_verified(route) -> bool:
    return bool(route and list(route.operating_days or []))


def _flight_available_on_date(
    db,
    origin: str,
    destination: str,
    departure_date: str,
    airline_iata: Optional[str] = None,
) -> bool:
    route = _direct_route_for_leg(db, origin, destination, airline_iata)
    return _route_operates_on_date(route, departure_date)


def _available_flight_candidates(
    db,
    origin: str,
    candidates: List[dict],
    departure_date: str,
) -> List[dict]:
    return [
        candidate
        for candidate in _flight_candidates(candidates)
        if _flight_available_on_date(
            db,
            origin,
            candidate.get("iata"),
            departure_date,
            candidate.get("airline_iata"),
        )
    ]


def _flight_booking_details(
    db,
    origin: str,
    destination: str,
    departure_date: str,
    airline_iata: Optional[str] = None,
) -> dict:
    route = _direct_route_for_leg(db, origin, destination, airline_iata)
    if not _route_operates_on_date(route, departure_date):
        return {}
    if not route:
        return {}

    return {
        "origin_airport_iata": route.origin_iata,
        "destination_airport_iata": route.destination_iata,
        "airline_iata": route.airline_iata,
        "airline_name": route.airline_name,
        "is_seasonal_route": route.is_seasonal,
        "seasonality_status": _seasonality_status(route.is_seasonal),
        "effective_from": route.effective_from.isoformat() if route.effective_from else None,
        "effective_to": route.effective_to.isoformat() if route.effective_to else None,
        "booking_url": _booking_url(
            route.airline_iata,
            route.origin_iata,
            route.destination_iata,
            departure_date,
        ),
        "flight_availability_verified": _route_availability_verified(route),
    }


def _clear_booking_details(stop: Dict[str, Any]) -> None:
    for key in (
        "origin_airport_iata",
        "destination_airport_iata",
        "airline_iata",
        "airline_name",
        "booking_url",
        "flight_availability_verified",
    ):
        stop.pop(key, None)


def _refresh_booking_details(
    db,
    plan: List[Dict[str, Any]],
    starting_airport_iata: str,
) -> None:
    previous_iata = starting_airport_iata
    for stop in plan:
        selected_airline_iata = stop.get("airline_iata")
        _clear_booking_details(stop)
        transport = (stop.get("transportFromPreviousCity") or "").strip().lower()
        destination_iata = (stop.get("iata") or "").strip().upper()
        travel_date = stop.get("arrivalDate")

        if transport == "flight" and previous_iata and destination_iata and travel_date:
            stop.update(
                _flight_booking_details(
                    db,
                    previous_iata,
                    destination_iata,
                    travel_date,
                    selected_airline_iata,
                )
            )

        if destination_iata:
            previous_iata = destination_iata


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
        min_stop_days=_minimum_stop_days(remaining_days),
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
        "airline_iata": candidate.get("airline_iata"),
        "airline_name": candidate.get("airline_name"),
        "is_seasonal_route": candidate.get("is_seasonal"),
        "seasonality_status": _seasonality_status(candidate.get("is_seasonal")),
        "effective_from": candidate.get("effective_from"),
        "effective_to": candidate.get("effective_to"),
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

            departure_date = cursor.strftime("%Y-%m-%d")
            requested_flights = _available_flight_candidates(
                db, current_airport, requested_matches, departure_date
            )
            available_flights = _available_flight_candidates(
                db, current_airport, candidates, departure_date
            )
            if requested_flights:
                choice_candidates = requested_flights
            elif requested_matches:
                choice_candidates = [
                    candidate
                    for candidate in requested_matches
                    if (candidate.get("transport") or "flight") != "flight"
                ]
            elif available_flights:
                choice_candidates = available_flights
            else:
                choice_candidates = [
                    candidate
                    for candidate in candidates
                    if (candidate.get("transport") or "flight") != "flight"
                ]

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
                    "days": _clamp_days(max(2, remaining_days // 2 or 1), remaining_days),
                    "transportFromPreviousCity": candidate.get("transport") or "flight",
                    "activities": ["City walk", "Local sights"],
                    "airline_iata": candidate.get("airline_iata"),
                    "airline_name": candidate.get("airline_name"),
                    "is_seasonal_route": candidate.get("is_seasonal"),
                    "seasonality_status": _seasonality_status(candidate.get("is_seasonal")),
                    "effective_from": candidate.get("effective_from"),
                    "effective_to": candidate.get("effective_to"),
                }

            days = _clamp_days(choice.get("days"), remaining_days)
            departure_dt = cursor + timedelta(days=days)
            booking_details = {}
            if (choice.get("transportFromPreviousCity") or "flight") == "flight":
                booking_details = _flight_booking_details(
                    db,
                    current_airport,
                    choice["iata"],
                    departure_date,
                    choice.get("airline_iata"),
                )
                if not booking_details:
                    break
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
                    "is_seasonal_route": choice.get("is_seasonal_route"),
                    "seasonality_status": choice.get("seasonality_status"),
                    "effective_from": choice.get("effective_from"),
                    "effective_to": choice.get("effective_to"),
                    "direct_flights_queried_from": current_airport,
                    **booking_details,
                }
            )
            remaining_days -= days
            current_airport = str(choice["iata"])

        if remaining_days > 0 and plan:
            plan[-1]["days"] = int(plan[-1].get("days") or 1) + remaining_days

        if plan:
            return_origin = plan[-1].get("iata")
            return_date = end_date
            return_flight_details = (
                _flight_booking_details(db, return_origin, starting_airport_iata, return_date)
                if return_origin
                else {}
            )
            return_transport = ground_transport_between_airports(
                db, plan[-1].get("iata"), starting_airport_iata
            )
            if return_flight_details:
                return_transport = "flight"
            return_booking_details = return_flight_details
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
                    "direct_flights_queried_from": plan[-1].get("iata"),
                    **return_booking_details,
                }
            )
    finally:
        db.close()

    _finalize_segment_days_and_dates(plan, start_date, end_date, travel_length)
    db = SessionLocal()
    try:
        _refresh_booking_details(db, plan, starting_airport_iata)
    finally:
        db.close()

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
