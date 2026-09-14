import pytest
from sqlalchemy.orm import Session
from typing import Any, cast

from backend.utils.nearest_airport import calculate_distance_km, nearest_airport, nearest_airports


class FakeAirport:
    def __init__(
        self,
        name: str = "Budapest Airport",
        iata: str = "BUD",
        icao: str = "LHBP",
        city: str = "Budapest",
        country_code: str = "HU",
        latitude: Any = 47.439,
        longitude: Any = 19.261,
    ):
        self.name = name
        self.iata = iata
        self.icao = icao
        self.city = city
        self.country_code = country_code
        self.latitude = latitude
        self.longitude = longitude


class FakeQuery:
    def __init__(self, airports):
        self.airports = airports

    def join(self, *args, **kwargs):
        return self

    def filter(self, *args, **kwargs):
        return self

    def distinct(self):
        return self

    def all(self):
        return self.airports


class FakeDB:
    def __init__(self, airports):
        self.airports = airports

    def query(self, model):
        return FakeQuery(self.airports)


def fake_session(airports) -> Session:
    return cast(Session, FakeDB(airports))


def test_calculate_distance_km_same_point_is_zero():
    distance = calculate_distance_km(47.4979, 19.0402, 47.4979, 19.0402)

    assert distance == pytest.approx(0)


def test_calculate_distance_km_between_budapest_and_vienna():
    distance = calculate_distance_km(
        47.4979,
        19.0402,
        48.2082,
        16.3738,
    )

    assert distance == pytest.approx(214, abs=5)


def test_nearest_airport_returns_none_without_db():
    result = nearest_airport(47.4979, 19.0402, db=None)

    assert result is None


def test_nearest_airport_returns_none_for_invalid_coordinates():
    db = fake_session([FakeAirport()])

    result = nearest_airport("bad-lat", 19.0402, db=db)

    assert result is None


def test_nearest_airport_returns_none_when_no_airports_exist():
    db = fake_session([])

    result = nearest_airport(47.4979, 19.0402, db=db)

    assert result is None


def test_nearest_airport_returns_closest_airport():
    budapest_airport = FakeAirport(
        name="Budapest Airport",
        iata="BUD",
        icao="LHBP",
        city="Budapest",
        country_code="HU",
        latitude=47.439,
        longitude=19.261,
    )

    vienna_airport = FakeAirport(
        name="Vienna Airport",
        iata="VIE",
        icao="LOWW",
        city="Vienna",
        country_code="AT",
        latitude=48.1103,
        longitude=16.5697,
    )

    db = fake_session([vienna_airport, budapest_airport])

    result = nearest_airport(47.4979, 19.0402, db=db)

    assert result == {
        "name": "Budapest Airport",
        "iata": "BUD",
        "icao": "LHBP",
        "city": "Budapest",
        "country": "HU",
        "distance_km": pytest.approx(18, abs=5),
    }


def test_nearest_airport_skips_airports_with_invalid_coordinates():
    invalid_airport = FakeAirport(
        name="Invalid Airport",
        iata="BAD",
        latitude="invalid",
        longitude=19.0,
    )

    valid_airport = FakeAirport(
        name="Budapest Airport",
        iata="BUD",
        latitude=47.439,
        longitude=19.261,
    )

    db = fake_session([invalid_airport, valid_airport])

    result = nearest_airport(47.4979, 19.0402, db=db)

    assert result is not None
    assert result["iata"] == "BUD"


def test_nearest_airport_returns_none_when_all_airport_coordinates_are_invalid():
    invalid_airport = FakeAirport(
        name="Invalid Airport",
        iata="BAD",
        latitude="invalid",
        longitude=19.0,
    )

    db = fake_session([invalid_airport])

    result = nearest_airport(47.4979, 19.0402, db=db)

    assert result is None


def test_distance_km_limit_does_not_prevent_returning_airport():
    vienna_airport = FakeAirport(
        name="Vienna Airport",
        iata="VIE",
        icao="LOWW",
        city="Vienna",
        country_code="AT",
        latitude=48.1103,
        longitude=16.5697,
    )

    db = fake_session([vienna_airport])

    result = nearest_airport(
        47.4979,
        19.0402,
        db=db,
        distance_km=1,
    )

    assert result is not None
    assert result["iata"] == "VIE"
    assert result["distance_km"] > 1


def test_nearest_airports_returns_closest_first_up_to_limit():
    budapest_airport = FakeAirport(iata="BUD", latitude=47.439, longitude=19.261)
    vienna_airport = FakeAirport(iata="VIE", latitude=48.1103, longitude=16.5697)
    bratislava_airport = FakeAirport(iata="BTS", latitude=48.1702, longitude=17.2127)
    prague_airport = FakeAirport(iata="PRG", latitude=50.1008, longitude=14.26)

    db = fake_session([prague_airport, vienna_airport, bratislava_airport, budapest_airport])

    result = nearest_airports(47.4979, 19.0402, db=db, limit=3)

    assert [r["iata"] for r in result] == ["BUD", "BTS", "VIE"]
    assert result[0]["distance_km"] < result[1]["distance_km"] < result[2]["distance_km"]


def test_nearest_airports_returns_empty_list_without_db():
    assert nearest_airports(47.4979, 19.0402, db=None, limit=3) == []


def test_nearest_airports_returns_fewer_than_limit_when_not_enough_airports():
    db = fake_session([FakeAirport(iata="BUD")])

    result = nearest_airports(47.4979, 19.0402, db=db, limit=3)

    assert len(result) == 1
    assert result[0]["iata"] == "BUD"


def test_nearest_airport_still_returns_single_dict_not_a_list():
    db = fake_session([FakeAirport(iata="BUD")])

    result = nearest_airport(47.4979, 19.0402, db=db)

    assert isinstance(result, dict)
    assert result["iata"] == "BUD"


