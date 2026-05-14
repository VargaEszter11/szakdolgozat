from datetime import datetime, timezone
from sqlalchemy.orm import Session, joinedload
import bcrypt
import re
import secrets
from typing import Any, Dict, List, Optional, Set
from . import models, schemas
from utils.place_image_upload import delete_file_for_public_path


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    # Convert password to bytes and hash it
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


# ============= User CRUD Operations =============

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    """Create a new user with hashed password"""
    hashed_password = hash_password(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def create_google_user(db: Session, email: str, display_name: Optional[str] = None) -> models.User:
    """Create a new user account for Google Sign-In."""
    base_name = (display_name or email.split("@")[0] or "google_user").strip().lower()
    base_name = re.sub(r"[^a-z0-9_]", "_", base_name)
    if len(base_name) < 3:
        base_name = "google_user"

    username = base_name[:50]
    suffix = 1
    while get_user_by_username(db, username=username):
        suffix_text = f"_{suffix}"
        username = f"{base_name[: max(1, 50 - len(suffix_text))]}{suffix_text}"
        suffix += 1

    random_password = secrets.token_urlsafe(32)
    db_user = models.User(
        username=username,
        email=email,
        password=hash_password(random_password),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user(db: Session, user_id: int) -> Optional[models.User]:
    """Get a user by ID"""
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    """Get a user by username"""
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    """Get a user by email"""
    return db.query(models.User).filter(models.User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    """Get a list of users"""
    return db.query(models.User).offset(skip).limit(limit).all()


def update_user(db: Session, user_id: int, user_update: schemas.UserUpdate) -> Optional[models.User]:
    """Update a user's information"""
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    
    update_data = user_update.model_dump(exclude_unset=True)
    
    # Hash password if it's being updated
    if "password" in update_data:
        update_data["password"] = hash_password(update_data["password"])
    
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int) -> bool:
    """Delete a user"""
    db_user = get_user(db, user_id)
    if not db_user:
        return False
    
    db.delete(db_user)
    db.commit()
    return True


# ============= Planned Trip CRUD Operations =============

def create_planned_trip(db: Session, trip: schemas.PlannedTripCreate) -> models.PlannedTrip:
    """Create a new planned trip"""
    db_trip = models.PlannedTrip(**trip.model_dump())
    db.add(db_trip)
    db.commit()
    db.refresh(db_trip)
    return db_trip


def get_planned_trip(db: Session, trip_id: int) -> Optional[models.PlannedTrip]:
    """Get a planned trip by ID"""
    return db.query(models.PlannedTrip).filter(models.PlannedTrip.id == trip_id).first()


def get_user_planned_trips(db: Session, user_id: int) -> List[models.PlannedTrip]:
    """Get all planned trips for a user"""
    return db.query(models.PlannedTrip).filter(models.PlannedTrip.user_id == user_id).all()


def get_planned_trips(db: Session, skip: int = 0, limit: int = 100) -> List[models.PlannedTrip]:
    """Get a list of planned trips"""
    return db.query(models.PlannedTrip).offset(skip).limit(limit).all()


def update_planned_trip(db: Session, trip_id: int, trip_update: schemas.PlannedTripUpdate) -> Optional[models.PlannedTrip]:
    """Update a planned trip"""
    db_trip = get_planned_trip(db, trip_id)
    if not db_trip:
        return None
    
    update_data = trip_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_trip, key, value)
    
    db.commit()
    db.refresh(db_trip)
    return db_trip


def delete_planned_trip(db: Session, trip_id: int) -> bool:
    """Delete a planned trip"""
    db_trip = get_planned_trip(db, trip_id)
    if not db_trip:
        return False
    
    db.delete(db_trip)
    db.commit()
    return True


# ============= Trip Stop CRUD Operations =============

def create_trip_stop(db: Session, stop: schemas.TripStopCreate) -> models.PlannedTripStop:
    """Create a new trip stop"""
    db_stop = models.PlannedTripStop(**stop.model_dump())
    db.add(db_stop)
    db.commit()
    db.refresh(db_stop)
    return db_stop


def get_trip_stop(db: Session, stop_id: int) -> Optional[models.PlannedTripStop]:
    """Get a trip stop by ID"""
    return db.query(models.PlannedTripStop).filter(models.PlannedTripStop.id == stop_id).first()


def get_trip_stops(db: Session, trip_id: int) -> List[models.PlannedTripStop]:
    """Get all stops for a trip"""
    return db.query(models.PlannedTripStop).filter(
        models.PlannedTripStop.trip_id == trip_id
    ).order_by(models.PlannedTripStop.stop_order).all()


def update_trip_stop(db: Session, stop_id: int, stop_update: schemas.TripStopUpdate) -> Optional[models.PlannedTripStop]:
    """Update a trip stop"""
    db_stop = get_trip_stop(db, stop_id)
    if not db_stop:
        return None
    
    update_data = stop_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_stop, key, value)
    
    db.commit()
    db.refresh(db_stop)
    return db_stop


