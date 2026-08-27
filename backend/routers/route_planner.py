"""HTTP endpoints for trip generation (visited / unvisited / random).

Thin router: auth + travel-log opt-in, then delegates to ``plan_requests``.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db, models
from travel_types.plan_requests import (
    GenerationRequest,
    GeocodeRequest,
    RandomGenerationRequest,
    geocode_places,
    generate_random_plan,
    generate_unvisited_plan,
    generate_visited_plan,
)
from travel_types import UnvisitedGenerationRequest
from utils.auth_deps import current_user_id, get_current_user

router = APIRouter()


def _with_planner_user(
    request,
    current_user: models.User,
    *,
    force_travel_log_user: bool = True,
):
    """
    Bind planner identity from the access token.

    Always sets plannerUserId. userId (travel log) is opt-in for visited/unvisited
    (only when the client sent userId) and omitted for random.
    """
    data = request.model_dump()
    uid = current_user_id(current_user)
    data["plannerUserId"] = uid
    if force_travel_log_user:
        data["userId"] = uid
    else:
        data["userId"] = uid if data.get("userId") is not None else None
    return request.__class__(**data)


@router.post("/api/geocode")
async def batch_geocode(
    request: GeocodeRequest,
    current_user: models.User = Depends(get_current_user),
):
    del current_user
    return await geocode_places(request)


@router.post("/generate_travel_plans/visited")
async def travel_plans_visited(
    request: GenerationRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Respect "use travel log" toggle: omit userId ⇒ no DB visited places loaded.
    return await generate_visited_plan(
        _with_planner_user(request, current_user, force_travel_log_user=False),
        db,
    )


@router.post("/generate_travel_plans/unvisited")
async def travel_plans_unvisited(
    request: UnvisitedGenerationRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Respect "use travel log" toggle: omit userId ⇒ no DB visited exclusions.
    return await generate_unvisited_plan(
        _with_planner_user(request, current_user, force_travel_log_user=False),
        db,
    )


@router.post("/generate_travel_plans/random")
async def travel_plans_random(
    request: RandomGenerationRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return await generate_random_plan(
        _with_planner_user(request, current_user, force_travel_log_user=False),
        db,
    )