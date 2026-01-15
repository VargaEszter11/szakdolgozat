#TODO: 3 endpoint: random generation, generate from visited places, generate from unvisited places
#model: mixtral

import json
import re
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

app = FastAPI()

OLLAMA_API_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "mixtral"

class GenerationRequest(BaseModel):
    pageContent: str
    visitedPlaces: list[str]

# Generic function to call Ollama API with a prompt
async def call_ollama_api(prompt: str) -> str:
    print(prompt)
    
    payload = {
        "model": MODEL_NAME,
        "stream": False,
        "messages": [{"role": "user", "content": prompt}],
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(OLLAMA_API_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

# Generate travel plan based on visited places
async def generate_travel_plan_visited(pageContent: str, visitedPlaces: list[str]) -> str:
    prompt = f"""



"""
    return await call_ollama_api(prompt)
    
@app.post("/generate_travel_plans/visited")
async def travel_plans_visited(request: GenerationRequest):
    try:
        travel_plan = await generate_travel_plan_visited(request.pageContent, request.visitedPlaces)
        return {"travel_plan": travel_plan}
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# Generate travel plan based on unvisited places
async def generate_travel_plan_unvisited(pageContent: str, visitedPlaces: list[str]) -> str:
    prompt = f"""



"""
    return await call_ollama_api(prompt)
    
@app.post("/generate_travel_plans/unvisited")
async def travel_plans_unvisited(request: GenerationRequest):
    try:
        travel_plan = await generate_travel_plan_unvisited(request.pageContent, request.visitedPlaces)
        return {"travel_plan": travel_plan}
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# Generate random travel plan
async def generate_travel_plan_random(pageContent: str) -> str:
    prompt = f"""



"""
    return await call_ollama_api(prompt)
    
@app.post("/generate_travel_plans/random")
async def travel_plans_random(request: GenerationRequest):
    try:
        travel_plan = await generate_travel_plan_random(request.pageContent)
        return {"travel_plan": travel_plan}
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=str(e))