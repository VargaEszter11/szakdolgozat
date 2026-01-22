# logic: api(possibble destinations) -> draft plan -> api -> final plan

from ast import List
import json
import re
from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
from utils.coordinates import geocode_place
from utils.nearest_airport import nearest_airport

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
async def generate_plan_with_location(draft_plan_func, *args, starting_point: str, **kwargs):
    lat, lon = await get_coordinates(starting_point)
    airport = nearest_airport(lat, lon)
    draft_plan = await draft_plan_func(*args, **kwargs)
    return {
        "draft_plan": draft_plan,
        "starting_point_coords": {"lat": lat, "lon": lon},
        "nearest_airport": airport
    }

# Generate travel plan functions
async def generate_travel_plan_visited(
    startingPoint: str,
    travelLength: int,
    preferences: List[str],
    visitedPlaces: List[str],
) -> str:
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

Constraint:
ONLY choose destinations from this list:
{visitedPlaces}

TASK:
Generate a realistic draft itinerary.

Rules:
- Use the starting point only as a transport hub.
- Choose geographically reasonable routes.
- Sum of days MUST equal {travelLength}.
- At the end of the trip, return to the starting point.

OUTPUT:
Return JSON ONLY using this structure:

{{
  "startingPoint": string,
  "tripLengthDays": number,
  "strategy": "visited",
  "plan": [
    {{"city": string,"country": string,"days": number,"transportFromPreviousCity": "train | bus | flight | ferry | none"}}
  ]
}}
"""
    return await call_ollama_api(prompt)


async def generate_travel_plan_unvisited(
    startingPoint: str,
    travelLength: int,
    preferences: List[str],
    visitedPlaces: List[str]
) -> str:
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

Constraint:
EXCLUDE the following places completely:
{visitedPlaces}

TASK:
Generate a realistic draft itinerary using ONLY new destinations.

Rules:
- Use the starting point only as a transport hub.
- Do not include excluded places.
- Sum of days MUST equal {travelLength}.
- At the end of the trip, return to the starting point.

OUTPUT:
Return JSON ONLY using this structure:

{{
  "startingPoint": string,
  "tripLengthDays": number,
  "strategy": "unvisited",
  "plan": [
    {{"city": string,"country": string,"days": number,"transportFromPreviousCity": "train | bus | flight | ferry | none"}}
  ]
}}
"""
    return await call_ollama_api(prompt)


async def generate_travel_plan_random(
    startingPoint: str,
    travelLength: int,
    preferences: List[str]
) -> str:
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

TASK:
Generate 5 realistic random European itineraries.

Rules:
- Starting point is used only as a transport hub.
- Cities may be in different countries.
- Routes must be geographically reasonable.
- Sum of days MUST equal {travelLength}.
- At the end of the trip, return to the starting point.

OUTPUT:
Return JSON ONLY using this structure:

{{
"trips": [
  {{"startingPoint": string,"tripLengthDays": number,"strategy": "random","plan": [{{"city": string,"country": string,"days": number,"transportFromPreviousCity": "train | bus | flight | ferry | none"}}]}}
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
        starting_point=request.startingPoint
    )


@app.post("/generate_travel_plans/unvisited")
async def travel_plans_unvisited(request: GenerationRequest):
    return await generate_plan_with_location(
        generate_travel_plan_unvisited,
        request.startingPoint,
        request.travelLength,
        request.preferences,
        request.visitedPlaces,
        starting_point=request.startingPoint
    )


@app.post("/generate_travel_plans/random")
async def travel_plans_random(request: RandomGenerationRequest):
    return await generate_plan_with_location(
        generate_travel_plan_random,
        request.startingPoint,
        request.travelLength,
        request.preferences,
        starting_point=request.startingPoint
    )