def delete_trip_stop(db: Session, stop_id: int) -> bool:
    """Delete a trip stop"""
    db_stop = get_trip_stop(db, stop_id)
    if not db_stop:
        return False
    
    db.delete(db_stop)
    db.commit()
    return True


# ============= Visited Place CRUD Operations =============

def create_visited_place(db: Session, place: schemas.VisitedPlaceCreate) -> models.VisitedPlace:
    """Create a new visited place"""
    db_place = models.VisitedPlace(**place.model_dump())
    db.add(db_place)
    db.commit()
    db.refresh(db_place)
    return db_place


def get_visited_place(db: Session, place_id: int) -> Optional[models.VisitedPlace]:
    """Get a visited place by ID"""
    return db.query(models.VisitedPlace).filter(models.VisitedPlace.id == place_id).first()


def get_user_visited_places(db: Session, user_id: int) -> List[models.VisitedPlace]:
    """Get all visited places for a user"""
    return (
        db.query(models.VisitedPlace)
        .options(joinedload(models.VisitedPlace.images))
        .filter(models.VisitedPlace.user_id == user_id)
        .all()
    )


def get_visited_places(db: Session, skip: int = 0, limit: int = 100) -> List[models.VisitedPlace]:
    """Get a list of visited places"""
    return db.query(models.VisitedPlace).offset(skip).limit(limit).all()


def update_visited_place(db: Session, place_id: int, place_update: schemas.VisitedPlaceUpdate) -> Optional[models.VisitedPlace]:
    """Update a visited place"""
    db_place = get_visited_place(db, place_id)
    if not db_place:
        return None
    
    update_data = place_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_place, key, value)
    
    db.commit()
    db.refresh(db_place)
    return db_place


def delete_visited_place(db: Session, place_id: int) -> bool:
    """Delete a visited place"""
    db_place = (
        db.query(models.VisitedPlace)
        .options(joinedload(models.VisitedPlace.images))
        .filter(models.VisitedPlace.id == place_id)
        .first()
    )
    if not db_place:
        return False

    for img in db_place.images:
        delete_file_for_public_path(img.image_path)

    db.delete(db_place)
    db.commit()
    return True

# ============= Image CRUD Operations =============

def create_image(db: Session, image: schemas.ImageCreate) -> models.Image:
    """Create a new image"""
    db_image = models.Image(**image.model_dump())
    db.add(db_image)
    db.commit()
    db.refresh(db_image)
    return db_image

def get_image(db: Session, image_id: int) -> Optional[models.Image]:
    """Get an image by ID"""
    return db.query(models.Image).filter(models.Image.id == image_id).first()

def get_images(db: Session, visited_place_id: int) -> List[models.Image]:
    """Get all images for a visited place (ordered by id)."""
    return (
        db.query(models.Image)
        .filter(models.Image.visited_place_id == visited_place_id)
        .order_by(models.Image.id)
        .all()
    )


def count_images_for_visited_place(db: Session, visited_place_id: int) -> int:
    """How many image rows exist for this place."""
    return (
        db.query(models.Image)
        .filter(models.Image.visited_place_id == visited_place_id)
        .count()
    )

def update_image(db: Session, image_id: int, image_update: schemas.ImageUpdate) -> Optional[models.Image]:
    """Update an image"""
    db_image = get_image(db, image_id)
    if not db_image:
        return None

    update_data = image_update.model_dump(exclude_unset=True)
    old_path = None
    if "image_path" in update_data:
        old_path = db_image.image_path

    for key, value in update_data.items():
        setattr(db_image, key, value)

    db.commit()
    db.refresh(db_image)

    if old_path and old_path != db_image.image_path:
        delete_file_for_public_path(old_path)

    return db_image


