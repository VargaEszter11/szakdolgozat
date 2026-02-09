# logic: api(possibble destinations) -> draft plan -> api -> final plan

import json
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from utils.coordinates import geocode_place
from utils.nearest_airport import nearest_airport, get_direct_destinations
from utils.flight_pricing import validate_travel_plan
from travel_types import (
    generate_travel_plan_visited,
    generate_travel_plan_unvisited,
    generate_travel_plan_random,
)

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


# Endpoints
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