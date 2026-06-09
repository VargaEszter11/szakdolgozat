import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock
from datetime import date
from types import SimpleNamespace

from database import schemas
from routers import planned_trips

app = FastAPI()
app.include_router(planned_trips.router, prefix="/api")


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

def trip_response(**overrides):
    data = {
        "id": 1,
        "user_id": 1,
        "title": "Trip",
        "start_date": None,
        "end_date": None,
        "start_city": None,
        "people": 1,
        "is_booked": False,
        "stops": [],
    }
    data.update(overrides)
    return data


def mock_trip():
    return SimpleNamespace(
        **trip_response(
            is_booked=True,
            end_date=date(2020, 1, 1),
            start_city="Home",
        )
    )

def test_create_trip_user_not_found(monkeypatch, client, db_mock):
    monkeypatch.setattr(planned_trips.crud, "get_user", lambda db, user_id: None)

    app.dependency_overrides[planned_trips.get_db] = override_get_db(db_mock)

    res = client.post("/api/planned-trips", json={
        "user_id": 1,
        "title": "Trip",
        "people": 1,
        "is_booked": False
    })

    assert res.status_code == 404


def test_create_trip_success(monkeypatch, client, db_mock):
    monkeypatch.setattr(planned_trips.crud, "get_user", lambda db, user_id: True)
    monkeypatch.setattr(planned_trips.crud, "create_planned_trip", lambda db, trip: trip_response())

    app.dependency_overrides[planned_trips.get_db] = override_get_db(db_mock)

    res = client.post("/api/planned-trips", json={
        "user_id": 1,
        "title": "Trip",
        "people": 1,
        "is_booked": False
    })

    assert res.status_code in (200, 201)


def test_create_trip_geocode_success(monkeypatch, client, db_mock):
    monkeypatch.setattr(planned_trips.crud, "get_user", lambda db, user_id: True)
    monkeypatch.setattr(planned_trips.crud, "create_planned_trip", lambda db, trip: trip_response(start_city="Miskolc"))

    async def fake_geocode(place):
        return (47.0, 19.0)

    monkeypatch.setattr(planned_trips, "geocode_place", AsyncMock(side_effect=fake_geocode))

    app.dependency_overrides[planned_trips.get_db] = override_get_db(db_mock)

    res = client.post("/api/planned-trips", json={
        "user_id": 1,
        "title": "Trip",
        "people": 1,
        "is_booked": False,
        "start_city": "Miskolc"
    })

    assert res.status_code in (200, 201)


def test_create_trip_geocode_fails(monkeypatch, client, db_mock):
    monkeypatch.setattr(planned_trips.crud, "get_user", lambda db, user_id: True)
    monkeypatch.setattr(planned_trips.crud, "create_planned_trip", lambda db, trip: trip_response(start_city="Miskolc"))

    async def fail_geocode(place):
        raise Exception("fail")

    monkeypatch.setattr(planned_trips, "geocode_place", AsyncMock(side_effect=fail_geocode))

    app.dependency_overrides[planned_trips.get_db] = override_get_db(db_mock)

    res = client.post("/api/planned-trips", json={
        "user_id": 1,
        "title": "Trip",
        "people": 1,
        "is_booked": False,
        "start_city": "Miskolc"
    })

    assert res.status_code in (200, 201)

def test_get_trip_not_found(monkeypatch, client, db_mock):
    monkeypatch.setattr(planned_trips.crud, "get_planned_trip", lambda db, trip_id: None)

    app.dependency_overrides[planned_trips.get_db] = override_get_db(db_mock)

    res = client.get("/api/planned-trips/1")

    assert res.status_code == 404


def test_get_trip_success(monkeypatch, client, db_mock):
    monkeypatch.setattr(planned_trips.crud, "get_planned_trip", lambda db, trip_id: mock_trip())

    app.dependency_overrides[planned_trips.get_db] = override_get_db(db_mock)

    res = client.get("/api/planned-trips/1")

    assert res.status_code == 200

def test_list_trips_all(monkeypatch, client, db_mock):
    monkeypatch.setattr(planned_trips.crud, "get_planned_trips", lambda db, skip=0, limit=100: [])

    app.dependency_overrides[planned_trips.get_db] = override_get_db(db_mock)

    res = client.get("/api/planned-trips")

    assert res.status_code == 200


def test_list_trips_by_user(monkeypatch, client, db_mock):
    monkeypatch.setattr(planned_trips.crud, "get_user", lambda db, user_id: True)
    monkeypatch.setattr(planned_trips.crud, "get_user_planned_trips", lambda db, user_id: [])

    app.dependency_overrides[planned_trips.get_db] = override_get_db(db_mock)

    res = client.get("/api/planned-trips?user_id=1")

    assert res.status_code == 200


def test_list_trips_user_not_found(monkeypatch, client, db_mock):
    monkeypatch.setattr(planned_trips.crud, "get_user", lambda db, user_id: None)

    app.dependency_overrides[planned_trips.get_db] = override_get_db(db_mock)

    res = client.get("/api/planned-trips?user_id=1")

    assert res.status_code == 404

def test_update_trip_not_found(monkeypatch, client, db_mock):
    monkeypatch.setattr(planned_trips.crud, "update_planned_trip", lambda db, trip_id, trip_update: None)

    app.dependency_overrides[planned_trips.get_db] = override_get_db(db_mock)

    res = client.put("/api/planned-trips/1", json={"title": "New"})

    assert res.status_code == 404


def test_update_trip_success(monkeypatch, client, db_mock):
    monkeypatch.setattr(planned_trips.crud, "update_planned_trip", lambda db, trip_id, trip_update: mock_trip())

    app.dependency_overrides[planned_trips.get_db] = override_get_db(db_mock)

    res = client.put("/api/planned-trips/1", json={"title": "New"})

    assert res.status_code == 200

def test_delete_trip_success(monkeypatch, client, db_mock):
    monkeypatch.setattr(planned_trips.crud, "delete_planned_trip", lambda db, trip_id: True)

    app.dependency_overrides[planned_trips.get_db] = override_get_db(db_mock)

    res = client.delete("/api/planned-trips/1")

    assert res.status_code == 204


def test_delete_trip_not_found(monkeypatch, client, db_mock):
    monkeypatch.setattr(planned_trips.crud, "delete_planned_trip", lambda db, trip_id: False)

    app.dependency_overrides[planned_trips.get_db] = override_get_db(db_mock)

    res = client.delete("/api/planned-trips/1")

    assert res.status_code == 404