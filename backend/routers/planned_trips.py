from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Any, List, Optional, cast
from datetime import date
from database import crud, schemas, get_db, models
from utils.coordinates import geocode_place
from utils.auth_deps import current_user_id, get_current_user

router = APIRouter()


def _place_key(place_name: str, country: Optional[str]) -> tuple[str, str]:
    return ((place_name or "").strip().lower(), (country or "").strip().lower())


def _require_trip_owner(trip, user_id: int) -> None:
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


def _sync_completed_booked_trip_to_visited(db: Session, trip) -> None:
    if not trip or not trip.is_booked or not trip.end_date or trip.end_date >= date.today():
        return

    existing = {
        _place_key(cast(Any, place).place_name, cast(Any, place).country)
        for place in crud.get_user_visited_places(db, trip.user_id)
    }
    stops = sorted(trip.stops or [], key=lambda stop: stop.stop_order or 0)
    for index, stop in enumerate(stops):
        if not stop.place_name:
            continue
        is_return_home = index == len(stops) - 1 and trip.start_city and (
            stop.place_name.strip().lower() == trip.start_city.strip().lower()
        )
        if is_return_home:
            continue

        key = _place_key(stop.place_name, stop.country)
        if key in existing:
            continue

        crud.create_visited_place(
            db,
            schemas.VisitedPlaceCreate(
                user_id=trip.user_id,
                place_name=stop.place_name,
                country=stop.country,
                date=stop.arrival_date or trip.end_date,
                rating=None,
                latitude=stop.latitude,
                longitude=stop.longitude,
            ),
        )
        existing.add(key)


def _sync_completed_booked_trips_to_visited(db: Session, trips) -> None:
    for trip in trips or []:
        _sync_completed_booked_trip_to_visited(db, trip)


@router.post("/planned-trips", response_model=schemas.PlannedTripResponse, status_code=status.HTTP_201_CREATED)
async def create_planned_trip(
    trip: schemas.PlannedTripCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create a new planned trip"""
    trip_dict = trip.model_dump()
    trip_dict["user_id"] = current_user_id(current_user)
    trip = schemas.PlannedTripCreate(**trip_dict)

    if trip.start_city:
        try:
            lat, lon = await geocode_place(trip.start_city)
            trip_dict = trip.model_dump()
            trip_dict["start_latitude"] = lat
            trip_dict["start_longitude"] = lon
            trip_with_coords = schemas.PlannedTripCreate(**trip_dict)
            return crud.create_planned_trip(db=db, trip=trip_with_coords)
        except Exception as e:
            print(f"Geocoding failed for start city {trip.start_city}: {e}")

    return crud.create_planned_trip(db=db, trip=trip)


@router.get("/planned-trips/{trip_id}", response_model=schemas.PlannedTripResponse)
def get_planned_trip(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get a planned trip by ID with all stops"""
    db_trip = crud.get_planned_trip(db, trip_id=trip_id)
    _require_trip_owner(db_trip, current_user_id(current_user))
    _sync_completed_booked_trip_to_visited(db, db_trip)
    return db_trip


@router.get("/planned-trips", response_model=List[schemas.PlannedTripResponse])
def list_planned_trips(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List planned trips for the authenticated user."""
    del skip, limit  # ownership-scoped list; pagination kept for API compatibility
    trips = crud.get_user_planned_trips(db, user_id=current_user_id(current_user))
    _sync_completed_booked_trips_to_visited(db, trips)
    return trips


@router.put("/planned-trips/{trip_id}", response_model=schemas.PlannedTripResponse)
def update_planned_trip(
    trip_id: int,
    trip: schemas.PlannedTripUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Update a planned trip"""
    existing = crud.get_planned_trip(db, trip_id=trip_id)
    _require_trip_owner(existing, current_user_id(current_user))
    db_trip = crud.update_planned_trip(db, trip_id=trip_id, trip_update=trip)
    if db_trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planned trip not found",
        )
    _sync_completed_booked_trip_to_visited(db, db_trip)
    return db_trip


@router.delete("/planned-trips/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_planned_trip(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Delete a planned trip"""
    existing = crud.get_planned_trip(db, trip_id=trip_id)
    _require_trip_owner(existing, current_user_id(current_user))
    success = crud.delete_planned_trip(db, trip_id=trip_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planned trip not found",
        )
    return None
