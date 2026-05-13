# TODO: better date handling, realistic travel mode

import json
from typing import List

from .llm_client import call_llm_api
from .prompt_common import (
    itinerary_rules_standard,
    language_name,
    NO_DIRECT_FLIGHTS_MESSAGE,
    output_json_single_trip_schema,
    system_travel_planner,
    user_trip_header,
)


async def generate_travel_plan_visited(
    startingPoint: str,
    travelLength: int,
    preferences: List[str],
    visitedPlaces: List[str],
    direct_destinations: List[dict] = None,
    start_date: str = None,
    end_date: str = None,
    language: str = "en",
    llm_provider: str = "deepseek",
    starting_airport_iata: str = None,
) -> str:
    """Generate travel plan for visited places (stepwise hub → next hub → …)."""
    if starting_airport_iata:
        from .stepwise_planner import build_plan_stepwise

        data = await build_plan_stepwise(
            strategy="visited",
            starting_point=startingPoint,
            starting_airport_iata=starting_airport_iata,
            travel_length=travelLength,
            preferences=preferences,
            start_date=start_date,
            end_date=end_date,
            language=language,
            llm_provider=llm_provider,
            visited_places=visitedPlaces,
            forbidden_places=None,
        )
        return json.dumps(data, ensure_ascii=False)

    lang_name = language_name(language)
    available_places = []
    if direct_destinations:
        dest_cities = {(dest.get("city") or "").lower(): dest for dest in direct_destinations if dest.get("city")}
        for place in visitedPlaces:
            place_lower = place.lower()
            for city_key, dest in dest_cities.items():
                if city_key and (place_lower in city_key or city_key in place_lower):
                    available_places.append(f"{dest.get('city')}, {dest.get('country')} (IATA: {dest.get('iata')})")

    direct_destinations_str = "\n".join(available_places) if available_places else NO_DIRECT_FLIGHTS_MESSAGE

    prompt = (
        f"{system_travel_planner(lang_name)}"
        f"{user_trip_header(startingPoint, start_date, end_date, travelLength, preferences)}"
        f"Available destinations with direct flights:\n{direct_destinations_str}\n\n"
        "Constraint:\nONLY choose destinations from this list:\n"
        f"{visitedPlaces}\n\n"
        "TASK:\nGenerate a realistic draft itinerary.\n"
        f"The trip must start on {start_date} and end on {end_date}.\n"
        f"{itinerary_rules_standard(travel_length=travelLength, start_date=start_date, end_date=end_date, starting_point=startingPoint, extra_rule_lines=('- ONLY use cities from the available destinations list above.', '- Choose geographically reasonable routes.'))}"
        f"{output_json_single_trip_schema(start_date, end_date, 'visited')}"
    )
    return await call_llm_api(prompt, llm_provider)
