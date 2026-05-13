import json
from typing import List

from .llm_client import call_llm_api
from .prompt_common import (
    itinerary_rules_standard,
    language_name,
    NO_DIRECT_FLIGHTS_MESSAGE,
    output_json_random_five_trips,
    system_travel_planner,
    user_trip_header,
)


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
) -> str:
    """Generate random itineraries (stepwise: each leg loads direct destinations from current airport)."""
    if starting_airport_iata:
        from .stepwise_planner import build_plan_stepwise

        trip = await build_plan_stepwise(
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
        )
        return json.dumps({"trips": [trip]}, ensure_ascii=False)

    lang_name = language_name(language)
    available_destinations = []
    if direct_destinations:
        for dest in direct_destinations:
            city = dest.get("city")
            if city:
                available_destinations.append(f"{city}, {dest.get('country')} (IATA: {dest.get('iata')})")

    destinations_info = "\n".join(available_destinations) if available_destinations else NO_DIRECT_FLIGHTS_MESSAGE

    prompt = (
        f"{system_travel_planner(lang_name)}"
        f"{user_trip_header(startingPoint, start_date, end_date, travelLength, preferences)}"
        f"Available destinations with direct flights:\n{destinations_info}\n\n"
        "TASK:\nGenerate 5 realistic random European itineraries using ONLY destinations with direct flights available.\n"
        f"The trip must start on {start_date} and end on {end_date}.\n"
        f"{itinerary_rules_standard(travel_length=travelLength, start_date=start_date, end_date=end_date, starting_point=startingPoint, extra_rule_lines=('- ONLY use cities from the available destinations list above.', '- Routes must be geographically reasonable.'))}"
        f"{output_json_random_five_trips(start_date, end_date)}"
    )
    return await call_llm_api(prompt, llm_provider)