def delete_image(db: Session, image_id: int) -> bool:
    """Delete an image"""
    db_image = get_image(db, image_id)
    if not db_image:
        return False

    path = db_image.image_path
    db.delete(db_image)
    db.commit()
    delete_file_for_public_path(path)
    return True


# ============= Airport & route cache CRUD =============


def _norm_iata(code: Optional[str]) -> str:
    return (code or "").strip().upper()


def _norm_country(code: Optional[str]) -> Optional[str]:
    if not code:
        return None
    c = str(code).strip().upper()
    return c[:2] if c else None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_airport(db: Session, iata: str) -> Optional[models.Airport]:
    """Get a cached airport by IATA code (case-insensitive lookup key)."""
    return db.query(models.Airport).filter(models.Airport.iata == _norm_iata(iata)).first()


def create_airport(db: Session, airport: schemas.AirportCreate) -> models.Airport:
    """Insert a new airport row. Fails if ``iata`` already exists."""
    data = airport.model_dump()
    data["iata"] = _norm_iata(data["iata"])
    if data.get("country"):
        data["country"] = _norm_country(data["country"])
    if data.get("icao"):
        data["icao"] = str(data["icao"]).strip().upper()
    db_airport = models.Airport(**data)
    db.add(db_airport)
    db.commit()
    db.refresh(db_airport)
    return db_airport


def _upsert_airport_no_commit(db: Session, airport: schemas.AirportCreate) -> models.Airport:
    iata = _norm_iata(airport.iata)
    row = get_airport(db, iata)
    country = _norm_country(airport.country) if airport.country else None
    icao = airport.icao.strip().upper() if airport.icao else None

    if row is None:
        row = models.Airport(
            iata=iata,
            icao=icao,
            city=airport.city,
            country=country,
            latitude=airport.latitude,
            longitude=airport.longitude,
        )
        db.add(row)
        return row

    if icao is not None:
        row.icao = icao
    if airport.city is not None:
        row.city = airport.city
    if country is not None:
        row.country = country
    if airport.latitude is not None:
        row.latitude = airport.latitude
    if airport.longitude is not None:
        row.longitude = airport.longitude
    row.updated_at = _utcnow()
    return row


def upsert_airport(db: Session, airport: schemas.AirportCreate) -> models.Airport:
    """Insert or update cached airport metadata (``updated_at`` bumped on update)."""
    row = _upsert_airport_no_commit(db, airport)
    db.commit()
    db.refresh(row)
    return row


def update_airport(db: Session, iata: str, airport_update: schemas.AirportUpdate) -> Optional[models.Airport]:
    """Patch fields on an existing airport."""
    row = get_airport(db, iata)
    if not row:
        return None

    update_data = airport_update.model_dump(exclude_unset=True)
    if "icao" in update_data and update_data["icao"] is not None:
        update_data["icao"] = str(update_data["icao"]).strip().upper()
    if "country" in update_data and update_data["country"] is not None:
        update_data["country"] = _norm_country(update_data["country"])

    for key, value in update_data.items():
        setattr(row, key, value)
    row.updated_at = _utcnow()

    db.commit()
    db.refresh(row)
    return row


def get_direct_route(
    db: Session, origin_iata: str, destination_iata: str
) -> Optional[models.DirectRoute]:
    return (
        db.query(models.DirectRoute)
        .filter(
            models.DirectRoute.origin_iata == _norm_iata(origin_iata),
            models.DirectRoute.destination_iata == _norm_iata(destination_iata),
        )
        .first()
    )


def create_direct_route(db: Session, route: schemas.DirectRouteCreate) -> models.DirectRoute:
    """Insert a new direct route edge."""
    data = route.model_dump()
    data["origin_iata"] = _norm_iata(data["origin_iata"])
    data["destination_iata"] = _norm_iata(data["destination_iata"])
    db_route = models.DirectRoute(**data)
    db.add(db_route)
    db.commit()
    db.refresh(db_route)
    return db_route


