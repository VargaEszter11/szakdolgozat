from datetime import date

import pytest

from backend.travel_types.booking import (
    _people_count,
    _skyscanner_date,
    booking_url,
    clear_booking_details,
    flight_booking_details,
    route_operates_on_date,
    seasonality_status,
)


def test_seasonality_status_true():
    assert seasonality_status(True) == "seasonal"


def test_seasonality_status_false():
    assert seasonality_status(False) == "year_round"


def test_seasonality_status_none():
    assert seasonality_status(None) == "unknown"


def test_people_count_returns_value():
    assert _people_count(3) == 3


def test_people_count_defaults_to_one():
    assert _people_count(None) == 1


def test_people_count_never_returns_less_than_one():
    assert _people_count(0) == 1
    assert _people_count(-5) == 1


def test_skyscanner_date():
    assert _skyscanner_date("2026-08-15") == "260815"


def test_skyscanner_date_invalid():
    assert _skyscanner_date("not-a-date") is None


def test_booking_url_generates_skyscanner_link():
    url = booking_url(
        airline_iata="FR",
        origin="bud",
        destination="fco",
        departure_date="2026-08-15",
        people=2,
    )

    assert url is not None
    assert "bud/fco/260815" in url
    assert "adultsv2=2" in url


def test_booking_url_returns_none_for_invalid_date():
    assert (
        booking_url(
            airline_iata="FR",
            origin="BUD",
            destination="FCO",
            departure_date="bad-date",
        )
        is None
    )


class Route:
    effective_from = None
    effective_to = None
    operating_days = []


def test_route_operates_on_date_with_no_operating_days():
    route = Route()

    assert route_operates_on_date(route, "2026-08-15") is True


def test_route_operates_on_date_invalid_date():
    route = Route()

    assert route_operates_on_date(route, "invalid-date") is False


def test_route_operates_on_date_before_effective_from():
    route = Route()
    route.effective_from = date(2026, 8, 1)

    assert route_operates_on_date(route, "2026-07-31") is False


def test_route_operates_on_date_after_effective_to():
    route = Route()
    route.effective_to = date(2026, 8, 31)

    assert route_operates_on_date(route, "2026-09-01") is False


def test_clear_booking_details():
    stop = {
        "origin_airport_iata": "BUD",
        "destination_airport_iata": "FCO",
        "airline_iata": "FR",
        "airline_name": "Ryanair",
        "booking_url": "https://example.com",
        "flight_availability_verified": True,
        "city": "Rome",
    }

    clear_booking_details(stop)

    assert "origin_airport_iata" not in stop
    assert "destination_airport_iata" not in stop
    assert "airline_iata" not in stop
    assert "airline_name" not in stop
    assert "booking_url" not in stop
    assert "flight_availability_verified" not in stop

    assert stop["city"] == "Rome"


def test_flight_booking_details(monkeypatch):
    class FakeRoute:
        origin_iata = "BUD"
        destination_iata = "FCO"
        airline_iata = "FR"
        airline_name = "Ryanair"
        is_seasonal = False
        effective_from = None
        effective_to = None
        operating_days = []

    monkeypatch.setattr(
        "backend.travel_types.booking.direct_route_for_leg",
        lambda *args, **kwargs: FakeRoute(),
    )

    result = flight_booking_details(
        db=None,
        origin="BUD",
        destination="FCO",
        departure_date="2026-08-15",
    )

    assert result["origin_airport_iata"] == "BUD"
    assert result["destination_airport_iata"] == "FCO"
    assert result["airline_iata"] == "FR"
    assert result["airline_name"] == "Ryanair"
    assert result["seasonality_status"] == "year_round"
    assert result["flight_availability_verified"] is False
    assert "booking_url" in result


def test_flight_booking_details_returns_empty_dict_when_route_not_available(monkeypatch):
    monkeypatch.setattr(
        "backend.travel_types.booking.direct_route_for_leg",
        lambda *args, **kwargs: None,
    )

    result = flight_booking_details(
        db=None,
        origin="BUD",
        destination="FCO",
        departure_date="2026-08-15",
    )

    assert result == {}