# TODO: better date handling, realistic travel mode

import json
from typing import List, Optional

from pydantic import BaseModel
from sqlalchemy.orm import Session

from .llm_client import call_llm_api
from .prompt_common import (
    itinerary_rules_standard,
    language_name,
    NO_DIRECT_FLIGHTS_MESSAGE,
    output_json_single_trip_schema,
    system_travel_planner,
    user_trip_header,
)


class UnvisitedGenerationRequest(BaseModel):
    """Request body for POST /generate_travel_plans/unvisited."""

    userId: Optional[int] = None
    plannerUserId: Optional[int] = None
    startingPoint: str
    budget: Optional[int] = None
    startDate: str
    endDate: str
    preferences: List[str] = []
    additionalExclusions: List[str] = []
    language: str = "en"


def format_user_visited_place_strings(places) -> List[str]:
    """Match frontend convention: 'City, Country' when country is set."""
    seen = set()
    out: List[str] = []
    for p in places:
        name = (getattr(p, "place_name", None) or "").strip()
        country = (getattr(p, "country", None) or "").strip()
        s = f"{name}, {country}" if country else name
        s = s.strip().strip(",")
        if not s:
            continue
        key = s.lower()
        if key not in seen:
            seen.add(key)
            out.append(s)
    return out


def merge_exclusion_lists(from_db: List[str], extras: List[str]) -> List[str]:
    cleaned = [x.strip() for x in extras if x and str(x).strip()]
    merged = from_db + cleaned
    seen = set()
    result: List[str] = []
    for item in merged:
        k = item.lower()
        if k not in seen:
            seen.add(k)
            result.append(item)
    return result


def build_unvisited_forbidden_places(
    db: Session, user_id: int, additional_exclusions: List[str]
) -> List[str]:
    """Load saved visited places for the user and merge with manual exclusions."""
    from database import crud

    rows = crud.get_user_visited_places(db, user_id)
    from_db = format_user_visited_place_strings(rows)
    return merge_exclusion_lists(from_db, additional_exclusions)


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
    direct_destinations: List[dict] = None,
    start_date: str = None,
    end_date: str = None,
    language: str = "en",
    llm_provider: str = "deepseek",
    starting_airport_iata: str = None,
) -> str:
    """Generate travel plan that avoids cities in ``forbidden_places`` (visited / excluded)."""
    if starting_airport_iata:
        from .stepwise_planner import build_plan_stepwise

        data = await build_plan_stepwise(
            strategy="unvisited",
            starting_point=startingPoint,
            starting_airport_iata=starting_airport_iata,
            travel_length=travelLength,
            preferences=preferences,
            start_date=start_date,
            end_date=end_date,
            language=language,
            llm_provider=llm_provider,
            visited_places=None,
            forbidden_places=forbidden_places,
        )
        return json.dumps(data, ensure_ascii=False)

    lang_name = language_name(language)

    visited_cities = {_extract_city(p) for p in forbidden_places}
    visited_full = [p.lower() for p in forbidden_places]
    excluded_display = {place_str.split(",")[0].strip() for place_str in forbidden_places}
    excluded_names = ", ".join(sorted(excluded_display)) if excluded_display else "none"

    available_destinations = []
    if direct_destinations:
        for dest in direct_destinations:
            city = dest.get("city", "")
            country = dest.get("country", "")
            if city and not _is_visited(city, country, visited_cities, visited_full):
                available_destinations.append(
                    f"{city}, {country} (IATA: {dest.get('iata')})"
                )

    destinations_info = "\n".join(available_destinations) if available_destinations else NO_DIRECT_FLIGHTS_MESSAGE

    prompt = (
        f"{system_travel_planner(lang_name)}"
        f"{user_trip_header(startingPoint, start_date, end_date, travelLength, preferences)}"
        "ALREADY VISITED (FORBIDDEN — do NOT include any of these cities):\n"
        f"{excluded_names}\n\n"
        "ALLOWED destinations (these are the ONLY cities you may use):\n"
        f"{destinations_info}\n\n"
        "TASK:\nGenerate a realistic draft itinerary using the ALLOWED cities as anchors. Prefer train/bus when practical; do not default to flights.\n"
        f"The trip must start on {start_date} and end on {end_date}.\n"
        "NEVER include any city from the FORBIDDEN list. If a city appears in both lists, it is FORBIDDEN.\n"
        f"{itinerary_rules_standard(travel_length=travelLength, start_date=start_date, end_date=end_date, starting_point=startingPoint, extra_rule_lines=('- Pick cities ONLY from the ALLOWED destinations list — no exceptions.',))}"
        f"{output_json_single_trip_schema(start_date, end_date, 'unvisited')}"
    )
    return await call_llm_api(prompt, llm_provider)
