from sqlalchemy.orm import Session
import bcrypt
from typing import List, Optional
from . import models, schemas


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
    return db.query(models.VisitedPlace).filter(models.VisitedPlace.user_id == user_id).all()


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
    db_place = get_visited_place(db, place_id)
    if not db_place:
        return False
    
    db.delete(db_place)
    db.commit()
    return True
