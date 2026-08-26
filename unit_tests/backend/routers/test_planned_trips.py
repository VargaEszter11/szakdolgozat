import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from datetime import date
from types import SimpleNamespace

from routers import planned_trips
from utils.auth_deps import get_current_user

app = FastAPI()
app.include_router(planned_trips.router, prefix="/api")


@pytest.fixture
def client(auth_user):
    app.dependency_overrides[get_current_user] = lambda: auth_user
    yield TestClient(app)
    app.dependency_overrides.pop(get_current_user, None)


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
        "start_latitude": None,
        "start_longitude": None,
        "people": 1,
        "is_booked": False,
        "stops": [],
    }
    data.update(overrides)
    return data


def mock_trip(**overrides):
    data = trip_response(
        is_booked=True,
        end_date=date(2020, 1, 1),
        start_city="Home",
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def test_create_trip_unauthorized(db_mock):
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides[planned_trips.get_db] = override_get_db(db_mock)
    bare = TestClient(app)
    res = bare.post(
        "/api/planned-trips",
        json={"user_id": 1, "title": "Trip", "people": 1, "is_booked": False},
    )
    assert res.status_code == 401


def test_create_trip_success(monkeypatch, client, db_mock):
    async def fake_geocode(_city):
        return 47.5, 19.0

    monkeypatch.setattr(planned_trips, "geocode_place", fake_geocode)
    monkeypatch.setattr(planned_trips.crud, "create_planned_trip", lambda db, trip: trip_response())
    app.dependency_overrides[planned_trips.get_db] = override_get_db(db_mock)

    res = client.post(
        "/api/planned-trips",
        json={"user_id": 1, "title": "Trip", "people": 1, "is_booked": False},
    )
    assert res.status_code in (200, 201)


def test_create_trip_with_start_city(monkeypatch, client, db_mock):
    captured = {}

    async def fake_geocode(city):
        captured["city"] = city
        return 48.1, 20.78

    def fake_create(db, trip):
        dumped = trip.model_dump() if hasattr(trip, "model_dump") else dict(trip)
        captured["created"] = dumped
        return trip_response(
            start_city=dumped.get("start_city"),
            start_latitude=dumped.get("start_latitude"),
            start_longitude=dumped.get("start_longitude"),
        )

    monkeypatch.setattr(planned_trips, "geocode_place", fake_geocode)
    monkeypatch.setattr(planned_trips.crud, "create_planned_trip", fake_create)
    app.dependency_overrides[planned_trips.get_db] = override_get_db(db_mock)

    res = client.post(
        "/api/planned-trips",
        json={
            "user_id": 1,
            "title": "Trip",
            "people": 1,
            "is_booked": False,
            "start_city": "Miskolc",
        },
    )
    assert res.status_code in (200, 201)
    body = res.json()
    assert body.get("start_city") == "Miskolc"
    assert captured.get("city") == "Miskolc"
    assert captured["created"]["start_latitude"] == 48.1
    assert captured["created"]["start_longitude"] == 20.78
    assert body.get("start_latitude") == 48.1
    assert body.get("start_longitude") == 20.78


def test_update_trip_regeocodes_start_city(monkeypatch, client, db_mock):
    captured = {}

    async def fake_geocode(city):
        captured["city"] = city
        return 47.49, 19.04

    def fake_update(db, trip_id, trip_update):
        dumped = trip_update.model_dump(exclude_unset=True)
        captured["update"] = dumped
        return mock_trip(
            start_city=dumped.get("start_city"),
            start_latitude=dumped.get("start_latitude"),
            start_longitude=dumped.get("start_longitude"),
        )

    monkeypatch.setattr(planned_trips, "geocode_place", fake_geocode)
    monkeypatch.setattr(planned_trips.crud, "get_planned_trip", lambda db, trip_id: mock_trip())
    monkeypatch.setattr(planned_trips.crud, "update_planned_trip", fake_update)
    monkeypatch.setattr(planned_trips.crud, "sync_completed_booked_trip_to_visited", lambda *a, **k: None)
    app.dependency_overrides[planned_trips.get_db] = override_get_db(db_mock)

    res = client.put("/api/planned-trips/1", json={"start_city": "Budapest"})
    assert res.status_code == 200
    assert captured.get("city") == "Budapest"
    assert captured["update"]["start_latitude"] == 47.49
    assert res.json().get("start_longitude") == 19.04


def test_get_trip_not_found(monkeypatch, client, db_mock):
    monkeypatch.setattr(planned_trips.crud, "get_planned_trip", lambda db, trip_id: None)
    app.dependency_overrides[planned_trips.get_db] = override_get_db(db_mock)
    res = client.get("/api/planned-trips/1")
    assert res.status_code == 404


def test_get_trip_success(monkeypatch, client, db_mock):
    monkeypatch.setattr(planned_trips.crud, "get_planned_trip", lambda db, trip_id: mock_trip())
    monkeypatch.setattr(planned_trips.crud, "sync_completed_booked_trip_to_visited", lambda *a, **k: None)
    app.dependency_overrides[planned_trips.get_db] = override_get_db(db_mock)
    res = client.get("/api/planned-trips/1")
    assert res.status_code == 200


def test_list_trips(monkeypatch, client, db_mock):
    monkeypatch.setattr(planned_trips.crud, "get_user_planned_trips", lambda db, user_id: [])
    monkeypatch.setattr(planned_trips.crud, "sync_completed_booked_trips_to_visited", lambda *a, **k: None)
    app.dependency_overrides[planned_trips.get_db] = override_get_db(db_mock)
    res = client.get("/api/planned-trips")
    assert res.status_code == 200


def test_update_trip_not_found(monkeypatch, client, db_mock):
    monkeypatch.setattr(planned_trips.crud, "get_planned_trip", lambda db, trip_id: None)
    app.dependency_overrides[planned_trips.get_db] = override_get_db(db_mock)
    res = client.put("/api/planned-trips/1", json={"title": "New"})
    assert res.status_code == 404


def test_update_trip_success(monkeypatch, client, db_mock):
    monkeypatch.setattr(planned_trips.crud, "get_planned_trip", lambda db, trip_id: mock_trip())
    monkeypatch.setattr(planned_trips.crud, "update_planned_trip", lambda db, trip_id, trip_update: mock_trip())
    monkeypatch.setattr(planned_trips.crud, "sync_completed_booked_trip_to_visited", lambda *a, **k: None)
    app.dependency_overrides[planned_trips.get_db] = override_get_db(db_mock)
    res = client.put("/api/planned-trips/1", json={"title": "New"})
    assert res.status_code == 200


def test_delete_trip_success(monkeypatch, client, db_mock):
    monkeypatch.setattr(planned_trips.crud, "get_planned_trip", lambda db, trip_id: mock_trip())
    monkeypatch.setattr(planned_trips.crud, "delete_planned_trip", lambda db, trip_id: True)
    app.dependency_overrides[planned_trips.get_db] = override_get_db(db_mock)
    res = client.delete("/api/planned-trips/1")
    assert res.status_code == 204


def test_delete_trip_not_found(monkeypatch, client, db_mock):
    monkeypatch.setattr(planned_trips.crud, "get_planned_trip", lambda db, trip_id: None)
    app.dependency_overrides[planned_trips.get_db] = override_get_db(db_mock)
    res = client.delete("/api/planned-trips/1")
    assert res.status_code == 404
