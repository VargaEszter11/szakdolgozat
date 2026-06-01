from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from database import crud, schemas, get_db
from utils.coordinates import geocode_place

router = APIRouter()


def _place_key(place_name: str, country: Optional[str]) -> tuple[str, str]:
    return ((place_name or "").strip().lower(), (country or "").strip().lower())


def _sync_completed_booked_trip_to_visited(db: Session, trip) -> None:
    if not trip or not trip.is_booked or not trip.end_date or trip.end_date >= date.today():
        return

    existing = {
        _place_key(place.place_name, place.country)
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
                latitude=stop.latitude,
                longitude=stop.longitude,
            ),
        )
        existing.add(key)


def _sync_completed_booked_trips_to_visited(db: Session, trips) -> None:
    for trip in trips or []:
        _sync_completed_booked_trip_to_visited(db, trip)


@router.post("/planned-trips", response_model=schemas.PlannedTripResponse, status_code=status.HTTP_201_CREATED)
async def create_planned_trip(trip: schemas.PlannedTripCreate, db: Session = Depends(get_db)):
    """Create a new planned trip"""
    # Verify user exists
    db_user = crud.get_user(db, user_id=trip.user_id)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Geocode the start city if provided
    if trip.start_city:
        try:
            lat, lon = await geocode_place(trip.start_city)
            
            # Create a new PlannedTripCreate object with coordinates
            trip_dict = trip.model_dump()
            trip_dict['start_latitude'] = lat
            trip_dict['start_longitude'] = lon
            trip_with_coords = schemas.PlannedTripCreate(**trip_dict)
            
            return crud.create_planned_trip(db=db, trip=trip_with_coords)
        except Exception as e:
            # If geocoding fails, save without coordinates
            print(f"Geocoding failed for start city {trip.start_city}: {e}")
    
    return crud.create_planned_trip(db=db, trip=trip)


@router.get("/planned-trips/{trip_id}", response_model=schemas.PlannedTripResponse)
def get_planned_trip(trip_id: int, db: Session = Depends(get_db)):
    """Get a planned trip by ID with all stops"""
    db_trip = crud.get_planned_trip(db, trip_id=trip_id)
    if db_trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planned trip not found"
        )
    _sync_completed_booked_trip_to_visited(db, db_trip)
    return db_trip


@router.get("/planned-trips", response_model=List[schemas.PlannedTripResponse])
def list_planned_trips(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List planned trips, optionally filtered by user"""
    if user_id is not None:
        # Verify user exists
        db_user = crud.get_user(db, user_id=user_id)
        if db_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        trips = crud.get_user_planned_trips(db, user_id=user_id)
        _sync_completed_booked_trips_to_visited(db, trips)
        return trips
    
    trips = crud.get_planned_trips(db, skip=skip, limit=limit)
    _sync_completed_booked_trips_to_visited(db, trips)
    return trips


@router.put("/planned-trips/{trip_id}", response_model=schemas.PlannedTripResponse)
def update_planned_trip(trip_id: int, trip: schemas.PlannedTripUpdate, db: Session = Depends(get_db)):
    """Update a planned trip"""
    db_trip = crud.update_planned_trip(db, trip_id=trip_id, trip_update=trip)
    if db_trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planned trip not found"
        )
    _sync_completed_booked_trip_to_visited(db, db_trip)
    return db_trip


@router.delete("/planned-trips/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_planned_trip(trip_id: int, db: Session = Depends(get_db)):
    """Delete a planned trip"""
    success = crud.delete_planned_trip(db, trip_id=trip_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planned trip not found"
        )
    return None
