"""Shared LLM prompt fragments and builders for travel plan generation."""

from __future__ import annotations

LANG_NAMES = {"en": "English", "hu": "Hungarian", "de": "German"}

NO_DIRECT_FLIGHTS_MESSAGE = "No direct flights available from starting airport."

TRANSPORT_RULES = """
Transport between stops (field transportFromPreviousCity: one of train | bus | flight | ferry | none):
- Do not blindly prioritize any one transport mode.
- Choose the mode that makes the route most logical: train/bus for nearby regional movement, flights for long jumps or island/sea-separated routes.
- A good itinerary may mix transport modes, but only when the route flow still makes sense.
"""

PRICING_AND_VALIDATION = """
Pricing and costs:
- Do NOT invent numeric prices or currency amounts in the JSON.
- Use realistic cities and IATA codes; the server uses local route data for airport routing.
"""

ACTIVITY_SUGGESTION_RULE = (
    '- For each destination, suggest 1-2 realistic activities/programs '
    '(e.g., "Museum visit", "City tour", "Beach day", "Historical site", "Local cuisine experience").'
)


def language_name(language_code: str) -> str:
    return LANG_NAMES.get((language_code or "en").lower(), "English")


def preferences_line(preferences: list | None) -> str:
    if not preferences:
        return "none"
    return ", ".join(str(p).strip() for p in preferences if str(p).strip())


def system_travel_planner(lang_name: str) -> str:
    return (
        "SYSTEM:\n"
        "You are a travel planning AI.\n"
        f"Write ALL text values (country names, activities) in {lang_name}.\n"
        f"{TRANSPORT_RULES}\n"
        f"{PRICING_AND_VALIDATION}\n"
    )


def system_stepwise_one_stop(lang_name: str) -> str:
    return (
        "SYSTEM:\n"
        "You choose exactly ONE next stop on a multi-city trip. "
        f"Write activities in {lang_name}.\n"
        "Prefer variety. Avoid repeatedly choosing the same famous hubs or the first-looking option.\n"
        f"{TRANSPORT_RULES}\n"
        f"{PRICING_AND_VALIDATION}\n"
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
        "- Put stops in a logical geographic order. Avoid zig-zags, backtracking, and jumping past nearby sensible stops.",
        "- Use train, bus, ferry, or flight according to what makes the route most logical; do not force one mode.",
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
    return f"""
OUTPUT:Return JSON ONLY using this structure:

{{
  "startingPoint": string,
  "startDate": "{start_date}",
  "endDate": "{end_date}",
  "tripLengthDays": number,
  "strategy": "{strategy}",
  "plan": [
    {{"city": string,"country": string,"iata": string,"days": number,"arrivalDate": "YYYY-MM-DD","departureDate": "YYYY-MM-DD","transportFromPreviousCity": "train | bus | flight | ferry | none","activities": [string]}}
  ]
}}
"""


def output_json_random_five_trips(start_date: str, end_date: str) -> str:
    return f"""
OUTPUT:Return JSON ONLY using this structure:

{{
"trips": [
  {{"startingPoint": string,"startDate": "{start_date}","endDate": "{end_date}","tripLengthDays": number,"strategy": "random","plan": [{{"city": string,"country": string,"iata": string,"days": number,"arrivalDate": "YYYY-MM-DD","departureDate": "YYYY-MM-DD","transportFromPreviousCity": "train | bus | flight | ferry | none","activities": [string]}}]}}
  ]
}}
"""


def stepwise_next_stop_prompt(
    *,
    strategy: str,
    lang_name: str,
    current_airport: str,
    current_city_label: str,
    prefs: str,
    remaining_days: int,
    cand_block: str,
    avoid: str,
) -> str:
    return (
        f"{system_stepwise_one_stop(lang_name)}"
        "USER:\n"
        f"Strategy: {strategy}\n"
        f"Current departure airport (IATA): {current_airport}\n"
        f"Current location label: {current_city_label}\n"
        f"Preferences: {prefs}\n"
        "Total days still to assign (this stop + any later stops before return home): "
        f"{remaining_days}\n\n"
        f"Candidate destinations reachable from {current_airport} by the listed transport. "
        "You MUST pick one row and copy city, country, IATA, and transport exactly:\n"
        f"{cand_block}\n\n"
        f"Avoid repeating these cities already visited on this trip: {avoid}\n\n"
        "Rules:\n"
        "- Output JSON only, one object.\n"
        "- Do not always pick the first candidate. Choose a destination that adds variety to the route.\n"
        "- Keep the route geographically logical: prefer nearby forward movement over zig-zags or backtracking.\n"
        "- Choose the candidate whose listed transport best fits the trip flow; do not force ground transport or flights.\n"
        "- Avoid choosing another airport/city in the exact same metro area unless it is genuinely the intended destination.\n"
        f'- "days": integer from 1 to {remaining_days} (days spent at the chosen city before moving on).\n'
        f'- If all remaining days should be spent at this city (last stop before return home), set "days" to {remaining_days}.\n'
        '- "transportFromPreviousCity": use the transport listed on the chosen candidate row.\n\n'
        "Return JSON only with this shape:\n"
        '{"city":"","country":"","iata":"","days":1,"transportFromPreviousCity":"flight","activities":["",""]}\n'
    )
