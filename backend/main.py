# logic: api(possibble destinations) -> draft plan -> api -> final plan
# next: create realistic plans

import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv()

import json
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from utils.coordinates import geocode_place
from utils.nearest_airport import nearest_airport
from utils.direct_destinations_cache import get_direct_destinations_cached
from utils.plan_enrichment import normalize_planner_response
from travel_types import (
    generate_travel_plan_visited,
    generate_travel_plan_unvisited,
    generate_travel_plan_random,
    UnvisitedGenerationRequest,
    build_unvisited_forbidden_places,
    merge_exclusion_lists,
)

# Database imports
from database import crud
from database.database import engine, Base, get_db
from routers import users, planned_trips, trip_stops, visited_places, auth
from middleware.request_logging import RequestLoggingMiddleware
from utils.console_logging import attach_api_loggers_to_console

# Create FastAPI app
app = FastAPI(
    title="TravelApp API",
    description="API for travel planning and visited places tracking",
    version="1.0.0"
)

# Inbound API logs print to the terminal (stderr)
attach_api_loggers_to_console()

# Create database tables on startup
@app.on_event("startup")
def startup_event():
    """Create database tables on application startup"""
    Base.metadata.create_all(bind=engine)
    # AirLabs route imports are intentionally manual. Do not call data importers here.
    from database.schema_patches import apply_startup_schema_patches

    apply_startup_schema_patches()
    from utils.place_image_upload import ensure_place_images_dir

    ensure_place_images_dir()

