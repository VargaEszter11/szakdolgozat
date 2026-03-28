# TODO: better date handling, realistic travel mode

from typing import List

from pydantic import BaseModel
from sqlalchemy.orm import Session

from .ollama_client import call_ollama_api


LANG_NAMES = {"en": "English", "hu": "Hungarian", "de": "German"}


class UnvisitedGenerationRequest(BaseModel):
    """Request body for POST /generate_travel_plans/unvisited."""

    userId: int
    startingPoint: str
    budget: int
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
) -> str:
    """Generate travel plan that avoids cities in ``forbidden_places`` (visited / excluded)."""
    lang_name = LANG_NAMES.get(language, "English")

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

    destinations_info = "\n".join(available_destinations) if available_destinations else "No direct flights available from starting airport."

    prompt = f"""
SYSTEM:
You are a travel planning AI.
DO NOT estimate prices.
DO NOT mention costs.
Write ALL text values (country names, activities) in {lang_name}.

USER:
Starting point: {startingPoint}
Start date: {start_date}
End date: {end_date}
Trip length: {travelLength} days
Preferences: {preferences}

ALREADY VISITED (FORBIDDEN — do NOT include any of these cities):
{excluded_names}

ALLOWED destinations (these are the ONLY cities you may use):
{destinations_info}

TASK:
Generate a realistic draft itinerary using ONLY cities from the ALLOWED list above.
The trip must start on {start_date} and end on {end_date}.
NEVER include any city from the FORBIDDEN list. If a city appears in both lists, it is FORBIDDEN.

Rules:
- Use the starting point only as a transport hub.
- Pick cities ONLY from the ALLOWED destinations list — no exceptions.
- Sum of days MUST equal {travelLength}.
- Assign concrete arrival and departure dates for each stop, starting from {start_date}.
- The LAST entry in the plan MUST be the starting point ({startingPoint}) with arrivalDate = {end_date}, days = 0, and the transport used to get back. This represents the return home.
- Choose the BEST transport method for each segment: use "flight" only when it's the most practical option (long distances, islands, time constraints), otherwise prefer "train" or "bus" for shorter distances.
- For each destination, suggest 1-2 realistic activities/programs (e.g., "Museum visit", "City tour", "Beach day", "Historical site", "Local cuisine experience").

OUTPUT:
Return JSON ONLY using this structure:

{{
  "startingPoint": string,
  "startDate": "{start_date}",
  "endDate": "{end_date}",
  "tripLengthDays": number,
  "strategy": "unvisited",
  "plan": [
    {{"city": string,"country": string,"iata": string,"days": number,"arrivalDate": "YYYY-MM-DD","departureDate": "YYYY-MM-DD","transportFromPreviousCity": "train | bus | flight | ferry | none","activities": [string]}}
  ]
}}
"""
    return await call_ollama_api(prompt)
