from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Date,
    DateTime,
    Numeric,
    Float,
    Boolean,
    ForeignKey,
    CheckConstraint,
    Index,
    func,
    text,
)
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
    use_travel_log_in_planner = Column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    preferred_llm_provider = Column(
        Text,
        nullable=False,
        server_default=text("'deepseek'"),
    )

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
    images = relationship("Image", back_populates="visited_place", cascade="all, delete-orphan")

class Image(Base):
    """Image model for images uploaded by users"""
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    visited_place_id = Column(Integer, ForeignKey("visited_places.id", ondelete="CASCADE"), nullable=False)
    # Persisted column name is `url` (existing PostgreSQL schema); attribute stays image_path in code.
    image_path = Column("url", Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    visited_place = relationship("VisitedPlace", back_populates="images")


class Airport(Base):
    """Cached airport metadata (lazily populated on first use)."""
    __tablename__ = "airports"

    iata = Column(String(3), primary_key=True)
    icao = Column(String(4), nullable=True)
    city = Column(Text, nullable=True)
    country = Column(String(2), nullable=True, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    first_seen_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    outgoing_routes = relationship(
        "DirectRoute",
        foreign_keys="DirectRoute.origin_iata",
        back_populates="origin",
        cascade="all, delete-orphan",
    )
    incoming_routes = relationship(
        "DirectRoute",
        foreign_keys="DirectRoute.destination_iata",
        back_populates="destination",
        cascade="all, delete-orphan",
    )


class DirectRoute(Base):
    """A directed direct-flight edge between two airports."""
    __tablename__ = "direct_routes"
    __table_args__ = (
        CheckConstraint("origin_iata <> destination_iata", name="ck_route_not_self"),
        Index("idx_direct_routes_origin", "origin_iata"),
        Index("idx_direct_routes_dest", "destination_iata"),
    )

    origin_iata = Column(
        String(3),
        ForeignKey("airports.iata", ondelete="CASCADE"),
        primary_key=True,
    )
    destination_iata = Column(
        String(3),
        ForeignKey("airports.iata", ondelete="CASCADE"),
        primary_key=True,
    )
    first_seen_at = Column(DateTime, server_default=func.now(), nullable=False)
    last_seen_at = Column(DateTime, server_default=func.now(), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    origin = relationship("Airport", foreign_keys=[origin_iata], back_populates="outgoing_routes")
    destination = relationship("Airport", foreign_keys=[destination_iata], back_populates="incoming_routes")


class RouteRefreshRun(Base):
    """Bookkeeping for the weekly direct-destinations refresh job."""
    __tablename__ = "route_refresh_runs"

    id = Column(Integer, primary_key=True, index=True)
    origin_iata = Column(
        String(3),
        ForeignKey("airports.iata", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    started_at = Column(DateTime, server_default=func.now(), nullable=False)
    finished_at = Column(DateTime, nullable=True)
    routes_found = Column(Integer, nullable=True)
    success = Column(Boolean, nullable=False, default=False)
    error_message = Column(Text, nullable=True)