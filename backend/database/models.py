from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Numeric, Float, ForeignKey, func
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    """User model for registered users"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(Text, unique=True, nullable=False, index=True)
    email = Column(Text, unique=True, nullable=False, index=True)
    password = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    planned_trips = relationship("PlannedTrip", back_populates="user", cascade="all, delete-orphan")
    visited_places = relationship("VisitedPlace", back_populates="user", cascade="all, delete-orphan")


class PlannedTrip(Base):
    """Planned trip model for user's planned trips"""
    __tablename__ = "planned_trips"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(Text, nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    start_city = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="planned_trips")
    stops = relationship("PlannedTripStop", back_populates="trip", cascade="all, delete-orphan")


class PlannedTripStop(Base):
    """Individual stop within a planned trip"""
    __tablename__ = "planned_trip_stops"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("planned_trips.id", ondelete="CASCADE"), nullable=False)
    place_name = Column(Text, nullable=False)
    country = Column(Text, nullable=True)
    stop_order = Column(Integer, nullable=True)
    arrival_date = Column(Date, nullable=True)
    departure_date = Column(Date, nullable=True)
    transport_from_last = Column(Text, nullable=True)
    activities = Column(Text, nullable=True)
    estimated_price = Column(Numeric(10, 2), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Relationships
    trip = relationship("PlannedTrip", back_populates="stops")


class VisitedPlace(Base):
    """Visited place model for places users have already visited"""
    __tablename__ = "visited_places"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    place_name = Column(Text, nullable=False)
    country = Column(Text, nullable=True)
    date = Column(Date, nullable=True)
    rating = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    photo_path = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Relationships
    user = relationship("User", back_populates="visited_places")
