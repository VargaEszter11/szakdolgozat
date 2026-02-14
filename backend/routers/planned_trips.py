from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import crud, schemas, get_db

router = APIRouter()


@router.post("/planned-trips", response_model=schemas.PlannedTripResponse, status_code=status.HTTP_201_CREATED)
def create_planned_trip(trip: schemas.PlannedTripCreate, db: Session = Depends(get_db)):
    """Create a new planned trip"""
    # Verify user exists
    db_user = crud.get_user(db, user_id=trip.user_id)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
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
        return crud.get_user_planned_trips(db, user_id=user_id)
    
    return crud.get_planned_trips(db, skip=skip, limit=limit)


@router.put("/planned-trips/{trip_id}", response_model=schemas.PlannedTripResponse)
def update_planned_trip(trip_id: int, trip: schemas.PlannedTripUpdate, db: Session = Depends(get_db)):
    """Update a planned trip"""
    db_trip = crud.update_planned_trip(db, trip_id=trip_id, trip_update=trip)
    if db_trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planned trip not found"
        )
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
