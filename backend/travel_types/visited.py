from typing import List
from .ollama_client import call_ollama_api


async def generate_travel_plan_visited(
    startingPoint: str,
    travelLength: int,
    preferences: List[str],
    visitedPlaces: List[str],
    direct_destinations: List[dict] = None,
    start_date: str = None,
    end_date: str = None,
) -> str:
    """Generate travel plan for visited places."""
    available_places = []
    if direct_destinations:
        dest_cities = {(dest.get("city") or "").lower(): dest for dest in direct_destinations if dest.get("city")}
        for place in visitedPlaces:
            place_lower = place.lower()
            for city_key, dest in dest_cities.items():
                if city_key and (place_lower in city_key or city_key in place_lower):
                    available_places.append(f"{dest.get('city')}, {dest.get('country')} (IATA: {dest.get('iata')})")
    
    direct_destinations_str = "\n".join(available_places) if available_places else "No direct flights available from starting airport."
    
    prompt = f"""
SYSTEM:
You are a travel planning AI.
DO NOT estimate prices.
DO NOT mention costs.

USER:
Starting point: {startingPoint}
Start date: {start_date}
End date: {end_date}
Trip length: {travelLength} days
Preferences: {preferences}

Available destinations with direct flights:
{direct_destinations_str} 

Constraint:
ONLY choose destinations from this list of visited places that have direct flights:
{visitedPlaces}

TASK:
Generate a realistic draft itinerary using ONLY destinations with direct flights available.
The trip must start on {start_date} and end on {end_date}.

Rules:
- Use the starting point only as a transport hub.
- ONLY use cities from the available destinations list above.
- Choose geographically reasonable routes.
- Sum of days MUST equal {travelLength}.
- Assign concrete arrival and departure dates for each stop, starting from {start_date}.
- At the end of the trip, return to the starting point by {end_date}.
- Choose the BEST transport method for each segment: use "flight" only when it's the most practical option (long distances, islands, time constraints), otherwise prefer "train" or "bus" for shorter distances.
- For each destination, suggest 1-2 realistic activities/programs (e.g., "Museum visit", "City tour", "Beach day", "Historical site", "Local cuisine experience").

OUTPUT:
Return JSON ONLY using this structure:

{{
  "startingPoint": string,
  "startDate": "{start_date}",
  "endDate": "{end_date}",
  "tripLengthDays": number,
  "strategy": "visited",
  "plan": [
    {{"city": string,"country": string,"iata": string,"days": number,"arrivalDate": "YYYY-MM-DD","departureDate": "YYYY-MM-DD","transportFromPreviousCity": "train | bus | flight | ferry | none","activities": [string]}}
  ]
}}
"""
    return await call_ollama_api(prompt)
