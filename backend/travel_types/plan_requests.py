"""API orchestration for travel plan generation.

Pipeline (``generate_plan_with_location``):
  1. Geocode starting city → nearest airport + direct destinations
  2. Call strategy-specific generator (visited / unvisited / random)
  3. Post-process: normalize city labels, lodging coords, booking URLs

``userId`` on requests is opt-in: the frontend sends it only when the
"use travel log from database" toggle is on.
"""
import asyncio
import json
from datetime import datetime
from typing import Any, List, Optional, cast

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import crud, models
from database.airport_city import airport_name_as_city
from travel_types import (
    UnvisitedGenerationRequest,
    build_unvisited_forbidden_places,
    build_visited_places_from_db,
    generate_travel_plan_random,
    generate_travel_plan_unvisited,
    generate_travel_plan_visited,
    merge_exclusion_lists,
)
from travel_types.booking import booking_url
from utils.coordinates import geocode_city_center, geocode_place
from utils.countries import geocode_country_label
from utils.direct_destinations_cache import get_direct_destinations_cached
from utils.nearest_airport import nearest_airport
from utils.plan_enrichment import normalize_planner_response


class GenerationRequest(BaseModel):
    """Visited mode: include listed places (manual + optional DB travel log)."""
    visitedPlaces: List[str]
    extraPlaces: List[str] = []
    startingPoint: str
    startDate: str
    endDate: str
    people: int = 1
    preferredTransport: str = "allModes"
    preferences: List[str] = []
    likedPlaces: List[str] = []
    dislikedPlaces: List[str] = []
    language: str = "en"
    userId: Optional[int] = None
    plannerUserId: Optional[int] = None


class RandomGenerationRequest(BaseModel):
    startingPoint: str
    startDate: str
    endDate: str
    people: int = 1
    preferredTransport: str = "allModes"
    preferences: List[str] = []
    likedPlaces: List[str] = []
    dislikedPlaces: List[str] = []
    language: str = "en"
    userId: Optional[int] = None
    plannerUserId: Optional[int] = None


class GeocodeRequest(BaseModel):
    places: List[str]
    language: str = "en"


def apply_stop_feedback(
    preferences: List[str],
    liked_places: Optional[List[str]] = None,
    disliked_places: Optional[List[str]] = None,
) -> tuple[List[str], List[str], List[str]]:
    """Split keep / don't-keep feedback into place lists.

    Liked cities are hard keep targets for regenerate (must be included when
    reachable). Disliked cities are excluded from candidates.
    """
    liked = merge_exclusion_lists([], liked_places or [])
    disliked = merge_exclusion_lists([], disliked_places or [])
    disliked_keys = {p.lower() for p in disliked}
    liked = [p for p in liked if p.lower() not in disliked_keys]
    return list(preferences or []), liked, disliked


def places_without_disliked(
    places: List[str], disliked_places: List[str]
) -> List[str]:
    if not disliked_places:
        return list(places or [])
    return [
        place
        for place in (places or [])
        if not any(
            place.lower() == disliked.lower()
            or place.lower().startswith(disliked.split(",")[0].strip().lower() + ",")
            or disliked.lower().startswith(place.split(",")[0].strip().lower() + ",")
            or place.split(",")[0].strip().lower()
            == disliked.split(",")[0].strip().lower()
            for disliked in disliked_places
        )
    ]


async def geocode_places(request: GeocodeRequest) -> list:
    result = []
    for place in request.places:
        if not (place and str(place).strip()):
            result.append(None)
            continue
        try:
            lat, lon = await geocode_place(str(place).strip(), language=request.language)
            result.append({"lat": lat, "lon": lon})
        except Exception:
            result.append(None)
    return result


async def generate_visited_plan(request: GenerationRequest, db: Session) -> dict:
    travel_length, llm_provider = planner_context(request, db)
    preferences, liked_places, disliked_places = apply_stop_feedback(
        request.preferences, request.likedPlaces, request.dislikedPlaces
    )
    # Regenerate with keep/don't-keep: only those two rules, then fill with new places.
    if liked_places or disliked_places:
        return await generate_plan_with_location(
            generate_travel_plan_random,
            request.startingPoint,
            travel_length,
            preferences,
            starting_point=request.startingPoint,
            start_date=request.startDate,
            end_date=request.endDate,
            travel_length=travel_length,
            people=request.people,
            preferredTransport=request.preferredTransport,
            language=request.language,
            llm_provider=llm_provider,
            keep_places=liked_places,
            forbidden_places=disliked_places,
            db=db,
        )

    visited_places = list(request.visitedPlaces)
    if request.userId is not None:
        visited_places = build_visited_places_from_db(
            db, request.userId, request.visitedPlaces
        )
    extra_places = list(request.extraPlaces or [])
    if not merge_exclusion_lists(visited_places, extra_places):
        raise HTTPException(
            status_code=400,
            detail=(
                "Add at least one place, or turn on using your travel log from the database."
            ),
        )
    return await generate_plan_with_location(
        generate_travel_plan_visited,
        request.startingPoint,
        travel_length,
        preferences,
        visited_places,
        starting_point=request.startingPoint,
        start_date=request.startDate,
        end_date=request.endDate,
        travel_length=travel_length,
        people=request.people,
        preferredTransport=request.preferredTransport,
        language=request.language,
        llm_provider=llm_provider,
        extra_places=extra_places,
        db=db,
    )