def _upsert_direct_route_no_commit(
    db: Session, origin_iata: str, destination_iata: str, *, is_active: bool = True
) -> models.DirectRoute:
    o = _norm_iata(origin_iata)
    d = _norm_iata(destination_iata)
    if o == d:
        raise ValueError("origin and destination must differ")

    now = _utcnow()
    row = get_direct_route(db, o, d)
    if row is None:
        row = models.DirectRoute(
            origin_iata=o,
            destination_iata=d,
            is_active=is_active,
            first_seen_at=now,
            last_seen_at=now,
        )
        db.add(row)
        return row

    row.is_active = is_active
    row.last_seen_at = now
    return row


def upsert_direct_route(
    db: Session, origin_iata: str, destination_iata: str, *, is_active: bool = True
) -> models.DirectRoute:
    """Insert or touch a direct route (``last_seen_at`` always updated)."""
    row = _upsert_direct_route_no_commit(db, origin_iata, destination_iata, is_active=is_active)
    db.commit()
    db.refresh(row)
    return row


def list_active_destinations_from_origin(db: Session, origin_iata: str) -> List[Dict[str, Any]]:
    """Return dicts compatible with ``get_direct_destinations`` (``iata``, ``city``, ``country``)."""
    o = _norm_iata(origin_iata)
    rows = (
        db.query(models.Airport)
        .join(
            models.DirectRoute,
            models.DirectRoute.destination_iata == models.Airport.iata,
        )
        .filter(
            models.DirectRoute.origin_iata == o,
            models.DirectRoute.is_active.is_(True),
        )
        .order_by(models.Airport.iata)
        .all()
    )
    return [{"iata": a.iata, "city": a.city, "country": a.country} for a in rows]


def sync_direct_routes_for_origin(
    db: Session, origin_iata: str, destinations: List[Dict[str, Any]]
) -> int:
    """Upsert origin + destination airports and routes; deactivate missing edges.

    ``destinations`` items should look like Amadeus direct-destination entries:
    ``iata``, ``city``, ``country`` (ISO-2). Commits once. Returns active route count for this origin.
    """
    o = _norm_iata(origin_iata)
    _upsert_airport_no_commit(db, schemas.AirportCreate(iata=o))

    seen: Set[str] = set()
    for dest in destinations:
        d_iata = _norm_iata(dest.get("iata"))
        if not d_iata or d_iata == o:
            continue
        seen.add(d_iata)
        _upsert_airport_no_commit(
            db,
            schemas.AirportCreate(
                iata=d_iata,
                city=dest.get("city"),
                country=_norm_country(dest.get("country")),
            ),
        )
        _upsert_direct_route_no_commit(db, o, d_iata, is_active=True)

    deactivate_q = db.query(models.DirectRoute).filter(models.DirectRoute.origin_iata == o)
    if seen:
        deactivate_q = deactivate_q.filter(models.DirectRoute.destination_iata.notin_(list(seen)))
    deactivate_q.update({"is_active": False}, synchronize_session=False)

    db.commit()

    return (
        db.query(models.DirectRoute)
        .filter(
            models.DirectRoute.origin_iata == o,
            models.DirectRoute.is_active.is_(True),
        )
        .count()
    )


def distinct_route_origins(db: Session) -> List[str]:
    """All origins that appear in ``direct_routes`` (for a scheduled refresh job)."""
    rows = db.query(models.DirectRoute.origin_iata).distinct().order_by(models.DirectRoute.origin_iata).all()
    return [r[0] for r in rows]


def start_route_refresh_run(db: Session, origin_iata: str) -> models.RouteRefreshRun:
    run = models.RouteRefreshRun(origin_iata=_norm_iata(origin_iata))
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def complete_route_refresh_run(
    db: Session,
    run_id: int,
    *,
    success: bool,
    routes_found: Optional[int] = None,
    error_message: Optional[str] = None,
) -> Optional[models.RouteRefreshRun]:
    run = db.query(models.RouteRefreshRun).filter(models.RouteRefreshRun.id == run_id).first()
    if not run:
        return None
    run.finished_at = _utcnow()
    run.success = success
    run.routes_found = routes_found
    run.error_message = error_message
    db.commit()
    db.refresh(run)
    return run


def get_route_refresh_runs_for_origin(
    db: Session, origin_iata: str, limit: int = 50
) -> List[models.RouteRefreshRun]:
    return (
        db.query(models.RouteRefreshRun)
        .filter(models.RouteRefreshRun.origin_iata == _norm_iata(origin_iata))
        .order_by(models.RouteRefreshRun.started_at.desc())
        .limit(limit)
        .all()
    )