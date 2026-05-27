from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from travel_types.plan_generation import (
    GenerationRequest,
    GeocodeRequest,
    RandomGenerationRequest,
    geocode_places,
    generate_random_plan,
    generate_unvisited_plan,
    generate_visited_plan,
)
from travel_types import UnvisitedGenerationRequest

router = APIRouter()


@router.post("/api/geocode")
async def batch_geocode(request: GeocodeRequest):
    return await geocode_places(request)


@router.post("/generate_travel_plans/visited")
async def travel_plans_visited(request: GenerationRequest, db: Session = Depends(get_db)):
    return await generate_visited_plan(request, db)


@router.post("/generate_travel_plans/unvisited")
async def travel_plans_unvisited(request: UnvisitedGenerationRequest, db: Session = Depends(get_db)):
    return await generate_unvisited_plan(request, db)


@router.post("/generate_travel_plans/random")
async def travel_plans_random(request: RandomGenerationRequest, db: Session = Depends(get_db)):
    return await generate_random_plan(request, db)
