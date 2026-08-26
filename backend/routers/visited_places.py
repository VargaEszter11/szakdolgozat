from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import Any, List, cast
from database import crud, schemas, get_db, models
from utils.coordinates import geocode_place
from utils.place_image_upload import save_place_image
from utils.auth_deps import current_user_id, get_current_user

router = APIRouter()


def _require_place_owner(place, user_id: int) -> None:
    if place is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visited place not found",
        )
    if int(cast(Any, place).user_id) != int(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )


def _require_image_owner(db: Session, image, user_id: int) -> None:
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )
    place = crud.get_visited_place(db, place_id=int(cast(Any, image).visited_place_id))
    _require_place_owner(place, user_id)


@router.post("/visited-places", response_model=schemas.VisitedPlaceResponse, status_code=status.HTTP_201_CREATED)
async def create_visited_place(
    place: schemas.VisitedPlaceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Add a visited place"""
    from utils.countries import geocode_country_label, normalize_country_code

    place_dict = place.model_dump()
    place_dict["user_id"] = current_user_id(current_user)
    if place_dict.get("country"):
        place_dict["country"] = normalize_country_code(place_dict["country"]) or place_dict["country"]
    place = schemas.VisitedPlaceCreate(**place_dict)

    try:
        country_label = geocode_country_label(place.country) if place.country else ""
        place_query = f"{place.place_name}, {country_label}" if country_label else place.place_name
        lat, lon = await geocode_place(place_query)
        place_dict = place.model_dump()
        place_dict["latitude"] = lat
        place_dict["longitude"] = lon
        place_with_coords = schemas.VisitedPlaceCreate(**place_dict)
        return crud.create_visited_place(db=db, place=place_with_coords)
    except Exception as e:
        print(f"Geocoding failed for {place.place_name}: {e}")
        return crud.create_visited_place(db=db, place=place)


@router.get("/visited-places/{place_id}", response_model=schemas.VisitedPlaceResponse)
def get_visited_place(
    place_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get a visited place by ID"""
    db_place = crud.get_visited_place(db, place_id=place_id)
    _require_place_owner(db_place, current_user_id(current_user))
    return db_place


@router.get("/visited-places", response_model=List[schemas.VisitedPlaceResponse])
def list_visited_places(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List visited places for the authenticated user."""
    del skip, limit
    uid = current_user_id(current_user)
    crud.sync_completed_booked_trips_for_user(db, uid)
    return crud.get_user_visited_places(db, user_id=uid)


@router.put("/visited-places/{place_id}", response_model=schemas.VisitedPlaceResponse)
def update_visited_place(
    place_id: int,
    place: schemas.VisitedPlaceUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Update a visited place"""
    existing = crud.get_visited_place(db, place_id=place_id)
    _require_place_owner(existing, current_user_id(current_user))
    db_place = crud.update_visited_place(db, place_id=place_id, place_update=place)
    if db_place is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visited place not found",
        )
    return db_place


@router.delete("/visited-places/{place_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_visited_place(
    place_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Delete a visited place"""
    existing = crud.get_visited_place(db, place_id=place_id)
    _require_place_owner(existing, current_user_id(current_user))
    success = crud.delete_visited_place(db, place_id=place_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visited place not found",
        )
    return None


@router.post(
    "/visited-places/{place_id}/images",
    response_model=schemas.ImageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_place_image(
    place_id: int,
    body: schemas.ImageCreateBody,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Attach an image record to a visited place."""
    db_place = crud.get_visited_place(db, place_id=place_id)
    _require_place_owner(db_place, current_user_id(current_user))
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
    current_user: models.User = Depends(get_current_user),
):
    """Upload a binary image file; saves under project uploads/place_images and creates an Image row."""
    db_place = crud.get_visited_place(db, place_id=place_id)
    _require_place_owner(db_place, current_user_id(current_user))
    content = await file.read()
    try:
        public_path = save_place_image(content, file.content_type)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    image_in = schemas.ImageCreate(image_path=public_path, visited_place_id=place_id)
    return crud.create_image(db, image_in)


@router.get("/visited-places/{place_id}/images", response_model=List[schemas.ImageResponse])
def list_place_images(
    place_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List all images for a visited place."""
    db_place = crud.get_visited_place(db, place_id=place_id)
    _require_place_owner(db_place, current_user_id(current_user))
    return crud.get_images(db, visited_place_id=place_id)


@router.get("/images/{image_id}", response_model=schemas.ImageResponse)
def read_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get a single image record by id."""
    db_image = crud.get_image(db, image_id=image_id)
    _require_image_owner(db, db_image, current_user_id(current_user))
    return db_image


@router.put("/images/{image_id}", response_model=schemas.ImageResponse)
def update_place_image(
    image_id: int,
    image: schemas.ImageUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Update an image record (e.g. stored path)."""
    existing = crud.get_image(db, image_id=image_id)
    _require_image_owner(db, existing, current_user_id(current_user))
    db_image = crud.update_image(db, image_id=image_id, image_update=image)
    if db_image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )
    return db_image


@router.delete("/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_place_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Delete an image record."""
    existing = crud.get_image(db, image_id=image_id)
    _require_image_owner(db, existing, current_user_id(current_user))
    success = crud.delete_image(db, image_id=image_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )
    return None
