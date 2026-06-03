from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Union, Literal
import datetime as dt
from decimal import Decimal


# ============= User Schemas =============

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6)
    preferred_llm_provider: Optional[Literal["deepseek", "ollama"]] = None


class UserResponse(UserBase):
    id: int
    created_at: dt.datetime
    preferred_llm_provider: str = "deepseek"

    model_config = ConfigDict(from_attributes=True)


# ============= Authentication Schemas =============

class LoginRequest(BaseModel):
    username: str
    password: str


class GoogleLoginRequest(BaseModel):
    credential: str


class LoginResponse(BaseModel):
    success: bool
    user_id: int
    username: str


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)


class RegisterResponse(BaseModel):
    success: bool
    message: str


class ForgotPasswordVerifyRequest(BaseModel):
    username: str
    email: EmailStr


class ForgotPasswordVerifyResponse(BaseModel):
    success: bool
    user_id: int


class ForgotPasswordResetRequest(BaseModel):
    user_id: int
    new_password: str = Field(..., min_length=6)


class ForgotPasswordResetResponse(BaseModel):
    success: bool
    message: str


# ============= Visited Place Schemas =============

class VisitedPlaceBase(BaseModel):
    place_name: str
    country: Optional[str] = None
    date: Optional[dt.date] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    description: Optional[str] = None
    photo_path: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class VisitedPlaceCreate(VisitedPlaceBase):
    user_id: int


class VisitedPlaceUpdate(BaseModel):
    place_name: Optional[str] = None
    country: Optional[str] = None
    date: Optional[dt.date] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    description: Optional[str] = None
    photo_path: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class VisitedPlaceResponse(BaseModel):
    id: int
    user_id: int
    place_name: str
    country: Optional[str] = None
    date: Optional[dt.date] = None
    rating: Optional[int] = None
    description: Optional[str] = None
    photo_path: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    image: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ============= Trip Stop Schemas =============

class TripStopBase(BaseModel):
    place_name: str
    country: Optional[str] = None
    stop_order: Optional[int] = None
    arrival_date: Optional[dt.date] = None
    departure_date: Optional[dt.date] = None
    transport_from_last: Optional[str] = None
    activities: Optional[str] = None
    estimated_price: Optional[Decimal] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    booking_url: Optional[str] = None
    flight_availability_verified: Optional[bool] = None


class TripStopCreate(TripStopBase):
    trip_id: int


class TripStopUpdate(BaseModel):
    place_name: Optional[str] = None
    country: Optional[str] = None
    stop_order: Optional[int] = None
    arrival_date: Optional[dt.date] = None
    departure_date: Optional[dt.date] = None
    transport_from_last: Optional[str] = None
    activities: Optional[str] = None
    estimated_price: Optional[Decimal] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    booking_url: Optional[str] = None
    flight_availability_verified: Optional[bool] = None


class TripStopResponse(TripStopBase):
    id: int
    trip_id: int

    model_config = ConfigDict(from_attributes=True)


# ============= Planned Trip Schemas =============

class PlannedTripBase(BaseModel):
    title: str
    start_date: Optional[dt.date] = None
    end_date: Optional[dt.date] = None
    start_city: Optional[str] = None
    people: int = 1
    is_booked: bool = False


class PlannedTripCreate(PlannedTripBase):
    user_id: int


class PlannedTripUpdate(BaseModel):
    title: Optional[str] = None
    start_date: Optional[dt.date] = None
    end_date: Optional[dt.date] = None
    start_city: Optional[str] = None
    people: Optional[int] = None
    is_booked: Optional[bool] = None


