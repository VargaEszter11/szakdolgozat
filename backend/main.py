# logic: api(possibble destinations) -> draft plan -> api -> final plan

from ast import List
import json
import re
from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
from utils.coordinates import geocode_place
from utils.nearest_airport import nearest_airport, get_direct_destinations
from utils.flight_pricing import validate_travel_plan, get_city_airport_code

app = FastAPI()

OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma3:4b"


class GenerationRequest(BaseModel):
    visitedPlaces: List[str]
    startingPoint: str
    budget: int
    travelLength: int
    preferences: List[str] = []


class RandomGenerationRequest(BaseModel):
    startingPoint: str
    budget: int
    travelLength: int
    preferences: List[str] = []

async def call_ollama_api(prompt: str) -> str:
    payload = {
        "model": MODEL_NAME,
        "stream": False,
        "prompt": prompt,
    }
    async with httpx.AsyncClient(timeout=None) as client:
        response = await client.post(OLLAMA_API_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["response"]


# Get coordinates for a place name
async def get_coordinates(place_name: str):
    try:
        return await geocode_place(place_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Get nearest airport and generate plan
async def generate_plan_with_location(draft_plan_func, *args, starting_point: str, budget: int = None, **kwargs):
    lat, lon = await get_coordinates(starting_point)
    airport = await nearest_airport(lat, lon)
    
    # Get direct destinations from the nearest airport
    direct_destinations = []
    if airport and airport.get("iata"):
        direct_destinations = await get_direct_destinations(airport["iata"])
    
    # Pass direct destinations to the draft plan function
    draft_plan_raw = await draft_plan_func(*args, direct_destinations=direct_destinations, **kwargs)
    
    # Parse the draft plan (it's a JSON string from Ollama)
    try:
        import json
        # Try to extract JSON from the response
        draft_plan_text = draft_plan_raw.strip()
        # Remove markdown code blocks if present
        if draft_plan_text.startswith("```"):
            lines = draft_plan_text.split("\n")
            draft_plan_text = "\n".join(lines[1:-1]) if len(lines) > 2 else draft_plan_text
        draft_plan = json.loads(draft_plan_text)
    except:
        draft_plan = {"raw": draft_plan_raw}
    
    # Validate the plan if budget is provided
    validation = None
    if budget and airport and airport.get("iata") and isinstance(draft_plan, dict):
        # Get travelLength from args (it's the second positional argument after startingPoint)
        travel_length = args[1] if len(args) > 1 else 7
        
        # Check if this is a random plan with multiple trips
        if "trips" in draft_plan:
            # Calculate prices for all trips first, then select the best one
            trips = draft_plan.get("trips", [])
            validated_trips = []
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                # Calculate prices for all trips
                for trip in trips:
                    trip_validation = await validate_travel_plan(trip, airport["iata"], budget, travel_length)
                    validated_trips.append({
                        "trip": trip,
                        "validation": trip_validation
                    })
                
                # Check if we have at least one valid plan
                valid_trips = [vt for vt in validated_trips if vt["validation"].get("valid", False)]
                if valid_trips:
                    break  # We have at least one valid plan, exit retry loop
                
                # If no valid plans, regenerate
                if retry_count < max_retries - 1:
                    validated_trips = []  # Clear previous attempts
                    draft_plan_raw = await draft_plan_func(*args, direct_destinations=direct_destinations, **kwargs)
                    try:
                        draft_plan_text = draft_plan_raw.strip()
                        if draft_plan_text.startswith("```"):
                            lines = draft_plan_text.split("\n")
                            draft_plan_text = "\n".join(lines[1:-1]) if len(lines) > 2 else draft_plan_text
                        draft_plan = json.loads(draft_plan_text)
                        trips = draft_plan.get("trips", [])
                    except:
                        break  # If parsing fails, break and use what we have
                
                retry_count += 1
            
            # Sort by: validity first, then by score (highest first), then by total price (lowest first)
            validated_trips.sort(key=lambda x: (
                x["validation"]["valid"],
                x["validation"]["score"],
                -x["validation"]["total_price"]  # Negative for ascending (lower price = better)
            ), reverse=True)
            
            # Select the best trip (first after sorting)
            best_trip = validated_trips[0] if validated_trips else None
            
            return {
                "draft_plan": {
                    "selected_trip": best_trip["trip"] if best_trip else None,
                    "all_trips": [vt["trip"] for vt in validated_trips] if validated_trips else trips,
                    "validations": [vt["validation"] for vt in validated_trips] if validated_trips else []
                },
                "starting_point_coords": {"lat": lat, "lon": lon},
                "nearest_airport": airport,
                "validation": best_trip["validation"] if best_trip else None,
                "best_trip_index": 0 if best_trip else None
            }
        else:
            # Single plan validation - retry until we get a valid plan
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                validation = await validate_travel_plan(draft_plan, airport["iata"], budget, travel_length)
                
                # If plan is valid, break
                if validation and validation.get("valid"):
                    break
                
                # If invalid, regenerate plan
                if retry_count < max_retries - 1:
                    draft_plan_raw = await draft_plan_func(*args, direct_destinations=direct_destinations, **kwargs)
                    try:
                        draft_plan_text = draft_plan_raw.strip()
                        if draft_plan_text.startswith("```"):
                            lines = draft_plan_text.split("\n")
                            draft_plan_text = "\n".join(lines[1:-1]) if len(lines) > 2 else draft_plan_text
                        draft_plan = json.loads(draft_plan_text)
                    except:
                        break  # If parsing fails, break and use what we have
                
                retry_count += 1
            
            # If still invalid after retries, use the last validation
            if not validation:
                validation = {
                    "valid": False,
                    "reason": "Plan validation not completed",
                    "total_price": 0,
                    "score": 0
                }
    
    return {
        "draft_plan": draft_plan,
        "starting_point_coords": {"lat": lat, "lon": lon},
        "nearest_airport": airport,
        "validation": validation
    }

# Generate travel plan functions
async def generate_travel_plan_visited(
    startingPoint: str,
    travelLength: int,
    preferences: List[str],
    visitedPlaces: List[str],
    direct_destinations: List[dict] = None,
) -> str:
    # Filter visited places to only include those with direct flights
    available_places = []
    if direct_destinations:
        dest_cities = {(dest.get("city") or "").lower(): dest for dest in direct_destinations if dest.get("city")}
        for place in visitedPlaces:
            # Try to match visited places with available destinations
            place_lower = place.lower()
            for city_key, dest in dest_cities.items():
                if city_key and (place_lower in city_key or city_key in place_lower):
                    available_places.append(f"{dest.get('city')}, {dest.get('country')} (IATA: {dest.get('iata')})")
    
    direct_destinations = "\n".join(available_places) if available_places else "No direct flights available from starting airport."
    
    prompt = f"""
SYSTEM:
You are a travel planning AI.
DO NOT estimate prices.
DO NOT mention costs.
DO NOT add activities.
ONLY decide cities, order, transport type, and number of days.

USER:
Starting point: {startingPoint}
Trip length: {travelLength} days
Preferences: {preferences}

Available destinations with direct flights:
{direct_destinations} 

Constraint:
ONLY choose destinations from this list of visited places that have direct flights:
{visitedPlaces}

TASK:
Generate a realistic draft itinerary using ONLY destinations with direct flights available.

Rules:
- Use the starting point only as a transport hub.
- ONLY use cities from the available destinations list above.
- ONLY choose destinations in Spain (ES), Germany (DE), or United Kingdom (GB).
- Choose geographically reasonable routes.
- Sum of days MUST equal {travelLength}.
- At the end of the trip, return to the starting point.
- Choose the BEST transport method for each segment: use "flight" only when it's the most practical option (long distances, islands, time constraints), otherwise prefer "train" or "bus" for shorter distances.
- For each destination, suggest 1-2 realistic activities/programs (e.g., "Museum visit", "City tour", "Beach day", "Historical site", "Local cuisine experience").

OUTPUT:
Return JSON ONLY using this structure:

{{
  "startingPoint": string,
  "tripLengthDays": number,
  "strategy": "visited",
  "plan": [
    {{"city": string,"country": string,"iata": string,"days": number,"transportFromPreviousCity": "train | bus | flight | ferry | none","activities": [string]}}
  ]
}}
"""
    return await call_ollama_api(prompt)


async def generate_travel_plan_unvisited(
    startingPoint: str,
    travelLength: int,
    preferences: List[str],
    visitedPlaces: List[str],
    direct_destinations: List[dict] = None,
) -> str:
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
- ONLY choose destinations in Spain (ES), Germany (DE), or United Kingdom (GB).
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


async def generate_travel_plan_random(
    startingPoint: str,
    travelLength: int,
    preferences: List[str],
    direct_destinations: List[dict] = None,
) -> str:
    # Use all direct destinations for random plans
    available_destinations = []
    if direct_destinations:
        for dest in direct_destinations:
            city = dest.get("city")
            if city:  # Only include destinations with valid city names
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

#Endpoints
@app.post("/generate_travel_plans/visited")
async def travel_plans_visited(request: GenerationRequest):
    return await generate_plan_with_location(
        generate_travel_plan_visited,
        request.startingPoint,
        request.travelLength,
        request.preferences,
        request.visitedPlaces,
        starting_point=request.startingPoint,
        budget=request.budget
    )


@app.post("/generate_travel_plans/unvisited")
async def travel_plans_unvisited(request: GenerationRequest):
    return await generate_plan_with_location(
        generate_travel_plan_unvisited,
        request.startingPoint,
        request.travelLength,
        request.preferences,
        request.visitedPlaces,
        starting_point=request.startingPoint,
        budget=request.budget
    )


@app.post("/generate_travel_plans/random")
async def travel_plans_random(request: RandomGenerationRequest):
    return await generate_plan_with_location(
        generate_travel_plan_random,
        request.startingPoint,
        request.travelLength,
        request.preferences,
        starting_point=request.startingPoint,
        budget=request.budget
    )