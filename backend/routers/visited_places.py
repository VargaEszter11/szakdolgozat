from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import crud, schemas, get_db
from utils.coordinates import geocode_place

router = APIRouter()


@router.post("/visited-places", response_model=schemas.VisitedPlaceResponse, status_code=status.HTTP_201_CREATED)
async def create_visited_place(place: schemas.VisitedPlaceCreate, db: Session = Depends(get_db)):
    """Add a visited place"""
    # Verify user exists
    db_user = crud.get_user(db, user_id=place.user_id)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Geocode the place to get coordinates
    try:
        place_query = f"{place.place_name}, {place.country}" if place.country else place.place_name
        lat, lon = await geocode_place(place_query)
        
        # Create a new VisitedPlaceCreate object with coordinates
        place_dict = place.model_dump()
        place_dict['latitude'] = lat
        place_dict['longitude'] = lon
        place_with_coords = schemas.VisitedPlaceCreate(**place_dict)
        
        return crud.create_visited_place(db=db, place=place_with_coords)
    except Exception as e:
        # If geocoding fails, save without coordinates
        print(f"Geocoding failed for {place.place_name}: {e}")
        return crud.create_visited_place(db=db, place=place)


@router.get("/visited-places/{place_id}", response_model=schemas.VisitedPlaceResponse)
def get_visited_place(place_id: int, db: Session = Depends(get_db)):
    """Get a visited place by ID"""
    db_place = crud.get_visited_place(db, place_id=place_id)
    if db_place is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visited place not found"
        )
    return db_place


@router.get("/visited-places", response_model=List[schemas.VisitedPlaceResponse])
def list_visited_places(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List visited places, optionally filtered by user"""
    if user_id is not None:
        # Verify user exists
        db_user = crud.get_user(db, user_id=user_id)
        if db_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return crud.get_user_visited_places(db, user_id=user_id)
    
    return crud.get_visited_places(db, skip=skip, limit=limit)


@router.put("/visited-places/{place_id}", response_model=schemas.VisitedPlaceResponse)
def update_visited_place(place_id: int, place: schemas.VisitedPlaceUpdate, db: Session = Depends(get_db)):
    """Update a visited place"""
    db_place = crud.update_visited_place(db, place_id=place_id, place_update=place)
    if db_place is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visited place not found"
        )
    return db_place


@router.delete("/visited-places/{place_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_visited_place(place_id: int, db: Session = Depends(get_db)):
    """Delete a visited place"""
    success = crud.delete_visited_place(db, place_id=place_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visited place not found"
        )
    return None
