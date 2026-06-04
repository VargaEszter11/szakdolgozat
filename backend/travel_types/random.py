from typing import List

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
    direct_destinations: List[dict] = None,
    start_date: str = None,
    end_date: str = None,
    language: str = "en",
    llm_provider: str = "deepseek",
    starting_airport_iata: str = None,
    preferredTransport: str = "allModes",
) -> str:
    """Generate random itineraries where each leg loads direct destinations from the current airport."""
    if starting_airport_iata:
        trip_json = await run_db_planner(
            strategy="random",
            starting_point=startingPoint,
            starting_airport_iata=starting_airport_iata,
            travel_length=travelLength,
            preferences=preferences,
            start_date=start_date,
            end_date=end_date,
            language=language,
            llm_provider=llm_provider,
            visited_places=None,
            forbidden_places=None,
            preferred_transport=preferredTransport,
        )
        return as_json({"trips": [from_json(trip_json)]})

    lang_name = language_name(language)
    destinations_info = destinations_text(
        [destination_label(dest) for dest in direct_destinations or [] if dest.get("city")]
    )

    prompt = (
        f"{system_travel_planner(lang_name)}"
        f"{user_trip_header(startingPoint, start_date, end_date, travelLength, preferences)}"
        f"Available airport-linked destinations:\n{destinations_info}\n\n"
        "TASK:\nGenerate a realistic random European itinerary using these destinations as possible anchors, but prefer sensible train/bus hops where geography supports it.\n"
        f"The trip must start on {start_date} and end on {end_date}.\n"
        f"{itinerary_rules_standard(travel_length=travelLength, start_date=start_date, end_date=end_date, starting_point=startingPoint, extra_rule_lines=('- Use cities from the available destinations list as anchors, but do not default to flights.', '- Routes must be geographically reasonable and varied.'))}"
        f"{output_json_random_five_trips(start_date, end_date)}"
    )
    return await call_llm_api(prompt, llm_provider)
