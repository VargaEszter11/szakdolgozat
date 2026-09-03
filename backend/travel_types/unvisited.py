"""Unvisited-places strategy: explore destinations not in the user's travel log.

``forbidden_places`` merges manual exclusions with DB visited places when
``userId`` is sent (travel-log toggle on).
"""
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .common import (
    destination_label,
    destinations_text,
    itinerary_rules_standard,
    language_name,
    merge_place_lists,
    output_json_single_trip_schema,
    place_label,
    places_context_block,
    run_db_planner,
    system_travel_planner,
    user_trip_header,
)
from .llm_client import call_llm_api


class UnvisitedGenerationRequest(BaseModel):
    """Request body for POST /generate_travel_plans/unvisited."""

    userId: Optional[int] = None
    plannerUserId: Optional[int] = None
    startingPoint: str
    startDate: str
    endDate: str
    people: int = 1
    preferredTransport: str = "allModes"
    preferences: List[str] = []
    additionalExclusions: List[str] = []
    likedPlaces: List[str] = []
    dislikedPlaces: List[str] = []
    language: str = "en"


def format_user_visited_place_strings(places) -> List[str]:
    """Match frontend convention: 'City, Country' when country is set."""
    return merge_place_lists([place_label(place) for place in places])


def merge_exclusion_lists(from_db: List[str], extras: List[str]) -> List[str]:
    return merge_place_lists(from_db, extras)


def build_unvisited_forbidden_places(
    db: Session, user_id: int, additional_exclusions: List[str]
) -> List[str]:
    """Load saved visited places for the user and merge with manual exclusions."""
    from database import crud

    rows = crud.get_user_visited_places(db, user_id)
    from_db = format_user_visited_place_strings(rows)
    return merge_exclusion_lists(from_db, additional_exclusions)


def build_visited_places_from_db(
    db: Session, user_id: int, client_places: List[str]
) -> List[str]:
    """Load saved visited places for the user and merge with client-supplied names."""
    from database import crud

    rows = crud.get_user_visited_places(db, user_id)
    from_db = format_user_visited_place_strings(rows)
    return merge_exclusion_lists(from_db, client_places)


def _extract_city(place_str: str) -> str:
    """Extract just the city name (before comma) and lowercase it."""
    return place_str.split(",")[0].strip().lower()


def _is_visited(city_name: str, country_name: str, visited_cities: set, visited_full: list) -> bool:
    """Check if a destination matches any forbidden (visited) place."""
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


async def generate_travel_plan_unvisited(
    startingPoint: str,
    travelLength: int,
    preferences: List[str],
    forbidden_places: List[str],
    direct_destinations: Optional[List[dict]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    language: str = "en",
    llm_provider: str = "deepseek",
    starting_airport_iata: Optional[str] = None,
    preferredTransport: str = "allModes",
    extra_places: Optional[List[str]] = None,
    keep_places: Optional[List[str]] = None,
) -> str:
    """Generate travel plan that avoids cities in ``forbidden_places`` (visited / excluded)."""
    start_date_value = start_date or ""
    end_date_value = end_date or ""

    if starting_airport_iata:
        return await run_db_planner(
            strategy="unvisited",
            starting_point=startingPoint,
            starting_airport_iata=starting_airport_iata,
            travel_length=travelLength,
            preferences=preferences,
            start_date=start_date_value,
            end_date=end_date_value,
            language=language,
            llm_provider=llm_provider,
            visited_places=None,
            forbidden_places=forbidden_places,
            extra_places=extra_places,
            keep_places=keep_places,
            preferred_transport=preferredTransport,
        )

    lang_name = language_name(language)
    visited_cities = {_extract_city(p) for p in forbidden_places}
    visited_full = [p.lower() for p in forbidden_places]
    excluded_display = {place_str.split(",")[0].strip() for place_str in forbidden_places}
    excluded_names = ", ".join(sorted(excluded_display)) if excluded_display else "none"
    destinations_info = destinations_text(
        [
            destination_label(dest)
            for dest in direct_destinations or []
            if dest.get("city")
            and not _is_visited(dest.get("city", ""), dest.get("country", ""), visited_cities, visited_full)
        ]
    )

    prompt = (
        f"{system_travel_planner(lang_name)}"
        f"{user_trip_header(startingPoint, start_date_value, end_date_value, travelLength, preferences)}"
        f"{places_context_block(forbidden_places=forbidden_places, extra_places=forbidden_places)}"
        "ALREADY VISITED (FORBIDDEN — do NOT include any of these cities):\n"
        f"{excluded_names}\n\n"
        "ALLOWED destinations (these are the ONLY cities you may use):\n"
        f"{destinations_info}\n\n"
        "TASK:\nGenerate a realistic draft itinerary using the ALLOWED cities as anchors. Prefer train/bus when practical; do not default to flights.\n"
        f"The trip must start on {start_date_value} and end on {end_date_value}.\n"
        "NEVER include any city from the FORBIDDEN list. If a city appears in both lists, it is FORBIDDEN.\n"
        f"{itinerary_rules_standard(travel_length=travelLength, start_date=start_date_value, end_date=end_date_value, starting_point=startingPoint, extra_rule_lines=('- Pick cities ONLY from the ALLOWED destinations list — no exceptions.',))}"
        f"{output_json_single_trip_schema(start_date_value, end_date_value, 'unvisited')}"
    )
    return await call_llm_api(prompt, llm_provider)
