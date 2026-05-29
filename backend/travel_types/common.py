"""Shared helpers for travel type entry points."""

from __future__ import annotations

import json
from typing import List

LANG_NAMES = {"en": "English", "hu": "Hungarian", "de": "German"}
NO_DIRECT_FLIGHTS_MESSAGE = "No direct flights available from starting airport."

TRANSPORT_RULES = (
    "Transport between stops (field transportFromPreviousCity: one of train | bus | flight | ferry):",
    "- Do not blindly prioritize any one transport mode.",
    "- Choose the mode that makes the route most logical: train/bus for nearby regional movement, flights for long jumps or island/sea-separated routes.",
    "- A good itinerary may mix transport modes, but only when the route flow still makes sense.",
)

ROUTE_DATA_RULES = (
    "Route data:",
    "- The same city or airport may appear more than once because several airlines can serve the same route.",
    "- Treat duplicate candidate rows with the same IATA or same city as one destination option.",
    "- Do not repeat the same city, same IATA, or same metro area as separate trip stops.",
    "- Use the route data only to prove reachability; the itinerary should still be city-based, not airport-based.",
    "- The city field in the final JSON must be the city/municipality name, not the airport name.",
    "- Remove airport suffixes/labels from city names, e.g. write Stockholm instead of Stockholm Arlanda.",
    "- Flight candidates may include seasonality: seasonal, year_round, or unknown.",
    "- If a seasonal flight is listed, the backend has already checked the known effective date range for the current travel date.",
    "- If seasonality is unknown, do not invent operating seasons or dates; use it as a reachable but unverified flight option.",
    "- Never claim that a seasonal/unknown flight operates outside the dates shown in the candidate row.",
)

GENERAL_OUTPUT_RULES = (
    "Pricing and costs:",
    "- Do NOT invent numeric prices or currency amounts in the JSON.",
    "- Use realistic cities and IATA codes; the server uses local route data for airport routing.",
)

ACTIVITY_SUGGESTION_RULE = "- For each destination, suggest 1-2 realistic activities/programs."


def language_name(language_code: str) -> str:
    return LANG_NAMES.get((language_code or "en").lower(), "English")


def preferences_line(preferences: list | None) -> str:
    if not preferences:
        return "none"
    return ", ".join(str(p).strip() for p in preferences if str(p).strip())


def _list_line(values: list | None) -> str:
    cleaned = [str(value).strip() for value in values or [] if str(value).strip()]
    return ", ".join(cleaned) if cleaned else "none"


def _block(*lines: str) -> str:
    return "\n".join(line for line in lines if line is not None) + "\n"


def _rules_block() -> str:
    return _block(*TRANSPORT_RULES, *ROUTE_DATA_RULES, *GENERAL_OUTPUT_RULES)


def places_context_block(
    *,
    requested_places: list | None = None,
    forbidden_places: list | None = None,
    extra_places: list | None = None,
) -> str:
    return (
        "User place constraints:\n"
        f"- Places the user wants considered/included: {_list_line(requested_places)}\n"
        f"- Extra places typed in the form: {_list_line(extra_places)}\n"
        f"- Places the user wants excluded: {_list_line(forbidden_places)}\n\n"
    )


def system_travel_planner(lang_name: str) -> str:
    return _block(
        "SYSTEM:",
        "You are a travel planning AI.",
        f"Write ALL text values (country names, activities) in {lang_name}.",
        _rules_block(),
    )


def system_next_stop(lang_name: str) -> str:
    return _block(
        "SYSTEM:",
        "You choose exactly ONE next stop on a multi-city trip.",
        f"Write activities in {lang_name}.",
        "Prefer variety. Avoid repeatedly choosing the same famous hubs or the first-looking option.",
        _rules_block(),
    )


def user_trip_header(
    starting_point: str,
    start_date: str,
    end_date: str,
    travel_length: int,
    preferences: list | None,
) -> str:
    return (
        "USER:\n"
        f"Starting point: {starting_point}\n"
        f"Start date: {start_date}\n"
        f"End date: {end_date}\n"
        f"Trip length: {travel_length} days\n"
        f"Preferences: {preferences_line(preferences)}\n"
    )


def itinerary_rules_standard(
    *,
    travel_length: int,
    start_date: str,
    end_date: str,
    starting_point: str,
    hub_line: str = "- Use the starting point only as a transport hub.",
    extra_rule_lines: tuple[str, ...] = (),
) -> str:
    lines: list[str] = [
        "",
        "Rules:",
        hub_line,
        *extra_rule_lines,
        "- Make the itinerary varied: avoid repeating the same region or same obvious city pattern.",
        "- If route data contains duplicate routes for the same city/IATA, treat them as one option.",
        "- Never use duplicate airport rows or multiple airports in the same metro area as separate stops.",
        "- Put stops in a logical geographic order. Avoid zig-zags, backtracking, and jumping past nearby sensible stops.",
        "- Use train, bus, ferry, or flight according to what makes the route most logical; do not force one mode.",
        "- Give each stop enough time. Avoid rushed one-night/one-day stops unless the whole trip is very short.",
        f"- Sum of days MUST equal {travel_length}.",
        f"- Assign concrete arrival and departure dates for each stop, starting from {start_date}.",
        (
            "- The LAST entry in the plan MUST be the starting point "
            f"({starting_point}) with arrivalDate = {end_date}, days = 0, "
            "and the transport used to get back. This represents the return home."
        ),
        ACTIVITY_SUGGESTION_RULE,
    ]
    return "\n".join(lines)