app.add_middleware(RequestLoggingMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers for database operations
app.include_router(auth.router, prefix="/api", tags=["authentication"])
app.include_router(users.router, prefix="/api", tags=["users"])
app.include_router(planned_trips.router, prefix="/api", tags=["trips"])
app.include_router(trip_stops.router, prefix="/api", tags=["stops"])
app.include_router(visited_places.router, prefix="/api", tags=["places"])


class GenerationRequest(BaseModel):
    visitedPlaces: List[str]
    extraPlaces: List[str] = []
    startingPoint: str
    budget: Optional[int] = None
    startDate: str
    endDate: str
    preferences: List[str] = []
    language: str = "en"
    userId: Optional[int] = None
    plannerUserId: Optional[int] = None


class RandomGenerationRequest(BaseModel):
    startingPoint: str
    budget: Optional[int] = None
    startDate: str
    endDate: str
    preferences: List[str] = []
    language: str = "en"
    userId: Optional[int] = None
    plannerUserId: Optional[int] = None


class GeocodeRequest(BaseModel):
    places: List[str]
    language: str = "en"


def resolve_llm_provider(db: Optional[Session], user_id: Optional[int]) -> str:
    from travel_types.llm_client import normalize_llm_provider

    if db is not None and user_id is not None:
        user = crud.get_user(db, user_id)
        if user is not None:
            raw = getattr(user, "preferred_llm_provider", None)
            if raw:
                return normalize_llm_provider(str(raw))
    return normalize_llm_provider(os.getenv("DEFAULT_LLM_PROVIDER"))


def planner_account_id(request) -> Optional[int]:
    """User id for loading planner preferences (LLM provider), independent of trip logic userId."""
    pid = getattr(request, "plannerUserId", None)
    if pid is not None:
        return pid
    return getattr(request, "userId", None)


async def get_coordinates(place_name: str):
    try:
        return await geocode_place(place_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/geocode")
async def batch_geocode(request: GeocodeRequest):
    """Return coordinates for a list of place names (e.g. 'City, Country'). Same order as input; null for failed."""
    result = []
    for place in request.places:
        if not (place and str(place).strip()):
            result.append(None)
            continue
        try:
            lat, lon = await geocode_place(str(place).strip(), language=request.language)
            result.append({"lat": lat, "lon": lon})
        except Exception:
            result.append(None)
    return result


# Get nearest airport and generate plan
async def generate_plan_with_location(
    draft_plan_func,
    *args,
    starting_point: str,
    budget: int = None,
    start_date: str = None,
    end_date: str = None,
    db: Optional[Session] = None,
    **kwargs,
):
    lat, lon = await get_coordinates(starting_point)
    airport = await nearest_airport(lat, lon, db=db)
    
    # Get direct destinations from the nearest airport (DB cache when session available)
    direct_destinations = []
    if airport and airport.get("iata"):
        direct_destinations = await get_direct_destinations_cached(db, airport["iata"])
    
    draft_plan_raw = await draft_plan_func(
        *args,
        direct_destinations=direct_destinations,
        starting_airport_iata=(airport or {}).get("iata"),
        start_date=start_date,
        end_date=end_date,
        **kwargs,
    )
    
    # Parse the draft plan (it's a JSON string from the LLM)
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
    
    # Fix AI-generated dates/lengths to match user's actual input
    if isinstance(draft_plan, dict) and start_date and end_date:
        travel_length_user = args[1] if len(args) > 1 else 7
        if "trips" in draft_plan:
            for trip in draft_plan.get("trips", []):
                trip["startDate"] = start_date
                trip["endDate"] = end_date
                trip["tripLengthDays"] = travel_length_user
        else:
            draft_plan["startDate"] = start_date
            draft_plan["endDate"] = end_date
            draft_plan["tripLengthDays"] = travel_length_user
    
    merged_plan = normalize_planner_response(draft_plan)

    return {
        "draft_plan": merged_plan,
        "starting_point_coords": {"lat": lat, "lon": lon},
        "nearest_airport": airport,
        "validation": None,
    }


# Travel Plan Generation Endpoints
@app.post("/generate_travel_plans/visited")
async def travel_plans_visited(request: GenerationRequest, db: Session = Depends(get_db)):
    start_dt = datetime.strptime(request.startDate, "%Y-%m-%d")
    end_dt = datetime.strptime(request.endDate, "%Y-%m-%d")
    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="End date must be after start date.")
    travel_length = (end_dt - start_dt).days

    llm_provider = resolve_llm_provider(db, planner_account_id(request))

    return await generate_plan_with_location(
        generate_travel_plan_visited,
        request.startingPoint,
        travel_length,
        request.preferences,
        request.visitedPlaces,
        starting_point=request.startingPoint,
        budget=request.budget,
        start_date=request.startDate,
        end_date=request.endDate,
        language=request.language,
        llm_provider=llm_provider,
        extra_places=request.extraPlaces,
        db=db,
    )


@app.post("/generate_travel_plans/unvisited")
async def travel_plans_unvisited(request: UnvisitedGenerationRequest, db: Session = Depends(get_db)):
    start_dt = datetime.strptime(request.startDate, "%Y-%m-%d")
    end_dt = datetime.strptime(request.endDate, "%Y-%m-%d")
    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="End date must be after start date.")
    travel_length = (end_dt - start_dt).days

    if request.userId is not None:
        forbidden_places = build_unvisited_forbidden_places(
            db, request.userId, request.additionalExclusions
        )
    else:
        forbidden_places = merge_exclusion_lists([], request.additionalExclusions)

    llm_provider = resolve_llm_provider(db, planner_account_id(request))

    return await generate_plan_with_location(
        generate_travel_plan_unvisited,
        request.startingPoint,
        travel_length,
        request.preferences,
        forbidden_places,
        starting_point=request.startingPoint,
        budget=request.budget,
        start_date=request.startDate,
        end_date=request.endDate,
        language=request.language,
        llm_provider=llm_provider,
        db=db,
    )


@app.post("/generate_travel_plans/random")
async def travel_plans_random(request: RandomGenerationRequest, db: Session = Depends(get_db)):
    start_dt = datetime.strptime(request.startDate, "%Y-%m-%d")
    end_dt = datetime.strptime(request.endDate, "%Y-%m-%d")
    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="End date must be after start date.")
    travel_length = (end_dt - start_dt).days

    llm_provider = resolve_llm_provider(db, planner_account_id(request))

    return await generate_plan_with_location(
        generate_travel_plan_random,
        request.startingPoint,
        travel_length,
        request.preferences,
        starting_point=request.startingPoint,
        budget=request.budget,
        start_date=request.startDate,
        end_date=request.endDate,
        language=request.language,
        llm_provider=llm_provider,
        db=db,
    )


@app.get("/")
async def root():
    return RedirectResponse(url="/pages/main_page.html")


_uploads_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads"))
os.makedirs(_uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=_uploads_dir), name="uploads")

_frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")