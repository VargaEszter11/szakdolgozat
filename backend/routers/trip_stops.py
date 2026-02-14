from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import crud, schemas, get_db
from utils.coordinates import geocode_place

router = APIRouter()


@router.post("/trip-stops", response_model=schemas.TripStopResponse, status_code=status.HTTP_201_CREATED)
async def create_trip_stop(stop: schemas.TripStopCreate, db: Session = Depends(get_db)):
    """Add a stop to a trip"""
    # Verify trip exists
    db_trip = crud.get_planned_trip(db, trip_id=stop.trip_id)
    if db_trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planned trip not found"
        )
    
    # Geocode the stop to get coordinates
    try:
        place_query = f"{stop.place_name}, {stop.country}" if stop.country else stop.place_name
        lat, lon = await geocode_place(place_query)
        
        # Create a new TripStopCreate object with coordinates
        stop_dict = stop.model_dump()
        stop_dict['latitude'] = lat
        stop_dict['longitude'] = lon
        stop_with_coords = schemas.TripStopCreate(**stop_dict)
        
        return crud.create_trip_stop(db=db, stop=stop_with_coords)
    except Exception as e:
        # If geocoding fails, save without coordinates
        print(f"Geocoding failed for {stop.place_name}: {e}")
        return crud.create_trip_stop(db=db, stop=stop)


@router.get("/trip-stops/{stop_id}", response_model=schemas.TripStopResponse)
def get_trip_stop(stop_id: int, db: Session = Depends(get_db)):
    """Get a trip stop by ID"""
    db_stop = crud.get_trip_stop(db, stop_id=stop_id)
    if db_stop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip stop not found"
        )
    return db_stop


@router.get("/trips/{trip_id}/stops", response_model=List[schemas.TripStopResponse])
def get_trip_stops(trip_id: int, db: Session = Depends(get_db)):
    """Get all stops for a trip"""
    # Verify trip exists
    db_trip = crud.get_planned_trip(db, trip_id=trip_id)
    if db_trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planned trip not found"
        )
    
    return crud.get_trip_stops(db, trip_id=trip_id)


@router.put("/trip-stops/{stop_id}", response_model=schemas.TripStopResponse)
def update_trip_stop(stop_id: int, stop: schemas.TripStopUpdate, db: Session = Depends(get_db)):
    """Update a trip stop"""
    db_stop = crud.update_trip_stop(db, stop_id=stop_id, stop_update=stop)
    if db_stop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip stop not found"
        )
    return db_stop


@router.delete("/trip-stops/{stop_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trip_stop(stop_id: int, db: Session = Depends(get_db)):
    """Delete a trip stop"""
    success = crud.delete_trip_stop(db, stop_id=stop_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip stop not found"
        )
    return None
