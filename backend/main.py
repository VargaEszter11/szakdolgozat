#TODO: 3 endpoint: random generation, generate from visited places, generate from unvisited places
#model: mixtral

import json
import re
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

app = FastAPI()

OLLAMA_API_URL = "http://localhost:11434/api/generate"
# Using gemma3:27b - good for travel planning, fits in memory
# Other options: "llama3.2" (smaller, faster) or "gemma3" (4B model, very fast)
MODEL_NAME = "gemma3"

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
async def generate_travel_plan_visited(startingPoint: str, budget: int, travelLength: int, preferences: list[str], visitedPlaces: list[str]) -> str:
    prompt = f"""

You are a professional travel planner. Create a trip in Europe based on the following criteria:

-Starting point: {startingPoint}

-Budget: {budget} EUR

-Travel length: {travelLength} days

-Preferences: {preferences}

Only choose from these places: {visitedPlaces}

Requirements:

-Do not plan any activities, sightseeing, or overnight stays in the starting city. The starting point is only used as a transportation hub.

-Suggest different cities for the trip to maximize variety.

-Include accommodation, transportation between cities, activities, and approximate daily costs.

-On the last day, return to the starting point.

-Only suggest possible cities and travel options, don't make up any cities or travel options.

-Where flight is the only option, don't suggest any other travel options.

-Don't make it too complex, keep it simple and easy to understand.

Return the itinerary in JSON format.

"""
    return await call_ollama_api(prompt)
    
@app.post("/generate_travel_plans/visited")
async def travel_plans_visited(request: GenerationRequest):
    try:
        travel_plan = await generate_travel_plan_visited(request.startingPoint, request.budget, request.travelLength, request.preferences, request.visitedPlaces)
        return {"travel_plan": travel_plan}
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# Generate travel plan based on unvisited places
async def generate_travel_plan_unvisited(startingPoint: str, budget: int, travelLength: int, preferences: list[str], visitedPlaces: list[str]) -> str:
    prompt = f"""
You are a professional travel planner. Create a trip in Europe based on the following criteria:

-Starting point: {startingPoint}

-Budget: {budget} EUR

-Travel length: {travelLength} days

-Preferences: {preferences}

Exclude these places from the trip: {visitedPlaces}

Requirements:

-Do not plan any activities, sightseeing, or overnight stays in the starting city. The starting point is only used as a transportation hub.

-Suggest different cities for the trip to maximize variety.

-Include accommodation, transportation between cities, activities, and approximate daily costs.

-On the last day, return to the starting point.

-Only suggest possible cities and travel options, don't make up any cities or travel options.

-Where flight is the only option, don't suggest any other travel options.

-Don't make it too complex, keep it simple and easy to understand.

Return the itinerary in JSON format.

"""
    return await call_ollama_api(prompt)
    
@app.post("/generate_travel_plans/unvisited")
async def travel_plans_unvisited(request: GenerationRequest):
    try:
        travel_plan = await generate_travel_plan_unvisited(request.startingPoint, request.budget, request.travelLength, request.preferences, request.visitedPlaces)
        return {"travel_plan": travel_plan}
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# Generate random travel plan
async def generate_travel_plan_random(startingPoint: str, budget: int, travelLength: int, preferences: list[str]) -> str:
    prompt = f"""
You are a professional travel planner. Create a trip in Europe based on the following criteria:

-Starting point: {startingPoint}

-Budget: {budget} EUR

-Travel length: {travelLength} days

-Preferences: {preferences}

Requirements:

-Do not plan any activities, sightseeing, or overnight stays in the starting city. The starting point is only used as a transportation hub.

-Suggest different cities for the trip to maximize variety.

-Include accommodation, transportation between cities, activities, and approximate daily costs.

-Only suggest possible cities and travel options, don't make up any cities or travel options.

-Where flight is the only option, don't suggest any other travel options.

Return the itinerary in JSON format
"""
    return await call_ollama_api(prompt)
    
@app.post("/generate_travel_plans/random")
async def travel_plans_random(request: RandomGenerationRequest):
    try:
        travel_plan = await generate_travel_plan_random(request.startingPoint, request.budget, request.travelLength, request.preferences)
        return {"travel_plan": travel_plan}
    except Exception as e:
        print(f"=== ENDPOINT ERROR ===")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))