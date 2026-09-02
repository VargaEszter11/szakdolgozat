"""Stop-by-stop itinerary builder backed by DB routes and an LLM picker.

Each leg: load candidates from ``direct_routes`` (+ ground/ferry/off-airport
access), ask the LLM to pick one (or fall back to heuristics), append a stop,
then move the cursor airport forward. Ends with an optional return-home leg.
"""
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
    return_flight_booking_details,
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
from .place_access import (
    candidates_for_unmatched_places,
    remaining_unmatched_places,
    resolve_home_hub_transfer,
    resolve_place_access,
)
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

    has_return = bool(plan[-1].get("is_return_home")) or int(plan[-1].get("days") or 0) == 0
    stops = plan[:-1] if has_return else plan
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

    if has_return:
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
    """Candidates that satisfy a not-yet-visited requested place.

    Copies the matching place string onto ``requested_place`` so downstream
    city normalization and accommodation search use the user's label.
    """
    remaining_places = [        place for place in requested_places if not place_used_in_plan(place, plan)
    ]
    matches: List[dict] = []
    for candidate in candidates:
        for place in remaining_places:
            if place_matches_candidate(place, candidate):
                enriched = dict(candidate)
                if not enriched.get("requested_place"):
                    enriched["requested_place"] = place
                matches.append(enriched)
                break
    return matches


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
    matching = [
        item
        for item in candidates
        if (item.get("iata") or "").strip().upper() == chosen_iata
    ]
    candidate = next(
        (item for item in matching if item.get("ground_transfer") or item.get("off_airport")),
        matching[0] if matching else None,
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
        "requested_place": candidate.get("requested_place"),
        "off_airport": candidate.get("off_airport"),
        "ground_transfer": candidate.get("ground_transfer"),
        "via_place_access": candidate.get("via_place_access"),
    }


def _used_iatas(plan: List[Dict[str, Any]]) -> set[str]:
    return {
        (stop.get("iata") or "").strip().upper()
        for stop in plan
        if stop.get("iata") and not stop.get("off_airport") and not stop.get("is_ground_transfer")
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
    language: str = "en",
    place_access_cache: Optional[Dict[str, Any]] = None,
) -> tuple[List[dict], List[dict]]:
    """Candidates for the next leg from ``current_airport``.

    Visited mode also geocodes unmatched typed places and may inject
    via-airport + ground-transfer options (e.g. Trogir via SPU).
    """
    candidates = await build_candidates(        db,
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
        unmatched = remaining_unmatched_places(requested_places, plan, candidates)
        resolutions = []
        for place in unmatched:
            resolution = await resolve_place_access(
                db,
                place,
                current_airport=current_airport,
                preferred_transport=preferred_transport,
                language=language,
                cache=place_access_cache,
            )
            if resolution:
                resolutions.append(resolution)

        reachable = {
            (item.get("iata") or "").strip().upper()
            for item in candidates
            if item.get("iata")
        }
        access_candidates = candidates_for_unmatched_places(
            resolutions,
            reachable_iatas=reachable,
            current_airport=current_airport,
        )
        if access_candidates:
            # Prefer existing route metadata (airline etc.) when injecting via-airport hubs.
            enriched = []
            for access in access_candidates:
                if access.get("off_airport"):
                    enriched.append(access)
                    continue
                access_iata = (access.get("iata") or "").strip().upper()
                base = next(
                    (
                        item
                        for item in candidates
                        if (item.get("iata") or "").strip().upper() == access_iata
                    ),
                    None,
                )
                if base:
                    merged = dict(base)
                    merged.update(
                        {
                            "requested_place": access.get("requested_place"),
                            "via_place_access": True,
                            "ground_transfer": access.get("ground_transfer"),
                        }
                    )
                    if (merged.get("transport") or "flight") == "flight" or not merged.get("transport"):
                        merged["transport"] = base.get("transport") or "flight"
                    enriched.append(merged)
                else:
                    enriched.append(access)
            requested_matches = _merge_requested_with_ranked(requested_matches, enriched)
            candidates = _merge_requested_with_ranked(enriched, candidates)

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
        "requested_place": candidate.get("requested_place"),
        "off_airport": candidate.get("off_airport"),
        "ground_transfer": candidate.get("ground_transfer"),
        "via_place_access": candidate.get("via_place_access"),
    }


