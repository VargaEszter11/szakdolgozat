"""Build itineraries leg-by-leg from validated local route candidates."""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from database.database import SessionLocal

from .place_matching import place_used_in_plan, prioritize_requested_places, split_place_label
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

    preferred = flights if previous_transport != "flight" else ground
    first = preferred[0]
    return [first] + [c for c in candidates if c is not first]


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
            candidates = rank_candidates(
                annotate_distances(db, current_airport, candidates),
                previous_iata=(previous_iata or "").strip().upper() or None,
            )
            previous_transport = plan[-1].get("transportFromPreviousCity") if plan else None
            candidates = _prefer_next_transport(candidates, previous_transport)
            if strategy == "visited":
                candidates = prioritize_requested_places(candidates, visited_places, plan)

            if not candidates:
                break

            candidate = _pick_candidate(
                candidates,
                strategy,
                has_requested_places=strategy == "visited" and bool(visited_places),
            )
            days = max(1, min(remaining_days, max(1, remaining_days // 2 or 1)))
            departure_dt = cursor + timedelta(days=days)
            plan.append(
                {
                    "city": candidate["city"],
                    "country": candidate.get("country") or "",
                    "iata": candidate["iata"],
                    "days": days,
                    "arrivalDate": cursor.strftime("%Y-%m-%d"),
                    "departureDate": departure_dt.strftime("%Y-%m-%d"),
                    "transportFromPreviousCity": candidate.get("transport") or "flight",
                    "activities": ["City walk", "Local sights"],
                    "direct_flights_queried_from": current_airport,
                }
            )
            remaining_days -= days
            current_airport = str(candidate["iata"])

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
