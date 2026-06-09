import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock

from routers import trip_stops

app = FastAPI()
app.include_router(trip_stops.router)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_mock():
    return MagicMock()


def override_get_db(db_mock):
    def _override():
        yield db_mock
    return _override


def trip_stop_response(**overrides):
    data = {
        "id": 1,
        "trip_id": 1,
        "place_name": "Paris",
        "country": "FR",
        "stop_order": None,
        "arrival_date": None,
        "departure_date": None,
        "transport_from_last": None,
        "activities": None,
        "estimated_price": None,
        "latitude": None,
        "longitude": None,
        "booking_url": None,
        "flight_availability_verified": None,
    }
    data.update(overrides)
    return data


def test_create_trip_stop_trip_not_found(monkeypatch, client, db_mock):
    monkeypatch.setattr(trip_stops.crud, "get_planned_trip", lambda db, trip_id: None)

    app.dependency_overrides[trip_stops.get_db] = override_get_db(db_mock)

    res = client.post("/trip-stops", json={
        "trip_id": 1,
        "place_name": "Paris",
        "country": "FR"
    })

    assert res.status_code == 404


def test_create_trip_stop_geocode_success(monkeypatch, client, db_mock):
    monkeypatch.setattr(trip_stops.crud, "get_planned_trip", lambda db, trip_id: True)
    monkeypatch.setattr(trip_stops.crud, "create_trip_stop", lambda db, stop: trip_stop_response())

    async def fake_geocode(place):
        return (48.8, 2.3)

    monkeypatch.setattr(trip_stops, "geocode_place", AsyncMock(side_effect=fake_geocode))

    app.dependency_overrides[trip_stops.get_db] = override_get_db(db_mock)

    res = client.post("/trip-stops", json={
        "trip_id": 1,
        "place_name": "Paris",
        "country": "FR"
    })

    assert res.status_code in (200, 201)


def test_create_trip_stop_geocode_fail(monkeypatch, client, db_mock):
    monkeypatch.setattr(trip_stops.crud, "get_planned_trip", lambda db, trip_id: True)
    monkeypatch.setattr(trip_stops.crud, "create_trip_stop", lambda db, stop: trip_stop_response())

    async def fail_geocode(place):
        raise Exception("geocode failed")

    monkeypatch.setattr(trip_stops, "geocode_place", AsyncMock(side_effect=fail_geocode))

    app.dependency_overrides[trip_stops.get_db] = override_get_db(db_mock)

    res = client.post("/trip-stops", json={
        "trip_id": 1,
        "place_name": "Paris",
        "country": "FR"
    })

    assert res.status_code in (200, 201)

def test_get_trip_stop_not_found(monkeypatch, client, db_mock):
    monkeypatch.setattr(trip_stops.crud, "get_trip_stop", lambda db, stop_id: None)

    app.dependency_overrides[trip_stops.get_db] = override_get_db(db_mock)

    res = client.get("/trip-stops/1")

    assert res.status_code == 404


def test_get_trip_stop_success(monkeypatch, client, db_mock):
    monkeypatch.setattr(trip_stops.crud, "get_trip_stop", lambda db, stop_id: trip_stop_response())

    app.dependency_overrides[trip_stops.get_db] = override_get_db(db_mock)

    res = client.get("/trip-stops/1")

    assert res.status_code == 200

def test_get_trip_stops_trip_not_found(monkeypatch, client, db_mock):
    monkeypatch.setattr(trip_stops.crud, "get_planned_trip", lambda db, trip_id: None)

    app.dependency_overrides[trip_stops.get_db] = override_get_db(db_mock)

    res = client.get("/trips/1/stops")

    assert res.status_code == 404


def test_get_trip_stops_success(monkeypatch, client, db_mock):
    monkeypatch.setattr(trip_stops.crud, "get_planned_trip", lambda db, trip_id: True)
    monkeypatch.setattr(trip_stops.crud, "get_trip_stops", lambda db, trip_id: [])

    app.dependency_overrides[trip_stops.get_db] = override_get_db(db_mock)

    res = client.get("/trips/1/stops")

    assert res.status_code == 200

def test_update_trip_stop_not_found(monkeypatch, client, db_mock):
    monkeypatch.setattr(trip_stops.crud, "update_trip_stop", lambda db, stop_id, stop_update: None)

    app.dependency_overrides[trip_stops.get_db] = override_get_db(db_mock)

    res = client.put("/trip-stops/1", json={
        "place_name": "Updated"
    })

    assert res.status_code == 404


def test_update_trip_stop_success(monkeypatch, client, db_mock):
    monkeypatch.setattr(trip_stops.crud, "update_trip_stop", lambda db, stop_id, stop_update: trip_stop_response(place_name="Updated"))

    app.dependency_overrides[trip_stops.get_db] = override_get_db(db_mock)

    res = client.put("/trip-stops/1", json={
        "place_name": "Updated"
    })

    assert res.status_code == 200

def test_delete_trip_stop_success(monkeypatch, client, db_mock):
    monkeypatch.setattr(trip_stops.crud, "delete_trip_stop", lambda db, stop_id: True)

    app.dependency_overrides[trip_stops.get_db] = override_get_db(db_mock)

    res = client.delete("/trip-stops/1")

    assert res.status_code == 204


def test_delete_trip_stop_not_found(monkeypatch, client, db_mock):
    monkeypatch.setattr(trip_stops.crud, "delete_trip_stop", lambda db, stop_id: False)

    app.dependency_overrides[trip_stops.get_db] = override_get_db(db_mock)

    res = client.delete("/trip-stops/1")

    assert res.status_code == 404