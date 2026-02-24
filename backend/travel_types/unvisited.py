from typing import List
from .ollama_client import call_ollama_api


async def generate_travel_plan_unvisited(
    startingPoint: str,
    travelLength: int,
    preferences: List[str],
    visitedPlaces: List[str],
    direct_destinations: List[dict] = None,
) -> str:
    """Generate travel plan for unvisited places."""
    # Filter out visited places from direct destinations
    available_destinations = []
    if direct_destinations:
        visited_lower = [place.lower() for place in visitedPlaces]
        for dest in direct_destinations:
            city = dest.get("city")
            if city:
                city_lower = city.lower()
                if not any(visited in city_lower or city_lower in visited for visited in visited_lower):
                    available_destinations.append(f"{dest.get('city')}, {dest.get('country')} (IATA: {dest.get('iata')})")
    
    destinations_info = "\n".join(available_destinations) if available_destinations else "No direct flights available from starting airport."
    
    prompt = f"""
SYSTEM:
You are a travel planning AI.
DO NOT estimate prices.
DO NOT mention costs.
DO NOT add activities.

USER:
Starting point: {startingPoint}
Trip length: {travelLength} days
Preferences: {preferences}

Available destinations with direct flights (excluding visited places):
{destinations_info}

Constraint:
EXCLUDE the following places completely:
{visitedPlaces}

TASK:
Generate a realistic draft itinerary using ONLY new destinations that have direct flights available.

Rules:
- Use the starting point only as a transport hub.
- ONLY use cities from the available destinations list above.
- Do not include excluded places.
- Sum of days MUST equal {travelLength}.
- At the end of the trip, return to the starting point.
- Choose the BEST transport method for each segment: use "flight" only when it's the most practical option (long distances, islands, time constraints), otherwise prefer "train" or "bus" for shorter distances.
- For each destination, suggest 1-2 realistic activities/programs (e.g., "Museum visit", "City tour", "Beach day", "Historical site", "Local cuisine experience").

OUTPUT:
Return JSON ONLY using this structure:

{{
  "startingPoint": string,
  "tripLengthDays": number,
  "strategy": "unvisited",
  "plan": [
    {{"city": string,"country": string,"iata": string,"days": number,"transportFromPreviousCity": "train | bus | flight | ferry | none","activities": [string]}}
  ]
}}
"""
    return await call_ollama_api(prompt)