def _stop_from_choice(
    db,
    *,
    choice: Dict[str, Any],
    current_airport: str,
    cursor: datetime,
    remaining_days: int,
) -> Optional[Dict[str, Any]]:
    """Build one plan stop from an LLM/heuristic choice.

    Returns None when a flight leg has no bookable direct route in the DB
    (caller skips the leg and may stop building).
    """
    days = _clamp_days(choice.get("days"), remaining_days)
    departure_date = cursor.strftime("%Y-%m-%d")
    booking_details = {}
    transport = choice.get("transportFromPreviousCity") or "flight"
    if transport == "flight":
        booking_details = flight_booking_details(
            db,
            current_airport,
            choice["iata"],
            departure_date,
            choice.get("airline_iata"),
        )
        if not booking_details:
            return None

    stop = {
        "city": choice["city"],
        "country": choice.get("country") or "",
        "iata": choice["iata"],
        "days": days,
        "arrivalDate": cursor.strftime("%Y-%m-%d"),
        "departureDate": (cursor + timedelta(days=days)).strftime("%Y-%m-%d"),
        "transportFromPreviousCity": transport,
        "activities": choice.get("activities") or [],
        "is_seasonal_route": choice.get("is_seasonal_route"),
        "seasonality_status": choice.get("seasonality_status"),
        "effective_from": choice.get("effective_from"),
        "effective_to": choice.get("effective_to"),
        "direct_flights_queried_from": current_airport,
        **booking_details,
    }
    if choice.get("requested_place"):
        stop["requested_place"] = choice["requested_place"]
    if choice.get("off_airport"):
        stop["off_airport"] = True
    if choice.get("access_city"):
        stop["access_city"] = choice["access_city"]
    if choice.get("local_transport"):
        stop["local_transport"] = choice["local_transport"]
    return stop


def _annotate_departure_home_transfer(
    plan: List[Dict[str, Any]],
    *,
    home_city: str,
    home_transfer: Optional[Dict[str, Any]],
) -> None:
    if not plan or not home_transfer or not home_transfer.get("access_city"):
        return
    first = plan[0]
    if first.get("is_return_home"):
        return
    first["departure_from_city"] = (home_city or "").strip().title() or home_city
    first["departure_access_city"] = home_transfer.get("access_city")
    first["departure_local_transport"] = home_transfer.get("local_transport") or "bus"


def _append_return_home(
    db,
    *,
    plan: List[Dict[str, Any]],
    starting_airport_iata: str,
    home_city: str,
    home_country: str,
    end_date: str,
    preferred_transport: str = "allModes",
    home_transfer: Optional[Dict[str, Any]] = None,
) -> None:
    if not plan:
        return

    return_origin = str(plan[-1].get("iata") or "").strip().upper()
    home_hub = str(starting_airport_iata or "").strip().upper()
    allowed_modes = _allowed_transport_modes(preferred_transport)
    return_transport = None
    return_flight_details: Dict[str, Any] = {}
    same_hub = bool(return_origin and home_hub and return_origin == home_hub)
    # Off-airport homes (e.g. Miskolc ↔ Kosice): prefer keeping the return as a
    # flight into the hub even when the reverse DirectRoute is missing/out of season.
    has_ground_home_transfer = bool(home_transfer and home_transfer.get("access_city"))
    prefer_soft_flight = has_ground_home_transfer and not same_hub

    if allowed_modes is None or "flight" in allowed_modes:
        return_flight_details = (
            return_flight_booking_details(
                db,
                return_origin,
                home_hub,
                end_date,
                allow_unverified=prefer_soft_flight,
            )
            if return_origin and home_hub
            else {}
        )
        if return_flight_details:
            return_transport = "flight"

    if (
        return_transport is None
        and (allowed_modes is None or {"train", "bus"} & allowed_modes)
    ):
        ground_transport = ground_transport_between_airports(
            db, return_origin, home_hub
        )
        if ground_transport and (allowed_modes is None or ground_transport in allowed_modes):
            return_transport = ground_transport

    if return_transport is None and (allowed_modes is None or "ferry" in allowed_modes):
        ferry_transport = ferry_transport_between_airports(
            db, return_origin, home_hub
        )
        if ferry_transport:
            return_transport = ferry_transport

    # Last resort for off-airport homes: still show a flight+transfer home instead of
    # dropping the return leg when no dated reverse route and no ground option exist.
    if (
        return_transport is None
        and prefer_soft_flight
        and (allowed_modes is None or "flight" in allowed_modes)
        and return_origin
        and home_hub
    ):
        return_flight_details = return_flight_booking_details(
            db,
            return_origin,
            home_hub,
            end_date,
            allow_unverified=True,
        )
        if return_flight_details:
            return_transport = "flight"

    if return_transport is None:
        return

    last_city = (plan[-1].get("city") or "").strip().lower()
    home_label = (home_city or "").strip()
    if last_city and home_label and last_city == home_label.lower():
        # Already at the starting place (e.g. last stop is home).
        return

    from database import models
    from utils.countries import resolve_country_code

    resolved_country = resolve_country_code(home_country) or ""
    if not resolved_country and home_transfer:
        resolved_country = (
            resolve_country_code(home_transfer.get("home_country"))
            or ""
        )
    # Hub country is only safe when home is at/near that airport. Off-airport
    # homes (ground transfer) may sit in a different country than the hub.
    if not resolved_country and home_hub and not has_ground_home_transfer:
        ap = (
            db.query(models.Airport)
            .filter(models.Airport.iata == home_hub)
            .first()
        )
        raw_code = getattr(ap, "country_code", None) if ap is not None else None
        if isinstance(raw_code, str):
            resolved_country = resolve_country_code(raw_code) or raw_code.strip().upper()

    return_stop: Dict[str, Any] = {
        "city": home_label.title() if home_label else home_city,
        "country": resolved_country or (home_country or ""),
        "iata": home_hub,
        "days": 0,
        "arrivalDate": end_date,
        "departureDate": end_date,
        "transportFromPreviousCity": return_transport,
        "activities": [],
        "is_return_home": True,
        "direct_flights_queried_from": plan[-1].get("iata"),
        **return_flight_details,
    }
    last_stop = plan[-1]
    # Mirror destination access: get from last place to its hub before the main return leg.
    if return_transport in {"flight", "ferry"}:
        last_access = (last_stop.get("access_city") or "").strip()
        last_local = (last_stop.get("local_transport") or "").strip()
        if last_access and last_local:
            return_stop["departure_access_city"] = last_access
            return_stop["departure_local_transport"] = last_local
            return_stop["departure_from_city"] = (last_stop.get("city") or "").strip()
    if home_transfer:
        access_city = (home_transfer.get("access_city") or "").strip()
        local = home_transfer.get("local_transport") or "bus"
        if access_city:
            if return_transport in {"flight", "ferry"}:
                # Same pattern as destination access: fly/ferry to hub, then ground home.
                return_stop["access_city"] = access_city
                return_stop["local_transport"] = local
            elif same_hub:
                # Already at the hub — main leg is the local transfer home.
                return_stop["access_city"] = access_city
            else:
                # Ground between different hubs, then local transfer home.
                return_stop["access_city"] = access_city
                return_stop["local_transport"] = local
    plan.append(return_stop)


