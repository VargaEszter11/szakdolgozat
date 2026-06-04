import json
import os
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import crud, models
from travel_types import (
    UnvisitedGenerationRequest,
    build_unvisited_forbidden_places,
    generate_travel_plan_random,
    generate_travel_plan_unvisited,
    generate_travel_plan_visited,
    merge_exclusion_lists,
)
from travel_types.booking import booking_url
from utils.coordinates import geocode_place
from utils.direct_destinations_cache import get_direct_destinations_cached
from utils.nearest_airport import nearest_airport
from utils.plan_enrichment import normalize_planner_response


class GenerationRequest(BaseModel):
    visitedPlaces: List[str]
    extraPlaces: List[str] = []
    startingPoint: str
    startDate: str
    endDate: str
    people: int = 1
    preferredTransport: str = "allModes"
    preferences: List[str] = []
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
    language: str = "en"
    userId: Optional[int] = None
    plannerUserId: Optional[int] = None


class GeocodeRequest(BaseModel):
    places: List[str]
    language: str = "en"


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
    return await generate_plan_with_location(
        generate_travel_plan_visited,
        request.startingPoint,
        travel_length,
        request.preferences,
        request.visitedPlaces,
        starting_point=request.startingPoint,
        start_date=request.startDate,
        end_date=request.endDate,
        travel_length=travel_length,
        people=request.people,
        preferredTransport=request.preferredTransport,
        language=request.language,
        llm_provider=llm_provider,
        extra_places=request.extraPlaces,
        db=db,
    )


async def generate_unvisited_plan(request: UnvisitedGenerationRequest, db: Session) -> dict:
    travel_length, llm_provider = planner_context(request, db)
    forbidden_places = (
        build_unvisited_forbidden_places(db, request.userId, request.additionalExclusions)
        if request.userId is not None
        else merge_exclusion_lists([], request.additionalExclusions)
    )
    return await generate_plan_with_location(
        generate_travel_plan_unvisited,
        request.startingPoint,
        travel_length,
        request.preferences,
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
    return await generate_plan_with_location(
        generate_travel_plan_random,
        request.startingPoint,
        travel_length,
        request.preferences,
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


def resolve_llm_provider(db: Optional[Session], user_id: Optional[int]) -> str:
    from travel_types.llm_client import normalize_llm_provider

    if db is not None and user_id is not None:
        user = crud.get_user(db, user_id)
        if user is not None:
            raw = getattr(user, "preferred_llm_provider", None)
            if raw:
                return normalize_llm_provider(str(raw))
    return normalize_llm_provider(os.getenv("DEFAULT_LLM_PROVIDER"))


def planner_account_id(request) -> Optional[int]:
    pid = getattr(request, "plannerUserId", None)
    return pid if pid is not None else getattr(request, "userId", None)


def travel_length_days(start_date: str, end_date: str) -> int:
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="End date must be after start date.")
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
    start_date: str = None,
    end_date: str = None,
    people: int = 1,
    travel_length: int,
    db: Optional[Session] = None,
    **kwargs,
):
    lat, lon = await get_coordinates(starting_point)
    airport = await nearest_airport(lat, lon, db=db)
    preferred_transport = kwargs.get("preferredTransport") or "allModes"
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
    clean_plan_city_names(draft_plan, db)
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
    for trip in plan.get("trips", [plan]):
        for stop in trip.get("plan", []):
            if not isinstance(stop, dict):
                continue
            iata = (stop.get("iata") or "").strip().upper()
            if not iata:
                continue
            airport = db.query(models.Airport).filter(models.Airport.iata == iata).first()
            if airport and airport.city:
                stop["city"] = airport.city


def parse_planner_json(raw: str) -> dict:
    try:
        text = (raw or "").strip()
        if text.startswith("```"):
            text = "\n".join(
                line for line in text.splitlines() if not line.strip().startswith("```")
            )
        return json.loads(text)
    except Exception:
        return {"raw": raw}


def set_requested_dates(plan: dict, *, start_date: str, end_date: str, travel_length: int) -> dict:
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
