from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from database import crud, schemas, get_db
from utils.coordinates import geocode_place
from utils.place_image_upload import save_place_image

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


# ============= Images for visited places =============


@router.post(
    "/visited-places/{place_id}/images",
    response_model=schemas.ImageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_place_image(
    place_id: int,
    body: schemas.ImageCreateBody,
    db: Session = Depends(get_db),
):
    """Attach an image record to a visited place."""
    db_place = crud.get_visited_place(db, place_id=place_id)
    if db_place is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visited place not found",
        )
    if crud.count_images_for_visited_place(db, place_id) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This visited place already has an image.",
        )
    image_in = schemas.ImageCreate(image_path=body.image_path, visited_place_id=place_id)
    return crud.create_image(db, image_in)


@router.post(
    "/visited-places/{place_id}/images/upload",
    response_model=schemas.ImageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_place_image(
    place_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a binary image file; saves under project uploads/place_images and creates an Image row."""
    db_place = crud.get_visited_place(db, place_id=place_id)
    if db_place is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visited place not found",
        )
    if crud.count_images_for_visited_place(db, place_id) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This visited place already has an image.",
        )
    content = await file.read()
    try:
        public_path = save_place_image(content, file.content_type)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    image_in = schemas.ImageCreate(image_path=public_path, visited_place_id=place_id)
    return crud.create_image(db, image_in)


@router.get("/visited-places/{place_id}/images", response_model=List[schemas.ImageResponse])
def list_place_images(place_id: int, db: Session = Depends(get_db)):
    """List all images for a visited place."""
    db_place = crud.get_visited_place(db, place_id=place_id)
    if db_place is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visited place not found",
        )
    return crud.get_images(db, visited_place_id=place_id)


@router.get("/images/{image_id}", response_model=schemas.ImageResponse)
def read_image(image_id: int, db: Session = Depends(get_db)):
    """Get a single image record by id."""
    db_image = crud.get_image(db, image_id=image_id)
    if db_image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )
    return db_image


@router.put("/images/{image_id}", response_model=schemas.ImageResponse)
def update_place_image(
    image_id: int,
    image: schemas.ImageUpdate,
    db: Session = Depends(get_db),
):
    """Update an image record (e.g. stored path)."""
    db_image = crud.update_image(db, image_id=image_id, image_update=image)
    if db_image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )
    return db_image


@router.delete("/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_place_image(image_id: int, db: Session = Depends(get_db)):
    """Delete an image record."""
    success = crud.delete_image(db, image_id=image_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )
    return None
