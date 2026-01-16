# TODO: 3 endpoint: random generation, generate from visited places, generate from unvisited places
# logic: draft plan -> api -> final plan

import json
import re
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

app = FastAPI()

OLLAMA_API_URL = "http://localhost:11434/api/generate"
# Using gemma3:27b - good for travel planning, fits in memory
# Other options: "llama3.2" (smaller, faster) or "gemma3" (4B model, very fast)
MODEL_NAME = "llama3.2"


class GenerationRequest(BaseModel):
    visitedPlaces: list[str]
    startingPoint: str
    budget: int
    travelLength: int
    preferences: list[str] = []


class RandomGenerationRequest(BaseModel):
    startingPoint: str
    budget: int
    travelLength: int
    preferences: list[str] = []

# Generic function to call Ollama API with a prompt
async def call_ollama_api(prompt: str) -> str:
    print("=== PROMPT ===")
    print(prompt)

    payload = {
        "model": MODEL_NAME,
        "stream": False,
        "prompt": prompt,
    }

    try:
        # No timeout - let the AI generation take as long as it needs
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(OLLAMA_API_URL, json=payload)
            print(f"=== RESPONSE STATUS: {response.status_code} ===")

            if response.status_code != 200:
                print(f"=== ERROR RESPONSE BODY ===")
                print(response.text)

            response.raise_for_status()
            data = response.json()
            print(f"=== RESPONSE DATA ===")
            print(data)
            return data["response"]
    except Exception as e:
        print(f"=== ERROR ===")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        raise


# Generate travel plan based on visited places
async def generate_travel_plan_visited(
    startingPoint: str,
    travelLength: int,
    preferences: list[str],
    visitedPlaces: list[str],
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
- Choose geographically reasonable routes.
- At the end of the trip, return to the starting point.

OUTPUT:
Return JSON ONLY using this structure:

{{
  "startingPoint": string,
  "tripLengthDays": number,
  "strategy": "visited",
  "plan": [
    {{
      "city": string,
      "country": string,
      "days": number,
      "transportFromPreviousCity": "train | bus | flight | ferry | none"
    }}
  ]
}}
"""
    return await call_ollama_api(prompt)


@app.post("/generate_travel_plans/visited")
async def travel_plans_visited(request: GenerationRequest):
    return {
        "draft_plan": await generate_travel_plan_visited(
            request.startingPoint,
            request.travelLength,
            request.preferences,
            request.visitedPlaces
        )
    }

# Generate travel plan based on unvisited places
async def generate_travel_plan_unvisited(
    startingPoint: str,
    travelLength: int,
    preferences: list[str],
    visitedPlaces: list[str]
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
- Choose geographically reasonable routes.
- At the end of the trip, return to the starting point.

OUTPUT:
Return JSON ONLY using this structure:

{{
  "startingPoint": string,
  "tripLengthDays": number,
  "strategy": "unvisited",
  "plan": [
    {{
      "city": string,
      "country": string,
      "days": number,
      "transportFromPreviousCity": "train | bus | flight | ferry | none"
    }}
  ]
}}
"""
    return await call_ollama_api(prompt)


@app.post("/generate_travel_plans/unvisited")
async def travel_plans_unvisited(request: GenerationRequest):
    return {
        "draft_plan": await generate_travel_plan_unvisited(
            request.startingPoint,
            request.travelLength,
            request.preferences,
            request.visitedPlaces
        )
    }

# Generate random travel plan
async def generate_travel_plan_random(
    startingPoint: str,
    travelLength: int,
    preferences: list[str]
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
Generate a realistic random European itinerary.

Rules:
- Starting point is used only as a transport hub.
- Cities may be in different countries.
- Routes must be geographically reasonable.
- Sum of days MUST equal {travelLength}.
- At the end of the trip, return to the starting point.

OUTPUT:
Return JSON ONLY using this structure:

{{
  "startingPoint": string,
  "tripLengthDays": number,
  "strategy": "random",
  "plan": [
    {{
      "city": string,
      "country": string,
      "days": number,
      "transportFromPreviousCity": "train | bus | flight | ferry | none"
    }}
  ]
}}
"""
    return await call_ollama_api(prompt)

@app.post("/generate_travel_plans/random")
async def travel_plans_random(request: RandomGenerationRequest):
    return {
        "draft_plan": await generate_travel_plan_random(
            request.startingPoint,
            request.travelLength,
            request.preferences
        )
    }