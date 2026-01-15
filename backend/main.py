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
async def generate_travel_plan_visited(startingPoint: str, budget: int, travelLength: int, preferences: list[str], visitedPlaces: list[str]) -> str:
    prompt = f"""
You are a travel planner AI. 

I want you to generate a detailed **travel plan** for a trip in Europe (or [continent/country]). Please follow these rules:

1. **Starting point:** {startingPoint}, use it only as a starting hub.
2. **Budget:** {budget} EUR (specify if the budget includes flights or only local transport + accommodation)  
3. **Trip duration:** {travelLength} days  
4. **Preferences:** {preferences} (e.g., history, food, nightlife, nature, hiking)  
5. **Only choose cities or countries from the list:** {visitedPlaces}  
6. **Transport types:** Suggest realistic transport between locations (train, bus, flight, ferry) with approximate costs.  
7. **Accommodation:** Suggest budget-friendly options (hostel, Airbnb, hotel) with approximate costs.  
8. **Activities:** Give brief activity suggestions per day. Include cost estimates where possible.  
9. **Output format:** Return the plan as **JSON** with the following structure:

{{
  "tripName": string,
  "startingPoint": string,
  "totalBudgetEUR": number,
  "tripLengthDays": number,
  "preferences": string[],
  "trip": [
    {{
      "day": number,
      "city": string,
      "country": string,
      "transportFromPreviousCity": {{
        "type": "train | bus | flight | ferry",
        "estimatedCostEUR": number,
        "estimatedDurationHours": number
      }},
      "accommodation": {{
        "type": "hostel | budget hotel | mid-range hotel",
        "estimatedCostEUR": number
      }},
      "activities": [
        {{
          "name": string,
          "estimatedCostEUR": number
        }}
      ],
      "estimatedDailyTotalEUR": number
    }}
  ],
  "estimatedTripTotalEUR": number
}}

10. Keep the prices **realistic and approximate**. Consider typical budget travel costs in Europe (e.g., €20-€60 per night for hostels, €5-€15 for meals, €10-€50 for trains/buses, flights €50-€150).  
11. Make it **realistic** in the given budget and travel length.
12. Choose the most reasonable transport options.
13. On the last day, the transport to the starting point should be included.
14. The duration should be exactly the same as the travel length.

Generate the JSON **only**, without extra explanations. Make the plan practical and feasible.
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
You are a travel planner AI. 

I want you to generate a detailed **travel plan** for a trip in Europe (or [continent/country]). Please follow these rules:

1. **Starting point:** {startingPoint}, use it only as a starting hub.
2. **Budget:** {budget} EUR (specify if the budget includes flights or only local transport + accommodation)  
3. **Trip duration:** {travelLength} days  
4. **Preferences:** {preferences} (e.g., history, food, nightlife, nature, hiking)  
5. **Exclude cities or countries:** {visitedPlaces}  
6. **Transport types:** Suggest realistic transport between locations (train, bus, flight, ferry) with approximate costs.  
7. **Accommodation:** Suggest budget-friendly options (hostel, Airbnb, hotel) with approximate costs.  
8. **Activities:** Give brief activity suggestions per day. Include cost estimates where possible.  
9. **Output format:** Return the plan as **JSON** with the following structure:

{{
  "tripName": string,
  "startingPoint": string,
  "totalBudgetEUR": number,
  "tripLengthDays": number,
  "preferences": string[],
  "trip": [
    {{
      "day": number,
      "city": string,
      "country": string,
      "transportFromPreviousCity": {{
        "type": "train | bus | flight | ferry",
        "estimatedCostEUR": number,
        "estimatedDurationHours": number
      }},
      "accommodation": {{
        "type": "hostel | budget hotel | mid-range hotel",
        "estimatedCostEUR": number
      }},
      "activities": [
        {{
          "name": string,
          "estimatedCostEUR": number
        }}
      ],
      "estimatedDailyTotalEUR": number
    }}
  ],
  "estimatedTripTotalEUR": number
}}

10. Keep the prices **realistic and approximate**. Consider typical budget travel costs in Europe (e.g., €20-€60 per night for hostels, €5-€15 for meals, €10-€50 for trains/buses, flights €50-€150).  
11. Make it **realistic** in the given budget and travel length.
12. Choose the most reasonable transport options.
13. On the last day, the transport to the starting point should be included.
14. The duration should be exactly the same as the travel length.

Generate the JSON **only**, without extra explanations. Make the plan practical and feasible.
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
You are a travel planner AI. 

I want you to generate a detailed **travel plan** for a trip in Europe (or [continent/country]). Please follow these rules:

1. **Starting point:** {startingPoint}, use it only as a starting hub.
2. **Budget:** {budget} EUR (specify if the budget includes flights or only local transport + accommodation)  
3. **Trip duration:** {travelLength} days  
4. **Preferences:** {preferences} (e.g., history, food, nightlife, nature, hiking)  
5. **You choose the cities and countries to visit, it can be different from the starting point.**  
6. **Transport types:** Suggest realistic transport between locations (train, bus, flight, ferry) with approximate costs and durations.  
7. **Accommodation:** Suggest budget-friendly options (hostel, Airbnb, hotel) with approximate costs.  
8. **Activities:** Give brief activity suggestions per day. Include cost estimates where possible.  
9. **Output format:** Return the plan as **JSON** with the following structure:

{{
  "tripName": string,
  "startingPoint": string,
  "totalBudgetEUR": number,
  "tripLengthDays": number,
  "preferences": string[],
  "trip": [
    {{
      "day": number,
      "city": string,
      "country": string,
      "transportFromPreviousCity": {{
        "type": "train | bus | flight | ferry",
        "estimatedCostEUR": number,
        "estimatedDurationHours": number
      }},
      "accommodation": {{
        "type": "hostel | budget hotel | mid-range hotel",
        "estimatedCostEUR": number
      }},
      "activities": [
        {{
          "name": string,
          "estimatedCostEUR": number
        }}
      ],
      "estimatedDailyTotalEUR": number
    }}
  ],
  "estimatedTripTotalEUR": number
}}

10. Keep the prices **realistic and approximate**. Consider typical budget travel costs in Europe (e.g., €20-€60 per night for hostels, €5-€15 for meals, €10-€50 for trains/buses, flights €50-€150).  
11. Make it **realistic** in the given budget and travel length.
12. Choose the most **reasonable** transport options.
13. On the last day, the transport to the starting point should be included.
14. The duration should be exactly the same as the travel length.

Generate the JSON **only**, without extra explanations. Make the plan practical and feasible.
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