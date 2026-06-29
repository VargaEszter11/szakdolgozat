from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Any, List, Optional, cast

from database import crud, schemas, get_db, models

router = APIRouter()


def _cover_image_url(place: models.VisitedPlace) -> Optional[str]:
    """First uploaded gallery image for cards, else legacy photo_path."""
    imgs = getattr(place, "images", None) or []
    if imgs:
        first = sorted(imgs, key=lambda im: im.id)[0]
        return first.image_path
    return cast(str | None, place.photo_path)


@router.post("/users", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if username already exists
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    return crud.create_user(db=db, user=user)


@router.get("/users/{user_id}", response_model=schemas.UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get user details by ID"""
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return db_user


@router.get("/users", response_model=List[schemas.UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    exclude_user_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """List or search users by username."""
    if search or exclude_user_id is not None:
        users = crud.search_users(
            db,
            search=search,
            exclude_user_id=exclude_user_id,
            skip=skip,
            limit=min(limit, 100),
        )
    else:
        users = crud.get_users(db, skip=skip, limit=limit)
    return users


@router.put("/users/{user_id}", response_model=schemas.UserResponse)
def update_user(user_id: int, user: schemas.UserUpdate, db: Session = Depends(get_db)):
    """Update user information"""
    # Check if username is being changed and if it already exists
    if user.username:
        existing_user = crud.get_user_by_username(db, username=user.username)
        if existing_user is not None and cast(Any, existing_user).id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    # Check if email is being changed and if it already exists
    if user.email:
        existing_user = crud.get_user_by_email(db, email=user.email)
        if existing_user is not None and cast(Any, existing_user).id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    db_user = crud.update_user(db, user_id=user_id, user_update=user)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return db_user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """Delete a user"""
    success = crud.delete_user(db, user_id=user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return None


@router.get("/users/{user_id}/visited-places", response_model=List[schemas.VisitedPlaceResponse])
def get_user_visited_places(user_id: int, db: Session = Depends(get_db)):
    """Get all visited places for a user"""
    # Verify user exists
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    places = crud.get_user_visited_places(db, user_id=user_id)
    return [
        schemas.VisitedPlaceResponse.model_validate(p).model_copy(
            update={"image": _cover_image_url(p)}
        )
        for p in places
    ]


@router.get("/users/{user_id}/planned-trips", response_model=List[schemas.PlannedTripResponse])
def get_user_planned_trips(user_id: int, db: Session = Depends(get_db)):
    """Get all planned trips for a user"""
    # Verify user exists
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return crud.get_user_planned_trips(db, user_id=user_id)
