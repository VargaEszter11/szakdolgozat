"""Random strategy: varied route without a fixed place list.

DB planner picks from ranked candidates at each hub; LLM fallback generates
five trip variants when no starting airport is available.
"""
from typing import List, Optional
from .common import (
    as_json,
    destination_label,
    destinations_text,
    from_json,
    itinerary_rules_standard,
    language_name,
    output_json_random_five_trips,
    run_db_planner,
    system_travel_planner,
    user_trip_header,
)
from .llm_client import call_llm_api


async def generate_travel_plan_random(
    startingPoint: str,
    travelLength: int,
    preferences: List[str],
    direct_destinations: Optional[List[dict]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    language: str = "en",
    llm_provider: str = "deepseek",
    starting_airport_iata: Optional[str] = None,
    preferredTransport: str = "allModes",
    extra_places: Optional[List[str]] = None,
    forbidden_places: Optional[List[str]] = None,
    keep_places: Optional[List[str]] = None,
) -> str:
    """Generate random itineraries where each leg loads direct destinations from the current airport."""
    start_date_value = start_date or ""
    end_date_value = end_date or ""

    if starting_airport_iata:
        trip_json = await run_db_planner(
            strategy="random",
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
        return as_json({"trips": [from_json(trip_json)]})

    lang_name = language_name(language)
    destinations_info = destinations_text(
        [destination_label(dest) for dest in direct_destinations or [] if dest.get("city")]
    )

    prompt = (
        f"{system_travel_planner(lang_name)}"
        f"{user_trip_header(startingPoint, start_date_value, end_date_value, travelLength, preferences)}"
        f"Available airport-linked destinations:\n{destinations_info}\n\n"
        "TASK:\nGenerate a realistic random European itinerary using these destinations as possible anchors, but prefer sensible train/bus hops where geography supports it.\n"
        f"The trip must start on {start_date_value} and end on {end_date_value}.\n"
        f"{itinerary_rules_standard(travel_length=travelLength, start_date=start_date_value, end_date=end_date_value, starting_point=startingPoint, extra_rule_lines=('- Use cities from the available destinations list as anchors, but do not default to flights.', '- Routes must be geographically reasonable and varied.'))}"
        f"{output_json_random_five_trips(start_date_value, end_date_value)}"
    )
    return await call_llm_api(prompt, llm_provider)