async def generate_unvisited_plan(request: UnvisitedGenerationRequest, db: Session) -> dict:
    travel_length, llm_provider = planner_context(request, db)
    preferences, liked_places, disliked_places = apply_stop_feedback(
        request.preferences, request.likedPlaces, request.dislikedPlaces
    )
    # Regenerate with keep/don't-keep: include keeps, exclude don't-keeps, add new places.
    if liked_places or disliked_places:
        return await generate_plan_with_location(
            generate_travel_plan_random,
            request.startingPoint,
            travel_length,
            preferences,
            starting_point=request.startingPoint,
            start_date=request.startDate,
            end_date=request.endDate,
            travel_length=travel_length,
            people=request.people,
            preferredTransport=request.preferredTransport,
            language=request.language,
            llm_provider=llm_provider,
            keep_places=liked_places,
            forbidden_places=disliked_places,
            db=db,
        )

    forbidden_places = (
        build_unvisited_forbidden_places(db, request.userId, request.additionalExclusions)
        if request.userId is not None
        else merge_exclusion_lists([], request.additionalExclusions)
    )
    return await generate_plan_with_location(
        generate_travel_plan_unvisited,
        request.startingPoint,
        travel_length,
        preferences,
        forbidden_places,
        starting_point=request.startingPoint,
        start_date=request.startDate,
        end_date=request.endDate,
        travel_length=travel_length,
        people=request.people,
        preferredTransport=request.preferredTransport,
        language=request.language,
        llm_provider=llm_provider,
        db=db,
    )


async def generate_random_plan(request: RandomGenerationRequest, db: Session) -> dict:
    travel_length, llm_provider = planner_context(request, db)
    preferences, liked_places, disliked_places = apply_stop_feedback(
        request.preferences, request.likedPlaces, request.dislikedPlaces
    )
    return await generate_plan_with_location(
        generate_travel_plan_random,
        request.startingPoint,
        travel_length,
        preferences,
        starting_point=request.startingPoint,
        start_date=request.startDate,
        end_date=request.endDate,
        travel_length=travel_length,
        people=request.people,
        preferredTransport=request.preferredTransport,
        language=request.language,
        llm_provider=llm_provider,
        keep_places=liked_places,
        forbidden_places=disliked_places,
        db=db,
    )


def resolve_llm_provider(db: Optional[Session], user_id: Optional[int]) -> str:
    """Always DeepSeek (Coolify / production). DB column is kept but ignored."""
    from travel_types.llm_client import normalize_llm_provider

    return normalize_llm_provider()


def planner_account_id(request) -> Optional[int]:
    pid = getattr(request, "plannerUserId", None)
    return pid if pid is not None else getattr(request, "userId", None)


def travel_length_days(start_date: str, end_date: str) -> int:
    """Number of days between start and end; end must be strictly after start."""
    start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
    today = datetime.now().date()
    if start_dt < today:
        raise HTTPException(
            status_code=400, detail="Start date cannot be before today."
        )
    if end_dt <= start_dt:
        raise HTTPException(
            status_code=400, detail="End date must be after start date."
        )
    return (end_dt - start_dt).days


def planner_context(request, db: Session) -> tuple[int, str]:
    return (
        travel_length_days(request.startDate, request.endDate),
        resolve_llm_provider(db, planner_account_id(request)),
    )


