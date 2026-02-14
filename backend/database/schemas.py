from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Union
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


class UserResponse(UserBase):
    id: int
    created_at: dt.datetime

    class Config:
        from_attributes = True


# ============= Authentication Schemas =============

class LoginRequest(BaseModel):
    username: str
    password: str


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

    class Config:
        from_attributes = True


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


class TripStopResponse(TripStopBase):
    id: int
    trip_id: int

    class Config:
        from_attributes = True


# ============= Planned Trip Schemas =============

class PlannedTripBase(BaseModel):
    title: str
    start_date: Optional[dt.date] = None
    end_date: Optional[dt.date] = None
    start_city: Optional[str] = None


class PlannedTripCreate(PlannedTripBase):
    user_id: int


class PlannedTripUpdate(BaseModel):
    title: Optional[str] = None
    start_date: Optional[dt.date] = None
    end_date: Optional[dt.date] = None
    start_city: Optional[str] = None


class PlannedTripResponse(PlannedTripBase):
    id: int
    user_id: int
    stops: List[TripStopResponse] = []

    class Config:
        from_attributes = True


# ============= Extended User Response with Relations =============

class UserWithRelationsResponse(UserResponse):
    planned_trips: List[PlannedTripResponse] = []
    visited_places: List[VisitedPlaceResponse] = []

    class Config:
        from_attributes = True
