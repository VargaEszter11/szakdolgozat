import pytest
from datetime import date, datetime
from decimal import Decimal
from fastapi import FastAPI
from fastapi.testclient import TestClient
from types import SimpleNamespace
from unittest.mock import MagicMock

from routers import trip_sharing
from utils.auth_deps import get_current_user

from .auth_test_utils import fake_user, override_current_user

app = FastAPI()
app.include_router(trip_sharing.router, prefix="/api")


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def db_mock():
    return MagicMock()


def override_get_db(db_mock):
    def _override():
        yield db_mock
    return _override


def sample_trip(**overrides):
    data = {
        "id": 1,
        "user_id": 10,
        "title": "Europe Trip",
        "start_date": date(2026, 7, 1),
        "end_date": date(2026, 7, 14),
        "start_city": "Budapest",
        "people": 2,
        "is_booked": False,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def sample_stop():
    return SimpleNamespace(
        id=1,
        trip_id=1,
        place_name="Prague",
        country="Czechia",
        stop_order=1,
        arrival_date=date(2026, 7, 2),
        departure_date=date(2026, 7, 4),
        transport_from_last="train",
        activities="Old town",
        estimated_price=Decimal("100.00"),
        latitude=50.08,
        longitude=14.43,
        booking_url=None,
        flight_availability_verified=None,
    )


def sample_link(**overrides):
    data = {
        "id": 1,
        "trip_id": 1,
        "created_by_user_id": 10,
        "share_token": "abc123token",
        "is_active": True,
        "created_at": datetime(2026, 1, 1, 12, 0, 0),
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def sample_invitation(**overrides):
    data = {
        "id": 5,
        "source_trip_id": 1,
        "from_user_id": 10,
        "to_user_id": 20,
        "status": "pending",
        "created_at": datetime(2026, 1, 1, 12, 0, 0),
        "responded_at": None,
        "result_trip_id": None,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_create_share_link_not_owner(monkeypatch, client, db_mock):
    override_current_user(app, fake_user(99))
    monkeypatch.setattr(
        trip_sharing.crud,
        "create_or_get_trip_share_link",
        MagicMock(side_effect=ValueError("not_owner")),
    )
    app.dependency_overrides[trip_sharing.get_db] = override_get_db(db_mock)

    res = client.post("/api/planned-trips/1/share-link", json={})

    assert res.status_code == 403


def test_create_share_link_success(monkeypatch, client, db_mock):
    override_current_user(app, fake_user(10))
    monkeypatch.setattr(
        trip_sharing.crud,
        "create_or_get_trip_share_link",
        lambda db, trip_id, user_id: sample_link(),
    )
    app.dependency_overrides[trip_sharing.get_db] = override_get_db(db_mock)

    res = client.post("/api/planned-trips/1/share-link", json={})

    assert res.status_code == 200
    body = res.json()
    assert body["share_token"] == "abc123token"
    assert "shared_trip.html?token=" in body["share_url"] or "/share?token=" in body["share_url"]


def test_get_shared_trip_public(monkeypatch, client, db_mock):
    trip = sample_trip()
    monkeypatch.setattr(
        trip_sharing.crud,
        "get_active_share_link_by_token",
        lambda db, token: sample_link(),
    )
    monkeypatch.setattr(trip_sharing.crud, "get_planned_trip", lambda db, trip_id: trip)
    monkeypatch.setattr(trip_sharing.crud, "get_trip_stops", lambda db, trip_id: [sample_stop()])
    app.dependency_overrides[trip_sharing.get_db] = override_get_db(db_mock)

    res = client.get("/api/shared-trips/abc123token")

    assert res.status_code == 200
    body = res.json()
    assert body["title"] == "Europe Trip"
    assert len(body["stops"]) == 1
    assert "user_id" not in body


def test_get_shared_trip_invalid_token(monkeypatch, client, db_mock):
    monkeypatch.setattr(
        trip_sharing.crud,
        "get_active_share_link_by_token",
        lambda db, token: None,
    )
    app.dependency_overrides[trip_sharing.get_db] = override_get_db(db_mock)

    res = client.get("/api/shared-trips/bad-token")

    assert res.status_code == 404


def test_share_with_user_success(monkeypatch, client, db_mock):
    override_current_user(app, fake_user(10))
    inv = sample_invitation()
    monkeypatch.setattr(
        trip_sharing.crud,
        "create_trip_share_invitation",
        lambda db, trip_id, from_user_id, to_user_id: inv,
    )
    monkeypatch.setattr(
        trip_sharing.crud,
        "get_user",
        lambda db, user_id: SimpleNamespace(id=user_id, username="sender" if user_id == 10 else "recipient"),
    )
    monkeypatch.setattr(
        trip_sharing.crud,
        "get_planned_trip",
        lambda db, trip_id: sample_trip(),
    )
    app.dependency_overrides[trip_sharing.get_db] = override_get_db(db_mock)

    res = client.post(
        "/api/planned-trips/1/share",
        json={"to_user_id": 20},
    )

    assert res.status_code == 201
    assert res.json()["status"] == "pending"


def test_share_with_self_rejected(monkeypatch, client, db_mock):
    override_current_user(app, fake_user(10))
    monkeypatch.setattr(
        trip_sharing.crud,
        "create_trip_share_invitation",
        MagicMock(side_effect=ValueError("cannot_share_with_self")),
    )
    app.dependency_overrides[trip_sharing.get_db] = override_get_db(db_mock)

    res = client.post(
        "/api/planned-trips/1/share",
        json={"to_user_id": 10},
    )

    assert res.status_code == 400


def test_list_invitations(monkeypatch, client, db_mock):
    override_current_user(app, fake_user(20))
    inv = sample_invitation()
    monkeypatch.setattr(
        trip_sharing.crud,
        "list_trip_share_invitations_for_user",
        lambda db, user_id, status: [inv],
    )
    monkeypatch.setattr(
        trip_sharing.crud,
        "get_planned_trip",
        lambda db, trip_id: sample_trip(),
    )
    monkeypatch.setattr(
        trip_sharing.crud,
        "get_user",
        lambda db, user_id: SimpleNamespace(id=user_id, username="alice"),
    )
    app.dependency_overrides[trip_sharing.get_db] = override_get_db(db_mock)

    res = client.get("/api/users/20/trip-share-invitations")

    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    assert body[0]["from_username"] == "alice"


def test_accept_invitation(monkeypatch, client, db_mock):
    override_current_user(app, fake_user(20))
    inv = sample_invitation(status="accepted", result_trip_id=99)
    monkeypatch.setattr(
        trip_sharing.crud,
        "accept_trip_share_invitation",
        lambda db, invitation_id, user_id: inv,
    )
    monkeypatch.setattr(
        trip_sharing.crud,
        "get_user",
        lambda db, user_id: SimpleNamespace(id=user_id, username="alice"),
    )
    monkeypatch.setattr(
        trip_sharing.crud,
        "get_planned_trip",
        lambda db, trip_id: sample_trip(),
    )
    app.dependency_overrides[trip_sharing.get_db] = override_get_db(db_mock)

    res = client.post("/api/trip-share-invitations/5/accept", json={})

    assert res.status_code == 200
    assert res.json()["status"] == "accepted"
    assert res.json()["result_trip_id"] == 99


def test_decline_invitation(monkeypatch, client, db_mock):
    override_current_user(app, fake_user(20))
    inv = sample_invitation(status="declined")
    monkeypatch.setattr(
        trip_sharing.crud,
        "decline_trip_share_invitation",
        lambda db, invitation_id, user_id: inv,
    )
    monkeypatch.setattr(
        trip_sharing.crud,
        "get_user",
        lambda db, user_id: SimpleNamespace(id=user_id, username="alice"),
    )
    monkeypatch.setattr(
        trip_sharing.crud,
        "get_planned_trip",
        lambda db, trip_id: sample_trip(),
    )
    app.dependency_overrides[trip_sharing.get_db] = override_get_db(db_mock)

    res = client.post("/api/trip-share-invitations/5/decline", json={})

    assert res.status_code == 200
    assert res.json()["status"] == "declined"
