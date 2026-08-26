"""
Planned trips CRUD API used by the Planned Trips page.

Ownership: every mutating/read-by-id call checks the trip belongs to the current user.
Start city: text plus start_latitude/start_longitude filled via Nominatim on create
(and again when start_city is updated). List/get also run booked→visited sync for
trips whose end_date is already in the past.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Any, List, Optional, Tuple, cast
from database import crud, schemas, get_db, models
from utils.auth_deps import current_user_id, get_current_user
from utils.coordinates import geocode_place

router = APIRouter()


def _require_trip_owner(trip, user_id: int) -> None:
    """404 if missing, 403 if the trip is owned by someone else."""
    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planned trip not found",
        )
    if int(cast(Any, trip).user_id) != int(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )


async def _geocode_start_city(start_city: Optional[str]) -> Tuple[Optional[float], Optional[float]]:
    """Resolve start city coordinates; return (None, None) if missing or geocode fails."""
    city = (start_city or "").strip() or None
    if not city:
        return None, None
    try:
        lat, lon = await geocode_place(city)
        return lat, lon
    except Exception as exc:
        # Keep the trip saveable even when Nominatim is down or the city is unknown
        print(f"Geocoding failed for start city {city}: {exc}")
        return None, None


# Create
@router.post("/planned-trips", response_model=schemas.PlannedTripResponse, status_code=status.HTTP_201_CREATED)
async def create_planned_trip(
    trip: schemas.PlannedTripCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create a trip for the current user; geocode start_city when provided."""
    trip_dict = trip.model_dump()
    trip_dict["user_id"] = current_user_id(current_user)
    start_city = (trip_dict.get("start_city") or "").strip() or None
    trip_dict["start_city"] = start_city
    # Coordinates are server-resolved only (ignore any client-supplied values).
    lat, lon = await _geocode_start_city(start_city)
    trip_dict["start_latitude"] = lat
    trip_dict["start_longitude"] = lon
    trip = schemas.PlannedTripCreate(**trip_dict)
    db_trip = crud.create_planned_trip(db=db, trip=trip)
    return crud.planned_trip_to_response(db, db_trip)


# Read
@router.get("/planned-trips/{trip_id}", response_model=schemas.PlannedTripResponse)
def get_planned_trip(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get one owned trip (includes stops). Syncs booked→visited if the trip has ended."""
    db_trip = crud.get_planned_trip(db, trip_id=trip_id)
    _require_trip_owner(db_trip, current_user_id(current_user))
    crud.sync_completed_booked_trip_to_visited(db, db_trip)
    return crud.planned_trip_to_response(db, db_trip)


@router.get("/planned-trips", response_model=List[schemas.PlannedTripResponse])
def list_planned_trips(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List all trips for the authenticated user (page list + home widgets use this)."""
    del skip, limit  # ownership-scoped list; pagination kept for API compatibility
    trips = crud.get_user_planned_trips(db, user_id=current_user_id(current_user))
    crud.sync_completed_booked_trips_to_visited(db, trips)
    return crud.planned_trips_to_response(db, trips)


# Update / delete
@router.put("/planned-trips/{trip_id}", response_model=schemas.PlannedTripResponse)
async def update_planned_trip(
    trip_id: int,
    trip: schemas.PlannedTripUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Partial update; re-geocode (or clear) start coordinates when start_city changes."""
    existing = crud.get_planned_trip(db, trip_id=trip_id)
    _require_trip_owner(existing, current_user_id(current_user))

    update_data = trip.model_dump(exclude_unset=True)
    # Do not trust client-sent coordinates; only set them when we geocode below.
    update_data.pop("start_latitude", None)
    update_data.pop("start_longitude", None)
    if "start_city" in update_data:
        start_city = (update_data.get("start_city") or "").strip() or None
        update_data["start_city"] = start_city
        lat, lon = await _geocode_start_city(start_city)
        update_data["start_latitude"] = lat
        update_data["start_longitude"] = lon

    trip = schemas.PlannedTripUpdate(**update_data)
    db_trip = crud.update_planned_trip(db, trip_id=trip_id, trip_update=trip)
    if db_trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planned trip not found",
        )
    crud.sync_completed_booked_trip_to_visited(db, db_trip)
    return crud.planned_trip_to_response(db, db_trip)


@router.delete("/planned-trips/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_planned_trip(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Delete an owned planned trip (cascades stops)."""
    existing = crud.get_planned_trip(db, trip_id=trip_id)
    _require_trip_owner(existing, current_user_id(current_user))
    success = crud.delete_planned_trip(db, trip_id=trip_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planned trip not found",
        )
    return None
