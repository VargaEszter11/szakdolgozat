from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session, joinedload
import bcrypt
import hashlib
import re
import secrets
from typing import Any, Dict, List, Optional, Set, cast
from . import models, schemas
from .airport_city import airport_name_as_city
from .airport_regions import is_europe_country
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


def search_users(
    db: Session,
    *,
    search: Optional[str] = None,
    exclude_user_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 20,
) -> List[models.User]:
    """Search users by username substring."""
    query = db.query(models.User)
    if exclude_user_id is not None:
        query = query.filter(models.User.id != exclude_user_id)
    if search:
        term = search.strip()
        if term:
            query = query.filter(models.User.username.ilike(f"%{term}%"))
    return query.order_by(models.User.username).offset(skip).limit(limit).all()


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


# ============= Password Reset Token CRUD Operations =============

PASSWORD_RESET_TOKEN_TTL_MINUTES = 30


def _hash_reset_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_password_reset_token(db: Session, user_id: int) -> str:
    """Issue a single-use password reset token, invalidating any prior unused ones.

    Returns the raw token; only this call ever sees it in plaintext (only its
    hash is persisted), so it must be emailed to the user immediately.
    """
    db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.user_id == user_id,
        models.PasswordResetToken.used_at.is_(None),
    ).delete()

    raw_token = secrets.token_urlsafe(32)
    db_token = models.PasswordResetToken(
        user_id=user_id,
        token_hash=_hash_reset_token(raw_token),
        expires_at=_utcnow_naive() + timedelta(minutes=PASSWORD_RESET_TOKEN_TTL_MINUTES),
    )
    db.add(db_token)
    db.commit()
    return raw_token


def get_valid_password_reset_token(db: Session, raw_token: str) -> Optional[models.PasswordResetToken]:
    """Look up an unused, unexpired password reset token by its raw value."""
    token_row = (
        db.query(models.PasswordResetToken)
        .filter(models.PasswordResetToken.token_hash == _hash_reset_token(raw_token))
        .first()
    )
    if not token_row:
        return None
    row = cast(Any, token_row)
    if row.used_at is not None or row.expires_at < _utcnow_naive():
        return None
    return token_row


def consume_password_reset_token(db: Session, token_row: models.PasswordResetToken) -> None:
    """Mark a password reset token as used so it cannot be replayed."""
    row = cast(Any, token_row)
    row.used_at = _utcnow_naive()
    db.commit()


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

    if "arrival_date" in update_data:
        stop_row = cast(Any, db_stop)
        new_arrival = update_data["arrival_date"]
        if stop_row.booking_url and new_arrival:
            from travel_types.booking import update_booking_url_date

            stop_row.booking_url = update_booking_url_date(stop_row.booking_url, str(new_arrival))

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
    image_row = cast(Any, db_image)

    update_data = image_update.model_dump(exclude_unset=True)
    old_path: Optional[str] = None
    if "image_path" in update_data:
        old_path = image_row.image_path

    for key, value in update_data.items():
        setattr(db_image, key, value)

    db.commit()
    db.refresh(db_image)

    if old_path and old_path != image_row.image_path:
        delete_file_for_public_path(old_path)

    return db_image


def delete_image(db: Session, image_id: int) -> bool:
    """Delete an image"""
    db_image = get_image(db, image_id)
    if not db_image:
        return False

    path = cast(Any, db_image).image_path
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
    legacy_country = data.pop("country", None)
    if data.get("country_code") or legacy_country:
        data["country_code"] = _norm_country(data.get("country_code") or legacy_country)
    if data.get("icao"):
        data["icao"] = str(data["icao"]).strip().upper()
    if not data.get("name"):
        data["name"] = data["iata"]
    db_airport = models.Airport(**data)
    db.add(db_airport)
    db.commit()
    db.refresh(db_airport)
    return db_airport


def _upsert_airport_no_commit(db: Session, airport: schemas.AirportCreate) -> models.Airport:
    iata = _norm_iata(airport.iata)
    row = get_airport(db, iata)
    country = _norm_country(airport.country_code or airport.country)
    icao = airport.icao.strip().upper() if airport.icao else None
    name = airport.name or iata

    if row is None:
        row = models.Airport(
            iata=iata,
            icao=icao,
            name=name,
            city=airport.city,
            country_code=country,
            latitude=airport.latitude,
            longitude=airport.longitude,
            timezone=airport.timezone,
        )
        db.add(row)
        return row

    airport_row = cast(Any, row)
    if icao is not None:
        airport_row.icao = icao
    if airport.name is not None:
        airport_row.name = airport.name
    if airport.city is not None:
        airport_row.city = airport.city
    if country is not None:
        airport_row.country_code = country
    if airport.latitude is not None:
        airport_row.latitude = airport.latitude
    if airport.longitude is not None:
        airport_row.longitude = airport.longitude
    if airport.timezone is not None:
        airport_row.timezone = airport.timezone
    airport_row.updated_at = _utcnow()
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
    legacy_country = update_data.pop("country", None)
    if "icao" in update_data and update_data["icao"] is not None:
        update_data["icao"] = str(update_data["icao"]).strip().upper()
    if "country_code" in update_data and update_data["country_code"] is not None:
        update_data["country_code"] = _norm_country(update_data["country_code"])
    elif legacy_country is not None:
        update_data["country_code"] = _norm_country(legacy_country)

    for key, value in update_data.items():
        setattr(row, key, value)
    cast(Any, row).updated_at = _utcnow()

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
    if data.get("airline_iata"):
        data["airline_iata"] = str(data["airline_iata"]).strip().upper()
    if not data.get("flight_number"):
        data["flight_number"] = "DIRECT"
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
            flight_number="DIRECT",
            is_active=is_active,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        return row

    route_row = cast(Any, row)
    route_row.is_active = is_active
    route_row.updated_at = now
    return row


