import pytest
from decimal import Decimal
from pydantic import ValidationError

from backend.database import schemas

def test_user_create_valid():
    user = schemas.UserCreate(
        username="john_doe",
        email="john@example.com",
        password="secret123",
    )

    assert user.username == "john_doe"


def test_user_create_password_too_short():
    with pytest.raises(ValidationError):
        schemas.UserCreate(
            username="john_doe",
            email="john@example.com",
            password="123",  # too short
        )


def test_user_update_allows_partial():
    update = schemas.UserUpdate(username="new_name", password=None)

    assert update.username == "new_name"
    assert update.email is None

def test_visited_place_rating_bounds():
    valid = schemas.VisitedPlaceCreate(
        user_id=1,
        place_name="Paris",
        rating=5,
    )

    assert valid.rating == 5


def test_visited_place_rating_too_low():
    with pytest.raises(ValidationError):
        schemas.VisitedPlaceCreate(
            user_id=1,
            place_name="Paris",
            rating=0,
        )


def test_visited_place_rating_too_high():
    with pytest.raises(ValidationError):
        schemas.VisitedPlaceCreate(
            user_id=1,
            place_name="Paris",
            rating=10,
        )

def test_trip_stop_decimal_price():
    stop = schemas.TripStopCreate(
        trip_id=1,
        place_name="Rome",
        estimated_price=Decimal("199.99"),
    )

    assert stop.estimated_price == Decimal("199.99")

def test_airport_iata_length_validation():
    with pytest.raises(ValidationError):
        schemas.AirportCreate(
            iata="BU",  # too short
            icao=None,
            name="Budapest",
            country_code=None,
            country=None,
        )


def test_airport_country_code_validation():
    airport = schemas.AirportCreate(
        iata="BUD",
        icao=None,
        name="Budapest",
        country_code="HU",
        country=None,
    )

    assert airport.country_code == "HU"

def test_direct_route_default_flight_number():
    route = schemas.DirectRouteCreate(
        airline_iata=None,
        origin_iata="BUD",
        destination_iata="LHR",
    )

    assert route.flight_number == "DIRECT"


def test_feedback_create_valid():
    fb = schemas.FeedbackCreate(message="Great trip planner")
    assert fb.message == "Great trip planner"


def test_feedback_create_rejects_empty():
    with pytest.raises(ValidationError):
        schemas.FeedbackCreate(message="")


def test_feedback_create_rejects_too_long():
    with pytest.raises(ValidationError):
        schemas.FeedbackCreate(message="x" * 2001)


def test_feedback_response_fields():
    from datetime import datetime

    fb = schemas.FeedbackResponse(
        id=1,
        user_id=2,
        username="alice",
        email="a@example.com",
        message="Hi",
        image_path="/uploads/feedback_images/a.jpg",
        created_at=datetime(2026, 1, 1, 12, 0, 0),
    )
    assert fb.username == "alice"
    assert fb.email == "a@example.com"
    assert fb.image_path == "/uploads/feedback_images/a.jpg"