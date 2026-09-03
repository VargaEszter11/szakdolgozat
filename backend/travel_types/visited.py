"""Visited-places strategy: include requested destinations in the itinerary.

When ``starting_airport_iata`` is known (normal path via ``plan_requests``),
delegates to the DB planner. The LLM-only branch below is a legacy fallback
when no hub could be resolved.
"""
from typing import List, Optional
from .common import (
    destination_label,
    destinations_text,
    itinerary_rules_standard,
    language_name,
    merge_place_lists,
    output_json_single_trip_schema,
    places_context_block,
    run_db_planner,
    system_travel_planner,
    user_trip_header,
)
from .llm_client import call_llm_api


async def generate_travel_plan_visited(
    startingPoint: str,
    travelLength: int,
    preferences: List[str],
    visitedPlaces: List[str],
    direct_destinations: Optional[List[dict]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    language: str = "en",
    llm_provider: str = "deepseek",
    starting_airport_iata: Optional[str] = None,
    extra_places: Optional[List[str]] = None,
    preferredTransport: str = "allModes",
    forbidden_places: Optional[List[str]] = None,
    keep_places: Optional[List[str]] = None,
) -> str:
    """Generate a travel plan from requested visited places."""
    start_date_value = start_date or ""
    end_date_value = end_date or ""
    requested_places = merge_place_lists(visitedPlaces, extra_places)
    if starting_airport_iata:
        return await run_db_planner(
            strategy="visited",
            starting_point=startingPoint,
            starting_airport_iata=starting_airport_iata,
            travel_length=travelLength,
            preferences=preferences,
            start_date=start_date_value,
            end_date=end_date_value,
            language=language,
            llm_provider=llm_provider,
            visited_places=requested_places,
            forbidden_places=forbidden_places,
            extra_places=extra_places,
            keep_places=keep_places,
            preferred_transport=preferredTransport,
        )

    lang_name = language_name(language)
    available_places = _matching_destinations(direct_destinations or [], requested_places)
    prompt = (
        f"{system_travel_planner(lang_name)}"
        f"{user_trip_header(startingPoint, start_date_value, end_date_value, travelLength, preferences)}"
        f"{places_context_block(requested_places=requested_places, extra_places=extra_places)}"
        f"Available airport-linked destinations:\n{destinations_text(available_places)}\n\n"
        "Constraint:\nONLY choose destinations from this list:\n"
        f"{requested_places}\n\n"
        "TASK:\nGenerate a realistic draft itinerary.\n"
        f"The trip must start on {start_date_value} and end on {end_date_value}.\n"
        f"{itinerary_rules_standard(travel_length=travelLength, start_date=start_date_value, end_date=end_date_value, starting_point=startingPoint, extra_rule_lines=('- Use cities from the available destinations list above.', '- Choose geographically reasonable routes and prefer train/bus when practical.'))}"
        f"{output_json_single_trip_schema(start_date_value, end_date_value, 'visited')}"
    )
    return await call_llm_api(prompt, llm_provider)


def _matching_destinations(destinations: List[dict], requested_places: List[str]) -> List[str]:
    out = []
    city_map = {
        (dest.get("city") or "").lower(): dest
        for dest in destinations
        if dest.get("city")
    }
    for place in requested_places:
        place_lower = place.lower()
        for city_key, dest in city_map.items():
            if city_key and (place_lower in city_key or city_key in place_lower):
                out.append(destination_label(dest))
    return out