def upsert_direct_route(
    db: Session, origin_iata: str, destination_iata: str, *, is_active: bool = True
) -> models.DirectRoute:
    """Insert or touch a direct route (``updated_at`` always updated)."""
    row = _upsert_direct_route_no_commit(db, origin_iata, destination_iata, is_active=is_active)
    db.commit()
    db.refresh(row)
    return row


def list_active_destinations_from_origin(db: Session, origin_iata: str) -> List[Dict[str, Any]]:
    """Return active destination airports as ``iata``, ``city``, and ``country`` dicts."""
    o = _norm_iata(origin_iata)
    rows = (
        db.query(models.Airport, models.DirectRoute)
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
    return [
        {
            "iata": airport.iata,
            "city": airport.city or _airport_name_as_city(airport.name, airport.iata),
            "country": airport.country_code,
            "airline_iata": route.airline_iata,
            "airline_name": route.airline_name,
            "is_seasonal": route.is_seasonal,
            "effective_from": route.effective_from.isoformat() if route.effective_from else None,
            "effective_to": route.effective_to.isoformat() if route.effective_to else None,
        }
        for airport, route in rows
    ]


def _airport_name_as_city(name: Optional[str], iata: str) -> str:
    return airport_name_as_city(name, iata)


def sync_direct_routes_for_origin(
    db: Session, origin_iata: str, destinations: List[Dict[str, Any]]
) -> int:
    """Upsert origin + destination airports and routes; deactivate missing edges.

    ``destinations`` items should contain ``iata``, ``city``, and ``country`` (ISO-2).
    Commits once. Returns active route count for this origin.
    """
    o = _norm_iata(origin_iata)
    _upsert_airport_no_commit(
        db,
        schemas.AirportCreate(
            iata=o,
            icao=None,
            country_code=None,
            country=None,
        ),
    )

    seen: Set[str] = set()
    for dest in destinations:
        d_iata = _norm_iata(dest.get("iata"))
        country = _norm_country(dest.get("country"))
        if not d_iata or d_iata == o or not is_europe_country(country):
            continue
        seen.add(d_iata)
        _upsert_airport_no_commit(
            db,
            schemas.AirportCreate(
                iata=d_iata,
                icao=None,
                city=dest.get("city"),
                country_code=None,
                country=country,
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




# ============= Trip Sharing CRUD =============

def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _assert_trip_owner(trip: Optional[models.PlannedTrip], user_id: int) -> models.PlannedTrip:
    if trip is None:
        raise ValueError("trip_not_found")
    trip_row = cast(Any, trip)
    if int(trip_row.user_id) != int(user_id):
        raise ValueError("not_owner")
    return trip


def share_url_for_token(share_token: str) -> str:
    return f"/share?token={share_token}"


def create_or_get_trip_share_link(
    db: Session, trip_id: int, user_id: int
) -> models.TripShareLink:
    """Create or reuse an active public share link for a trip."""
    trip = _assert_trip_owner(get_planned_trip(db, trip_id), user_id)

    existing = (
        db.query(models.TripShareLink)
        .filter(
            models.TripShareLink.trip_id == trip.id,
            models.TripShareLink.is_active.is_(True),
        )
        .first()
    )
    if existing:
        return existing

    link = models.TripShareLink(
        trip_id=trip.id,
        created_by_user_id=user_id,
        share_token=secrets.token_urlsafe(24),
        is_active=True,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def revoke_trip_share_link(db: Session, trip_id: int, user_id: int) -> bool:
    """Deactivate all active share links for a trip owned by the user."""
    _assert_trip_owner(get_planned_trip(db, trip_id), user_id)
    links = (
        db.query(models.TripShareLink)
        .filter(
            models.TripShareLink.trip_id == trip_id,
            models.TripShareLink.is_active.is_(True),
        )
        .all()
    )
    if not links:
        return False
    for link in links:
        cast(Any, link).is_active = False
    db.commit()
    return True


def get_active_share_link_by_token(
    db: Session, token: str
) -> Optional[models.TripShareLink]:
    if not token or not token.strip():
        return None
    return (
        db.query(models.TripShareLink)
        .filter(
            models.TripShareLink.share_token == token.strip(),
            models.TripShareLink.is_active.is_(True),
        )
        .first()
    )


def copy_planned_trip_for_user(
    db: Session,
    source_trip: models.PlannedTrip,
    recipient_user_id: int,
    *,
    title_prefix: str = "Shared: ",
) -> models.PlannedTrip:
    """Duplicate a planned trip and its stops for another user."""
    source_row = cast(Any, source_trip)
    title = str(source_row.title or "Trip")
    if title_prefix and not title.startswith(title_prefix):
        title = f"{title_prefix}{title}"

    new_trip = models.PlannedTrip(
        user_id=recipient_user_id,
        title=title,
        start_date=source_row.start_date,
        end_date=source_row.end_date,
        start_city=source_row.start_city,
        people=source_row.people or 1,
        is_booked=False,
    )
    db.add(new_trip)
    db.flush()

    for stop in get_trip_stops(db, int(source_row.id)):
        stop_row = cast(Any, stop)
        db.add(
            models.PlannedTripStop(
                trip_id=new_trip.id,
                place_name=stop_row.place_name,
                country=stop_row.country,
                stop_order=stop_row.stop_order,
                arrival_date=stop_row.arrival_date,
                departure_date=stop_row.departure_date,
                transport_from_last=stop_row.transport_from_last,
                activities=stop_row.activities,
                estimated_price=stop_row.estimated_price,
                latitude=stop_row.latitude,
                longitude=stop_row.longitude,
                booking_url=stop_row.booking_url,
                flight_availability_verified=stop_row.flight_availability_verified,
            )
        )

    db.commit()
    db.refresh(new_trip)
    return new_trip


def create_trip_share_invitation(
    db: Session, trip_id: int, from_user_id: int, to_user_id: int
) -> models.TripShareInvitation:
    if from_user_id == to_user_id:
        raise ValueError("cannot_share_with_self")

    _assert_trip_owner(get_planned_trip(db, trip_id), from_user_id)

    recipient = get_user(db, to_user_id)
    if recipient is None:
        raise ValueError("recipient_not_found")

    pending = (
        db.query(models.TripShareInvitation)
        .filter(
            models.TripShareInvitation.source_trip_id == trip_id,
            models.TripShareInvitation.to_user_id == to_user_id,
            models.TripShareInvitation.status == "pending",
        )
        .first()
    )
    if pending:
        raise ValueError("invitation_already_pending")

    invitation = models.TripShareInvitation(
        source_trip_id=trip_id,
        from_user_id=from_user_id,
        to_user_id=to_user_id,
        status="pending",
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return invitation


def get_trip_share_invitation(db: Session, invitation_id: int) -> Optional[models.TripShareInvitation]:
    return (
        db.query(models.TripShareInvitation)
        .filter(models.TripShareInvitation.id == invitation_id)
        .first()
    )


def list_trip_share_invitations_for_user(
    db: Session, user_id: int, status: str = "pending"
) -> List[models.TripShareInvitation]:
    query = db.query(models.TripShareInvitation).filter(
        models.TripShareInvitation.to_user_id == user_id
    )
    if status:
        query = query.filter(models.TripShareInvitation.status == status)
    return query.order_by(models.TripShareInvitation.created_at.desc()).all()


def accept_trip_share_invitation(
    db: Session, invitation_id: int, user_id: int
) -> models.TripShareInvitation:
    invitation = get_trip_share_invitation(db, invitation_id)
    if invitation is None:
        raise ValueError("invitation_not_found")

    inv_row = cast(Any, invitation)
    if int(inv_row.to_user_id) != int(user_id):
        raise ValueError("not_recipient")
    if inv_row.status != "pending":
        raise ValueError("invitation_not_pending")

    source_trip = get_planned_trip(db, int(inv_row.source_trip_id))
    if source_trip is None:
        raise ValueError("source_trip_not_found")

    new_trip = copy_planned_trip_for_user(db, source_trip, user_id)
    inv_row.status = "accepted"
    inv_row.responded_at = _utcnow_naive()
    inv_row.result_trip_id = new_trip.id
    db.commit()
    db.refresh(invitation)
    return invitation


def decline_trip_share_invitation(
    db: Session, invitation_id: int, user_id: int
) -> models.TripShareInvitation:
    invitation = get_trip_share_invitation(db, invitation_id)
    if invitation is None:
        raise ValueError("invitation_not_found")

    inv_row = cast(Any, invitation)
    if int(inv_row.to_user_id) != int(user_id):
        raise ValueError("not_recipient")
    if inv_row.status != "pending":
        raise ValueError("invitation_not_pending")

    inv_row.status = "declined"
    inv_row.responded_at = _utcnow_naive()
    db.commit()
    db.refresh(invitation)
    return invitation