async def get_coordinates(place_name: str):
    try:
        return await geocode_place(place_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


async def generate_plan_with_location(
    draft_plan_func,
    *args,
    starting_point: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    people: int = 1,
    travel_length: int,
    db: Optional[Session] = None,
    **kwargs,
):
    """Shared entry for all three planner modes after the form is validated."""
    lat, lon = await get_coordinates(starting_point)
    airport = nearest_airport(lat, lon, db=db)
    preferred_transport = kwargs.get("preferredTransport") or "allModes"
    # Ground-only modes skip flight route loading entirely.
    should_load_direct_destinations = preferred_transport not in {"trainBus", "trainBusFerry"}
    direct_destinations = (
        await get_direct_destinations_cached(db, airport["iata"])
        if should_load_direct_destinations and airport and airport.get("iata")
        else []
    )

    draft_plan_raw = await draft_plan_func(
        *args,
        direct_destinations=direct_destinations,
        starting_airport_iata=(airport or {}).get("iata"),
        start_date=start_date,
        end_date=end_date,
        **kwargs,
    )

    draft_plan = set_requested_dates(
        parse_planner_json(draft_plan_raw),
        start_date=start_date,
        end_date=end_date,
        travel_length=travel_length,
    )
    if db is not None:
        clean_plan_city_names(draft_plan, db)
        await attach_lodging_coordinates(draft_plan)
    apply_people_to_booking_links(draft_plan, people)
    return {
        "draft_plan": normalize_planner_response(draft_plan),
        "starting_point_coords": {"lat": lat, "lon": lon},
        "nearest_airport": airport,
        "validation": None,
    }


def apply_people_to_booking_links(plan: dict, people: int = 1) -> None:
    for trip in plan.get("trips", [plan]):
        for stop in trip.get("plan", []):
            if not stop.get("booking_url"):
                continue
            updated_url = booking_url(
                stop.get("airline_iata"),
                stop.get("origin_airport_iata"),
                stop.get("destination_airport_iata"),
                stop.get("arrivalDate"),
                people,
            )
            if updated_url:
                stop["booking_url"] = updated_url


def clean_plan_city_names(plan: dict, db: Session) -> None:
    """Normalize stop city labels for display and accommodation search.

    IATA codes are routing hubs only. Prefer the user's ``requested_place``,
    then derive a tourist-facing name from the airport row (with IATA overrides).
    """
    for trip in plan.get("trips", [plan]):
        for stop in trip.get("plan", []):
            if not isinstance(stop, dict):
                continue
            # Keep typed / home place names; IATA is only the routing hub.
            if (
                stop.get("off_airport")
                or stop.get("is_ground_transfer")
                or stop.get("is_return_home")
            ):
                requested = (stop.get("requested_place") or "").strip()
                if requested:
                    stop["city"] = requested.split(",")[0].strip().title()
                continue
            requested = (stop.get("requested_place") or "").strip()
            if requested:
                stop["city"] = requested.split(",")[0].strip().title()
                continue
            iata = (stop.get("iata") or "").strip().upper()
            if not iata:
                continue
            airport = db.query(models.Airport).filter(models.Airport.iata == iata).first()
            if airport is not None:
                airport_row = cast(Any, airport)
                city = airport_name_as_city(airport_row.name, iata)
                if not city or city.upper() == iata:
                    city = (airport_row.city or "").strip()
                if city:
                    stop["city"] = city


async def attach_lodging_coordinates(plan: dict) -> None:
    """Attach city-center coordinates for accommodation search (not airport POIs).

    Booking.com text search often resolves to the airport; lat/lon anchors the
    map on the municipality. Reuses off-airport coords when already present.
    Sleeps between Nominatim calls to respect the 1 req/s usage policy.
    """
    for trip in plan.get("trips", [plan]):
        stops = trip.get("plan", [])
        for index, stop in enumerate(stops):
            if not isinstance(stop, dict):
                continue
            if stop.get("lodging_latitude") is not None and stop.get("lodging_longitude") is not None:
                continue
            lat = stop.get("latitude")
            lon = stop.get("longitude")
            if lat is not None and lon is not None:
                stop["lodging_latitude"] = lat
                stop["lodging_longitude"] = lon
                continue
            city = (stop.get("city") or "").strip()
            if not city:
                continue
            country_label = geocode_country_label(stop.get("country") or "")
            try:
                if index > 0:
                    await asyncio.sleep(1.1)
                lat, lon = await geocode_city_center(city, country_label)
                stop["lodging_latitude"] = lat
                stop["lodging_longitude"] = lon
            except Exception:
                continue


def parse_planner_json(raw: str) -> dict:
    """Parse LLM output; strips markdown fences if the model wrapped JSON in ```."""
    try:
        text = (raw or "").strip()
        if text.startswith("```"):
            text = "\n".join(
                line for line in text.splitlines() if not line.strip().startswith("```")
            )
        return json.loads(text)
    except Exception:
        return {"raw": raw}


def set_requested_dates(
    plan: dict,
    *,
    start_date: Optional[str],
    end_date: Optional[str],
    travel_length: int,
) -> dict:
    if "trips" in plan:
        for trip in plan.get("trips", []):
            trip["startDate"] = start_date
            trip["endDate"] = end_date
            trip["tripLengthDays"] = travel_length
    else:
        plan["startDate"] = start_date
        plan["endDate"] = end_date
        plan["tripLengthDays"] = travel_length
    return plan