class PlannedTripResponse(PlannedTripBase):
    id: int
    user_id: int
    stops: List[TripStopResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ============= Extended User Response with Relations =============

class UserWithRelationsResponse(UserResponse):
    planned_trips: List[PlannedTripResponse] = []
    visited_places: List[VisitedPlaceResponse] = []

    model_config = ConfigDict(from_attributes=True)

# ============= Image Schemas =============

class ImageBase(BaseModel):
    image_path: str


class ImageCreate(ImageBase):
    visited_place_id: int


class ImageCreateBody(BaseModel):
    """POST body for `/visited-places/{place_id}/images` (place id comes from the URL)."""

    image_path: str


class ImageUpdate(BaseModel):
    image_path: Optional[str] = None


class ImageResponse(ImageBase):
    id: int
    visited_place_id: int
    created_at: dt.datetime

    model_config = ConfigDict(from_attributes=True)


# ============= Airline Schemas =============

class AirlineBase(BaseModel):
    iata: str = Field(..., min_length=2, max_length=2)
    icao: Optional[str] = Field(None, min_length=3, max_length=3)
    name: str
    website: Optional[str] = None


class AirlineCreate(AirlineBase):
    pass


class AirlineUpdate(BaseModel):
    icao: Optional[str] = Field(None, min_length=3, max_length=3)
    name: Optional[str] = None
    website: Optional[str] = None


class AirlineResponse(AirlineBase):
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = ConfigDict(from_attributes=True)


# ============= Airport Schemas =============

class AirportBase(BaseModel):
    iata: str = Field(..., min_length=3, max_length=3)
    icao: Optional[str] = Field(None, min_length=4, max_length=4)
    name: str
    city: Optional[str] = None
    country_code: Optional[str] = Field(None, min_length=2, max_length=2)
    # Compatibility with older cache callers that still submit/read `country`.
    country: Optional[str] = Field(None, min_length=2, max_length=2)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None


class AirportCreate(AirportBase):
    # Cache callers may only know the IATA code; CRUD fills name with the code.
    name: Optional[str] = None


class AirportUpdate(BaseModel):
    icao: Optional[str] = Field(None, min_length=4, max_length=4)
    name: Optional[str] = None
    city: Optional[str] = None
    country_code: Optional[str] = Field(None, min_length=2, max_length=2)
    country: Optional[str] = Field(None, min_length=2, max_length=2)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None


class AirportResponse(AirportBase):
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = ConfigDict(from_attributes=True)


# ============= Direct Route Schemas =============

class DirectRouteBase(BaseModel):
    airline_iata: Optional[str] = Field(None, min_length=2, max_length=2)
    airline_name: Optional[str] = None
    flight_number: str = "DIRECT"
    origin_iata: str = Field(..., min_length=3, max_length=3)
    destination_iata: str = Field(..., min_length=3, max_length=3)
    dep_time: Optional[dt.time] = None
    arr_time: Optional[dt.time] = None
    aircraft: Optional[str] = None
    effective_from: Optional[dt.date] = None
    effective_to: Optional[dt.date] = None
    is_active: bool = True


class DirectRouteCreate(DirectRouteBase):
    pass


class DirectRouteUpdate(BaseModel):
    airline_iata: Optional[str] = Field(None, min_length=2, max_length=2)
    airline_name: Optional[str] = None
    flight_number: Optional[str] = None
    origin_iata: Optional[str] = Field(None, min_length=3, max_length=3)
    destination_iata: Optional[str] = Field(None, min_length=3, max_length=3)
    dep_time: Optional[dt.time] = None
    arr_time: Optional[dt.time] = None
    aircraft: Optional[str] = None
    effective_from: Optional[dt.date] = None
    effective_to: Optional[dt.date] = None
    is_active: Optional[bool] = None


class DirectRouteResponse(DirectRouteBase):
    id: int
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = ConfigDict(from_attributes=True)


class RouteDayBase(BaseModel):
    route_id: int
    weekday: int = Field(..., ge=1, le=7)


class RouteDayCreate(RouteDayBase):
    pass


class RouteDayResponse(RouteDayBase):
    model_config = ConfigDict(from_attributes=True)


# ============= Route Price Schemas =============

class RoutePriceBase(BaseModel):
    route_id: int
    departure_date: dt.date
    currency: str = Field(..., min_length=3, max_length=3)
    price: Decimal
    booking_url: Optional[str] = None
    provider: Optional[str] = None


class RoutePriceCreate(RoutePriceBase):
    pass


class RoutePriceUpdate(BaseModel):
    departure_date: Optional[dt.date] = None
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    price: Optional[Decimal] = None
    booking_url: Optional[str] = None
    provider: Optional[str] = None


class RoutePriceResponse(RoutePriceBase):
    id: int
    fetched_at: dt.datetime

    model_config = ConfigDict(from_attributes=True)


# ============= Route Refresh Run Schemas =============

class RouteRefreshRunBase(BaseModel):
    origin_iata: str = Field(..., min_length=3, max_length=3)
    routes_found: Optional[int] = None
    success: bool = False
    error_message: Optional[str] = None


class RouteRefreshRunCreate(BaseModel):
    origin_iata: str = Field(..., min_length=3, max_length=3)


class RouteRefreshRunResponse(RouteRefreshRunBase):
    id: int
    started_at: dt.datetime
    finished_at: Optional[dt.datetime] = None

    model_config = ConfigDict(from_attributes=True)