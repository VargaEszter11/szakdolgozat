from typing import List
from .ollama_client import call_ollama_api


async def generate_travel_plan_random(
    startingPoint: str,
    travelLength: int,
    preferences: List[str],
    direct_destinations: List[dict] = None,
) -> str:
    """Generate random travel plans."""
    # Use all direct destinations for random plans
    available_destinations = []
    if direct_destinations:
        for dest in direct_destinations:
            city = dest.get("city")
            if city:
                available_destinations.append(f"{city}, {dest.get('country')} (IATA: {dest.get('iata')})")
    
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

Available destinations with direct flights:
{destinations_info}

TASK:
Generate 5 realistic random European itineraries using ONLY destinations with direct flights available.

Rules:
- Starting point is used only as a transport hub.
- ONLY use cities from the available destinations list above.
- ONLY choose destinations in Spain (ES), Germany (DE), or United Kingdom (GB).
- Cities may be in different countries but must be ES, DE, or GB.
- Routes must be geographically reasonable.
- Sum of days MUST equal {travelLength}.
- At the end of the trip, return to the starting point.
- Choose the BEST transport method for each segment: use "flight" only when it's the most practical option (long distances, islands, time constraints), otherwise prefer "train" or "bus" for shorter distances.
- For each destination, suggest 1-2 realistic activities/programs (e.g., "Museum visit", "City tour", "Beach day", "Historical site", "Local cuisine experience").

OUTPUT:
Return JSON ONLY using this structure:

{{
"trips": [
  {{"startingPoint": string,"tripLengthDays": number,"strategy": "random","plan": [{{"city": string,"country": string,"iata": string,"days": number,"transportFromPreviousCity": "train | bus | flight | ferry | none","activities": [string]}}]}}
  ]
}}
"""
    return await call_ollama_api(prompt)