def output_json_single_trip_schema(start_date: str, end_date: str, strategy: str) -> str:
    return _block(
        "OUTPUT:Return JSON ONLY using this structure:",
        "{",
        '  "startingPoint": string,',
        f'  "startDate": "{start_date}",',
        f'  "endDate": "{end_date}",',
        '  "tripLengthDays": number,',
        f'  "strategy": "{strategy}",',
        '  "plan": [',
        '    {"city": string,"country": string,"iata": string,"days": number,"arrivalDate": "YYYY-MM-DD","departureDate": "YYYY-MM-DD","transportFromPreviousCity": "train | bus | flight | ferry","activities": [string]}',
        "  ]",
        "}",
    )


def output_json_random_five_trips(start_date: str, end_date: str) -> str:
    return _block(
        "OUTPUT:Return JSON ONLY using this structure:",
        "{",
        '"trips": [',
        f'  {{"startingPoint": string,"startDate": "{start_date}","endDate": "{end_date}","tripLengthDays": number,"strategy": "random","plan": [{{"city": string,"country": string,"iata": string,"days": number,"arrivalDate": "YYYY-MM-DD","departureDate": "YYYY-MM-DD","transportFromPreviousCity": "train | bus | flight | ferry","activities": [string]}}]}}',
        "  ]",
        "}",
    )


def next_stop_prompt(
    *,
    strategy: str,
    lang_name: str,
    current_airport: str,
    current_city_label: str,
    prefs: str,
    remaining_days: int,
    min_stop_days: int,
    cand_block: str,
    avoid: str,
    requested_places: list | None = None,
    forbidden_places: list | None = None,
    extra_places: list | None = None,
) -> str:
    return _block(
        system_next_stop(lang_name),
        "USER:",
        f"Strategy: {strategy}",
        f"Current departure airport (IATA): {current_airport}",
        f"Current location label: {current_city_label}",
        f"Preferences: {prefs}",
        places_context_block(
            requested_places=requested_places,
            forbidden_places=forbidden_places,
            extra_places=extra_places,
        ),
        f"Total days still to assign (this stop + any later stops before return home): {remaining_days}",
        "",
        f"Candidate destinations reachable from {current_airport} by the listed transport.",
        "You MUST pick one row. Copy country, IATA, and transport exactly, but clean the city name for display:",
        cand_block,
        "",
        f"Avoid repeating these cities already visited on this trip: {avoid}",
        "",
        "Rules:",
        "- Output JSON only, one object.",
        "- Do not always pick the first candidate. Choose a destination that adds variety to the route.",
        "- If multiple candidates represent the same city/IATA/metro area, treat them as duplicates and pick only one.",
        '- The returned city must be a clean city name, not an airport name.',
        "- If any requested/extra place appears in the candidate list, strongly prefer choosing it before unrelated places.",
        "- Never choose a candidate that matches the excluded places list.",
        "- Keep the route geographically logical: prefer nearby forward movement over zig-zags or backtracking.",
        "- Choose the candidate whose listed transport best fits the trip flow; do not force ground transport or flights.",
        "- For flight candidates, respect the listed seasonality/effective dates. Do not invent missing operating dates.",
        "- Unknown seasonality means the route is reachable but date details are not verified by the source.",
        "- Avoid choosing another airport/city in the exact same metro area unless it is genuinely the intended destination.",
        f'- "days": integer from {min_stop_days} to {remaining_days} (days spent at the chosen city before moving on).',
        "- Prefer fewer well-paced stops over many rushed stops; do not leave a single leftover day for another city.",
        f'- If all remaining days should be spent at this city (last stop before return home), set "days" to {remaining_days}.',
        '- "transportFromPreviousCity": use the transport listed on the chosen candidate row.',
        f'- "preferences": choose from the preferences listed in {prefs} when selecting the activities, but not only from them.',
        "",
        "Return JSON only with this shape:",
        '{"city":"","country":"","iata":"","days":1,"transportFromPreviousCity":"flight","activities":["",""]}',
    )


def as_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False)


def from_json(raw: str) -> dict:
    return json.loads(raw)


def merge_place_lists(*groups: List[str] | None) -> List[str]:
    seen = set()
    out: List[str] = []
    for group in groups:
        for place in group or []:
            text = str(place).strip()
            if not text:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(text)
    return out


def place_label(place) -> str:
    name = (getattr(place, "place_name", None) or "").strip()
    country = (getattr(place, "country", None) or "").strip()
    return (f"{name}, {country}" if country else name).strip().strip(",")


def destination_label(destination: dict) -> str:
    return (
        f"{destination.get('city')}, {destination.get('country')} "
        f"(IATA: {destination.get('iata')})"
    )


def destinations_text(destinations: List[str]) -> str:
    return "\n".join(destinations) if destinations else NO_DIRECT_FLIGHTS_MESSAGE


async def run_db_planner(
    *,
    strategy: str,
    starting_point: str,
    starting_airport_iata: str,
    travel_length: int,
    preferences: List[str],
    start_date: str,
    end_date: str,
    language: str,
    llm_provider: str,
    visited_places: List[str] | None = None,
    forbidden_places: List[str] | None = None,
    extra_places: List[str] | None = None,
) -> str:
    from .planner import build_plan

    data = await build_plan(
        strategy=strategy,
        starting_point=starting_point,
        starting_airport_iata=starting_airport_iata,
        travel_length=travel_length,
        preferences=preferences,
        start_date=start_date,
        end_date=end_date,
        language=language,
        llm_provider=llm_provider,
        visited_places=visited_places,
        forbidden_places=forbidden_places,
        extra_places=extra_places,
    )
    return as_json(data)
