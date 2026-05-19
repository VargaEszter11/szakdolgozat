from sqlalchemy import (
    BigInteger,
    Column,
    Integer,
    SmallInteger,
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

    @property
    def country(self) -> str | None:
        """Compatibility for older cache code that still reads airport.country."""
        return self.country_code

    @country.setter
    def country(self, value: str | None) -> None:
        self.country_code = value


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
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    airline = relationship("Airline", back_populates="routes")
    origin = relationship("Airport", foreign_keys=[origin_iata], back_populates="outgoing_routes")
    destination = relationship("Airport", foreign_keys=[destination_iata], back_populates="incoming_routes")
    operating_days = relationship("RouteDay", back_populates="route", cascade="all, delete-orphan")
    price_cache = relationship("RoutePrice", back_populates="route", cascade="all, delete-orphan")


class RouteDay(Base):
    """Operating weekday for a direct route (1=Monday, 7=Sunday)."""
    __tablename__ = "route_days"
    __table_args__ = (
        CheckConstraint("weekday BETWEEN 1 AND 7", name="chk_weekday"),
        Index("idx_route_days_weekday", "weekday"),
    )

    route_id = Column(
        BigInteger,
        ForeignKey("direct_routes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    weekday = Column(SmallInteger, primary_key=True)

    route = relationship("DirectRoute", back_populates="operating_days")


class RoutePrice(Base):
    """Cached provider price for a route/date pair."""
    __tablename__ = "route_prices"
    __table_args__ = (
        Index("idx_route_prices_route", "route_id"),
        Index("idx_route_prices_departure", "departure_date"),
    )

    id = Column(BigInteger, primary_key=True, index=True)
    route_id = Column(
        BigInteger,
        ForeignKey("direct_routes.id", ondelete="CASCADE"),
        nullable=False,
    )
    departure_date = Column(Date, nullable=False)
    currency = Column(String(3), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    booking_url = Column(Text, nullable=True)
    provider = Column(Text, nullable=True)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    route = relationship("DirectRoute", back_populates="price_cache")


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