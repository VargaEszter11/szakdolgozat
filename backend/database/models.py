from sqlalchemy import (
    BigInteger,
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
    Time,
    func,
    text,
)
from sqlalchemy.orm import relationship
from typing import Any, cast

from .database import Base


class User(Base):
    """User model for registered users"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(Text, unique=True, nullable=False, index=True)
    email = Column(Text, unique=True, nullable=False, index=True)
    password = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    preferred_llm_provider = Column(
        Text,
        nullable=False,
        server_default=text("'deepseek'"),
    )
    home_city = Column(Text, nullable=True)
    tutorial_completed = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    # Relationships
    planned_trips = relationship(
        "PlannedTrip",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="PlannedTrip.user_id",
    )
    visited_places = relationship("VisitedPlace", back_populates="user", cascade="all, delete-orphan")
    feedbacks = relationship("Feedback", back_populates="user", cascade="all, delete-orphan")


class PasswordResetToken(Base):
    """Single-use, time-limited token emailed to a user for password reset."""
    __tablename__ = "password_reset_tokens"
    __table_args__ = (
        Index("idx_password_reset_tokens_token_hash", "token_hash", unique=True),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(Text, nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", foreign_keys=[user_id])


class PlannedTrip(Base):
    """User itinerary shown on the Planned Trips page (title, dates, start city, stops)."""
    __tablename__ = "planned_trips"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(Text, nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    start_city = Column(Text, nullable=True)
    start_latitude = Column(Float, nullable=True)
    start_longitude = Column(Float, nullable=True)
    people = Column(Integer, nullable=False, default=1, server_default="1")
    is_booked = Column(Boolean, nullable=False, default=False, server_default="false")
    # Set when this trip was created by accepting a user-to-user share invitation
    shared_from_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    user = relationship("User", back_populates="planned_trips", foreign_keys=[user_id])
    shared_from_user = relationship("User", foreign_keys=[shared_from_user_id])
    stops = relationship("PlannedTripStop", back_populates="trip", cascade="all, delete-orphan")


class PlannedTripStop(Base):
    """One city/stop on a planned trip; latitude/longitude set when the stop is created."""
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
    booking_url = Column(Text, nullable=True)
    flight_availability_verified = Column(Boolean, nullable=True)

    # Relationships
    trip = relationship("PlannedTrip", back_populates="stops")


class TripShareLink(Base):
    """Public read-only share link (?token=) for a planned trip; deactivate via is_active."""
    __tablename__ = "trip_share_links"
    __table_args__ = (
        Index("idx_trip_share_links_token", "share_token", unique=True),
        Index("idx_trip_share_links_trip_active", "trip_id", "is_active"),
    )

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("planned_trips.id", ondelete="CASCADE"), nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    share_token = Column(Text, nullable=False, unique=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime, server_default=func.now())

    trip = relationship("PlannedTrip", foreign_keys=[trip_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])


class TripShareInvitation(Base):
    """In-app share invite; accept copies the trip and sets planned_trips.shared_from_user_id."""
    __tablename__ = "trip_share_invitations"
    __table_args__ = (
        Index("idx_trip_share_invitations_to_status", "to_user_id", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    source_trip_id = Column(Integer, ForeignKey("planned_trips.id", ondelete="CASCADE"), nullable=False)
    from_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    to_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(Text, nullable=False, default="pending", server_default=text("'pending'"))
    created_at = Column(DateTime, server_default=func.now())
    responded_at = Column(DateTime, nullable=True)
    result_trip_id = Column(Integer, ForeignKey("planned_trips.id", ondelete="SET NULL"), nullable=True)

    source_trip = relationship("PlannedTrip", foreign_keys=[source_trip_id])
    from_user = relationship("User", foreign_keys=[from_user_id])
    to_user = relationship("User", foreign_keys=[to_user_id])
    result_trip = relationship("PlannedTrip", foreign_keys=[result_trip_id])


class VisitedPlace(Base):
    """Visited place model for places users have already visited"""
    __tablename__ = "visited_places"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    place_name = Column(Text, nullable=False)
    country = Column(Text, nullable=True)
    date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
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
    visited_place_id = Column(
        Integer,
        ForeignKey("visited_places.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Persisted column name is `url` (existing PostgreSQL schema); attribute stays image_path in code.
    image_path = Column("url", Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    visited_place = relationship("VisitedPlace", back_populates="images")


class Airline(Base):
    """Airline metadata used by direct routes."""
    __tablename__ = "airlines"
    __table_args__ = (Index("idx_airlines_name", "name"),)

    iata = Column(String(2), primary_key=True)
    icao = Column(String(3), nullable=True)
    name = Column(Text, nullable=False)
    website = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    routes = relationship("DirectRoute", back_populates="airline")


class Airport(Base):
    """Cached airport metadata (lazily populated on first use)."""
    __tablename__ = "airports"

    iata = Column(String(3), primary_key=True)
    icao = Column(String(4), nullable=True)
    name = Column(Text, nullable=False)
    city = Column(Text, nullable=True)
    country_code = Column(String(2), nullable=True, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    timezone = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

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

    @property
    def country(self) -> str | None:
        """Compatibility for older cache code that still reads airport.country."""
        return cast(str | None, self.country_code)

    @country.setter
    def country(self, value: str | None) -> None:
        cast(Any, self).country_code = value


class DirectRoute(Base):
    """A directed direct-flight edge between two airports."""
    __tablename__ = "direct_routes"
    __table_args__ = (
        CheckConstraint("origin_iata <> destination_iata", name="chk_different_airports"),
        Index("idx_routes_origin", "origin_iata"),
        Index("idx_routes_destination", "destination_iata"),
        Index("idx_routes_airline", "airline_iata"),
        Index("idx_routes_active", "is_active"),
        Index(
            "uniq_route",
            "airline_iata",
            "origin_iata",
            "destination_iata",
            unique=True,
        ),
    )

    id = Column(BigInteger, primary_key=True, index=True)
    airline_iata = Column(
        String(2),
        ForeignKey("airlines.iata", ondelete="SET NULL"),
        nullable=True,
    )
    airline_name = Column(Text, nullable=True)
    flight_number = Column(Text, nullable=False)
    origin_iata = Column(
        String(3),
        ForeignKey("airports.iata", ondelete="CASCADE"),
        nullable=False,
    )
    destination_iata = Column(
        String(3),
        ForeignKey("airports.iata", ondelete="CASCADE"),
        nullable=False,
    )
    dep_time = Column(Time, nullable=True)
    arr_time = Column(Time, nullable=True)
    aircraft = Column(Text, nullable=True)
    effective_from = Column(Date, nullable=True)
    effective_to = Column(Date, nullable=True)
    is_seasonal = Column(Boolean, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    airline = relationship("Airline", back_populates="routes")
    origin = relationship("Airport", foreign_keys=[origin_iata], back_populates="outgoing_routes")
    destination = relationship("Airport", foreign_keys=[destination_iata], back_populates="incoming_routes")


class Feedback(Base):
    """User-submitted feedback visible on the admin page."""
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    image_path = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="feedbacks")

