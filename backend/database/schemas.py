from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from typing import Optional, List, Literal, Dict, Any
import datetime as dt
from decimal import Decimal

from utils.password_policy import validate_password_strength


# ============= User Schemas =============

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

    @field_validator("password")
    @classmethod
    def _password_strength(cls, value: str) -> str:
        return validate_password_strength(value)


class UserUpdate(BaseModel):
    username: Optional[str] = Field(default=None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=8)
    preferred_llm_provider: Optional[Literal["deepseek"]] = None
    home_city: Optional[str] = Field(default=None, max_length=255)
    tutorial_completed: Optional[bool] = None

    @field_validator("password")
    @classmethod
    def _password_strength(cls, value: Optional[str]) -> Optional[str]:
        if value is None or value == "":
            return None
        return validate_password_strength(value)


class UserResponse(UserBase):
    id: int
    created_at: dt.datetime
    preferred_llm_provider: str = "deepseek"
    home_city: Optional[str] = None
    tutorial_completed: bool = False
    email_verified: bool = False

    model_config = ConfigDict(from_attributes=True)


# ============= Authentication Schemas =============
# Request/response bodies for /api/register, /login, /google-login, forgot-password

class LoginRequest(BaseModel):
    username: str
    password: str


class GoogleLoginRequest(BaseModel):
    code: str  # OAuth authorization code from Google Identity (redirect code client)


class LoginResponse(BaseModel):
    success: bool
    user_id: int
    username: str
    access_token: str
    token_type: str = "bearer"
    avatar_url: Optional[str] = None
    tutorial_completed: bool = False


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)

    @field_validator("password")
    @classmethod
    def _password_strength(cls, value: str) -> str:
        return validate_password_strength(value)


class RegisterResponse(BaseModel):
    success: bool
    message: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequestResponse(BaseModel):
    success: bool
    message: str


class ForgotPasswordResetRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def _password_strength(cls, value: str) -> str:
        return validate_password_strength(value)


class ForgotPasswordResetResponse(BaseModel):
    success: bool
    message: str


class VerifyEmailConfirmRequest(BaseModel):
    token: str


class VerifyEmailConfirmResponse(BaseModel):
    success: bool
    message: str


class VerifyEmailResendRequest(BaseModel):
    email: EmailStr


class VerifyEmailResendResponse(BaseModel):
    success: bool
    message: str


# ============= Visited Place Schemas =============

class VisitedPlaceBase(BaseModel):
    place_name: str
    country: Optional[str] = None
    date: Optional[dt.date] = None
    end_date: Optional[dt.date] = None
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
    end_date: Optional[dt.date] = None
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
    end_date: Optional[dt.date] = None
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
    start_latitude: Optional[float] = None
    start_longitude: Optional[float] = None
    people: int = 1
    is_booked: bool = False


class PlannedTripCreate(PlannedTripBase):
    # Optional in the body; create endpoint always sets it from the access token.
    user_id: Optional[int] = None


class PlannedTripUpdate(BaseModel):
    title: Optional[str] = None
    start_date: Optional[dt.date] = None
    end_date: Optional[dt.date] = None
    start_city: Optional[str] = None
    start_latitude: Optional[float] = None
    start_longitude: Optional[float] = None
    people: Optional[int] = None
    is_booked: Optional[bool] = None


class PlannedTripResponse(PlannedTripBase):
    id: int
    user_id: int
    shared_from_user_id: Optional[int] = None
    shared_from_username: Optional[str] = None
    stops: List[TripStopResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ============= Trip Sharing Schemas =============

class TripShareLinkRequest(BaseModel):
    user_id: Optional[int] = None


class TripShareLinkResponse(BaseModel):
    share_token: str
    share_url: str


class TripShareInvitationCreate(BaseModel):
    to_user_id: int
    from_user_id: Optional[int] = None


class TripShareInvitationAction(BaseModel):
    user_id: Optional[int] = None


class TripShareSourceSummary(BaseModel):
    """Compact trip info embedded in invitation responses for the share inbox cards."""
    id: int
    title: str
    start_date: Optional[dt.date] = None
    end_date: Optional[dt.date] = None
    start_city: Optional[str] = None


class TripShareInvitationResponse(BaseModel):
    id: int
    source_trip_id: int
    from_user_id: int
    to_user_id: int
    status: str
    created_at: dt.datetime
    responded_at: Optional[dt.datetime] = None
    result_trip_id: Optional[int] = None
    from_username: Optional[str] = None
    source_trip: Optional[TripShareSourceSummary] = None

    model_config = ConfigDict(from_attributes=True)


class SharedTripPublicResponse(BaseModel):
    """Unauthenticated payload for shared_trip.html (no owner ids)."""
    title: str
    start_date: Optional[dt.date] = None
    end_date: Optional[dt.date] = None
    start_city: Optional[str] = None
    start_latitude: Optional[float] = None
    start_longitude: Optional[float] = None
    people: int = 1
    stops: List[TripStopResponse] = []


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


# ============= Feedback Schemas =============

class FeedbackResponse(BaseModel):
    id: int
    user_id: int
    username: str
    email: Optional[str] = None
    message: str
    image_path: Optional[str] = None
    solved: bool = False
    created_at: dt.datetime

    model_config = ConfigDict(from_attributes=True)


class FeedbackSolvedUpdate(BaseModel):
    solved: bool = True


class NotificationItem(BaseModel):
    id: str
    type: str
    title: str
    body: Optional[str] = None
    href: Optional[str] = None
    created_at: Optional[dt.datetime] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class NotificationsResponse(BaseModel):
    items: List[NotificationItem]
