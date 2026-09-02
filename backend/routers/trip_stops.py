from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Any, cast
from database import crud, schemas, get_db, models
from utils.coordinates import geocode_place
from utils.auth_deps import current_user_id, get_current_user

router = APIRouter()


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


@router.post("/trip-stops", response_model=schemas.TripStopResponse, status_code=status.HTTP_201_CREATED)
async def create_trip_stop(
    stop: schemas.TripStopCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Add a stop to an owned trip and geocode place_name → latitude/longitude for the map."""
    from utils.countries import geocode_country_label, resolve_country_code

    db_trip = crud.get_planned_trip(db, trip_id=stop.trip_id)
    _require_trip_owner(db_trip, current_user_id(current_user))

    stop_dict = stop.model_dump()
    if stop_dict.get("country"):
        stop_dict["country"] = resolve_country_code(stop_dict["country"]) or stop_dict["country"]
    stop = schemas.TripStopCreate(**stop_dict)

    try:
        country_label = geocode_country_label(stop.country) if stop.country else ""
        place_query = f"{stop.place_name}, {country_label}" if country_label else stop.place_name
        lat, lon = await geocode_place(place_query)
        stop_dict = stop.model_dump()
        stop_dict["latitude"] = lat
        stop_dict["longitude"] = lon
        stop_with_coords = schemas.TripStopCreate(**stop_dict)
        return crud.create_trip_stop(db=db, stop=stop_with_coords)
    except Exception as e:
        # Still create the stop without coords -> the details map may geocode later as fallback
        print(f"Geocoding failed for {stop.place_name}: {e}")
        return crud.create_trip_stop(db=db, stop=stop)


@router.get("/trip-stops/{stop_id}", response_model=schemas.TripStopResponse)
def get_trip_stop(
    stop_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get a trip stop by ID"""
    db_stop = crud.get_trip_stop(db, stop_id=stop_id)
    if db_stop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip stop not found",
        )
    db_trip = crud.get_planned_trip(db, trip_id=int(cast(Any, db_stop).trip_id))
    _require_trip_owner(db_trip, current_user_id(current_user))
    return db_stop


@router.put("/trip-stops/{stop_id}", response_model=schemas.TripStopResponse)
def update_trip_stop(
    stop_id: int,
    stop: schemas.TripStopUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Update a trip stop"""
    existing = crud.get_trip_stop(db, stop_id=stop_id)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip stop not found",
        )
    db_trip = crud.get_planned_trip(db, trip_id=int(cast(Any, existing).trip_id))
    _require_trip_owner(db_trip, current_user_id(current_user))
    db_stop = crud.update_trip_stop(db, stop_id=stop_id, stop_update=stop)
    if db_stop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip stop not found",
        )
    return db_stop


@router.delete("/trip-stops/{stop_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trip_stop(
    stop_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Delete a trip stop"""
    existing = crud.get_trip_stop(db, stop_id=stop_id)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip stop not found",
        )
    db_trip = crud.get_planned_trip(db, trip_id=int(cast(Any, existing).trip_id))
    _require_trip_owner(db_trip, current_user_id(current_user))
    success = crud.delete_trip_stop(db, stop_id=stop_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip stop not found",
        )
    return None