def _missing_requested_places(
    *,
    strategy: str,
    requested_places: List[str],
    plan: List[Dict[str, Any]],
) -> List[str]:
    if strategy != "visited" or not requested_places:
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
    """Main itinerary loop: hub → next stop → … → return home."""
    home_city, home_country = split_place_label(starting_point)
    from utils.countries import resolve_country_code

    home_country = resolve_country_code(home_country) or (home_country or "")
    requested_places = _merge_place_lists(visited_places, extra_places)
    visited_places = requested_places
    forbidden_places = forbidden_places or []
    extra_places = extra_places or []

    plan: List[Dict[str, Any]] = []
    current_airport = starting_airport_iata
    cursor = datetime.strptime(start_date, "%Y-%m-%d")
    remaining_days = int(travel_length)
    max_legs = min(24, max(1, remaining_days) + 8)
    place_access_cache: Dict[str, Any] = {}

    db = SessionLocal()
    try:
        home_transfer = await resolve_home_hub_transfer(
            db,
            starting_point,
            starting_airport_iata=starting_airport_iata,
            preferred_transport=preferred_transport,
            language=language,
        )
        if not home_country and home_transfer and home_transfer.get("home_country"):
            home_country = str(home_transfer.get("home_country") or "").strip()
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
                language=language,
                place_access_cache=place_access_cache,
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

            stop = None
            if choice.get("ground_transfer"):
                # Fly/bus to hub, then ground leg to the typed place (off-airport visit).
                transfer = dict(choice["ground_transfer"])
                place_choice = {
                    "city": transfer.get("city") or choice.get("city"),
                    "country": transfer.get("country") or choice.get("country") or "",
                    "iata": transfer.get("iata") or choice.get("iata"),
                    "days": choice.get("days"),
                    "transportFromPreviousCity": choice.get("transportFromPreviousCity")
                    or "flight",
                    "activities": choice.get("activities") or ["City walk", "Local sights"],
                    "airline_iata": choice.get("airline_iata"),
                    "airline_name": choice.get("airline_name"),
                    "is_seasonal_route": choice.get("is_seasonal_route"),
                    "seasonality_status": choice.get("seasonality_status"),
                    "effective_from": choice.get("effective_from"),
                    "effective_to": choice.get("effective_to"),
                    "requested_place": transfer.get("requested_place")
                    or choice.get("requested_place"),
                    "off_airport": True,
                    "access_city": choice.get("city"),
                    "local_transport": transfer.get("transport") or "bus",
                }
                stop = _stop_from_choice(
                    db,
                    choice=place_choice,
                    current_airport=current_airport,
                    cursor=cursor,
                    remaining_days=remaining_days,
                )
            else:
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
            cursor = datetime.strptime(stop["departureDate"], "%Y-%m-%d")
            current_airport = str(stop["iata"])

        if remaining_days > 0 and plan:
            for item in reversed(plan):
                if int(item.get("days") or 0) <= 0:
                    continue
                item["days"] = int(item.get("days") or 1) + remaining_days
                break

        _annotate_departure_home_transfer(
            plan,
            home_city=home_city,
            home_transfer=home_transfer,
        )
        _append_return_home(
            db,
            plan=plan,
            starting_airport_iata=starting_airport_iata,
            home_city=home_city,
            home_country=home_country,
            end_date=end_date,
            preferred_transport=preferred_transport,
            home_transfer=home_transfer,
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
