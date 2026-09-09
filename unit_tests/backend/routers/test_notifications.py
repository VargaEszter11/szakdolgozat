from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from database import get_db
from routers import notifications
from utils.auth_deps import get_current_user
from .conftest import install_auth_override


app = FastAPI()
app.include_router(notifications.router, prefix="/api")


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_mock():
    return MagicMock()


@pytest.fixture(autouse=True)
def _override_db(db_mock):
    def _get_db():
        yield db_mock

    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)


def _no_items():
    """Patch every crud call the endpoint makes to return an empty result."""
    return patch.multiple(
        "routers.notifications.crud",
        list_trip_share_invitations_for_user=MagicMock(return_value=[]),
        list_trip_share_invitations_from_user=MagicMock(return_value=[]),
        list_feedbacks_for_user=MagicMock(return_value=[]),
        get_user_planned_trips=MagicMock(return_value=[]),
    )


def test_list_notifications_requires_auth(client):
    res = client.get("/api/notifications")
    assert res.status_code == 401


def test_list_notifications_empty(client, auth_headers):
    install_auth_override(app)
    with _no_items():
        res = client.get("/api/notifications", headers=auth_headers)

    assert res.status_code == 200
    assert res.json() == {"items": []}


def test_share_pending_item(client, auth_headers, auth_user):
    install_auth_override(app, auth_user)
    invitation = SimpleNamespace(
        id=11,
        source_trip_id=5,
        from_user_id=2,
        created_at=datetime(2026, 1, 1, 10, 0, 0),
    )
    trip = SimpleNamespace(id=5, title="Paris Weekend")
    from_user = SimpleNamespace(id=2, username="alice")

    with patch.multiple(
        "routers.notifications.crud",
        list_trip_share_invitations_for_user=MagicMock(return_value=[invitation]),
        list_trip_share_invitations_from_user=MagicMock(return_value=[]),
        list_feedbacks_for_user=MagicMock(return_value=[]),
        get_user_planned_trips=MagicMock(return_value=[]),
        get_planned_trip=MagicMock(return_value=trip),
        get_user=MagicMock(return_value=from_user),
    ):
        res = client.get("/api/notifications", headers=auth_headers)

    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    item = items[0]
    assert item["id"] == "share:11"
    assert item["type"] == "share_pending"
    assert item["title"] == "Shared trip invitation"
    assert item["body"] == "alice shared “Paris Weekend” with you."
    assert item["href"] == "/trips"
    assert item["meta"] == {
        "invitation_id": 11,
        "trip_title": "Paris Weekend",
        "from_username": "alice",
    }


def test_share_pending_item_falls_back_when_trip_and_user_missing(client, auth_headers, auth_user):
    install_auth_override(app, auth_user)
    invitation = SimpleNamespace(
        id=12,
        source_trip_id=999,
        from_user_id=42,
        created_at=None,
    )

    with patch.multiple(
        "routers.notifications.crud",
        list_trip_share_invitations_for_user=MagicMock(return_value=[invitation]),
        list_trip_share_invitations_from_user=MagicMock(return_value=[]),
        list_feedbacks_for_user=MagicMock(return_value=[]),
        get_user_planned_trips=MagicMock(return_value=[]),
        get_planned_trip=MagicMock(return_value=None),
        get_user=MagicMock(return_value=None),
    ):
        res = client.get("/api/notifications", headers=auth_headers)

    item = res.json()["items"][0]
    assert item["body"] == "user#42 shared “Trip” with you."
    assert item["meta"]["from_username"] == "user#42"
    assert item["meta"]["trip_title"] == "Trip"
    assert item["created_at"] is None


def test_share_accepted_item_recent_is_included(client, auth_headers, auth_user):
    install_auth_override(app, auth_user)
    recent = datetime.combine(date.today() - timedelta(days=1), datetime.min.time())
    invitation = SimpleNamespace(
        id=21,
        source_trip_id=7,
        to_user_id=3,
        responded_at=recent,
    )
    trip = SimpleNamespace(id=7, title="Rome Trip")
    to_user = SimpleNamespace(id=3, username="bob")

    with patch.multiple(
        "routers.notifications.crud",
        list_trip_share_invitations_for_user=MagicMock(return_value=[]),
        list_trip_share_invitations_from_user=MagicMock(return_value=[invitation]),
        list_feedbacks_for_user=MagicMock(return_value=[]),
        get_user_planned_trips=MagicMock(return_value=[]),
        get_planned_trip=MagicMock(return_value=trip),
        get_user=MagicMock(return_value=to_user),
    ):
        res = client.get("/api/notifications", headers=auth_headers)

    items = res.json()["items"]
    assert len(items) == 1
    item = items[0]
    assert item["id"] == "share_accepted:21"
    assert item["type"] == "share_accepted"
    assert item["body"] == "bob accepted your shared trip “Rome Trip”."
    assert item["meta"] == {
        "invitation_id": 21,
        "trip_title": "Rome Trip",
        "to_username": "bob",
    }


def test_share_accepted_item_older_than_90_days_is_excluded(client, auth_headers, auth_user):
    install_auth_override(app, auth_user)
    stale = datetime.combine(date.today() - timedelta(days=91), datetime.min.time())
    invitation = SimpleNamespace(
        id=22,
        source_trip_id=7,
        to_user_id=3,
        responded_at=stale,
    )

    with patch.multiple(
        "routers.notifications.crud",
        list_trip_share_invitations_for_user=MagicMock(return_value=[]),
        list_trip_share_invitations_from_user=MagicMock(return_value=[invitation]),
        list_feedbacks_for_user=MagicMock(return_value=[]),
        get_user_planned_trips=MagicMock(return_value=[]),
        get_planned_trip=MagicMock(return_value=None),
        get_user=MagicMock(return_value=None),
    ):
        res = client.get("/api/notifications", headers=auth_headers)

    assert res.json()["items"] == []


def test_feedback_solved_only_included_when_solved(client, auth_headers, auth_user):
    install_auth_override(app, auth_user)
    solved = SimpleNamespace(
        id=101,
        solved=True,
        message="  Great app,   thanks!  ",
        created_at=datetime(2026, 2, 1, 8, 0, 0),
    )
    unsolved = SimpleNamespace(
        id=102,
        solved=False,
        message="Still broken",
        created_at=datetime(2026, 2, 2, 8, 0, 0),
    )

    with _no_items():
        with patch(
            "routers.notifications.crud.list_feedbacks_for_user",
            return_value=[solved, unsolved],
        ):
            res = client.get("/api/notifications", headers=auth_headers)

    items = res.json()["items"]
    assert len(items) == 1
    item = items[0]
    assert item["id"] == "feedback_solved:101"
    assert item["type"] == "feedback_solved"
    assert item["body"] == "Great app, thanks!"
    assert item["meta"]["feedback_id"] == 101


def test_trip_completed_filters(client, auth_headers, auth_user):
    install_auth_override(app, auth_user)
    today = date.today()

    booked_recent = SimpleNamespace(
        id=1, title="Berlin", is_booked=True, end_date=today - timedelta(days=5)
    )
    not_booked = SimpleNamespace(
        id=2, title="Vienna", is_booked=False, end_date=today - timedelta(days=5)
    )
    no_end_date = SimpleNamespace(
        id=3, title="Prague", is_booked=True, end_date=None
    )
    still_upcoming = SimpleNamespace(
        id=4, title="Oslo", is_booked=True, end_date=today + timedelta(days=5)
    )
    too_old = SimpleNamespace(
        id=5, title="Madrid", is_booked=True, end_date=today - timedelta(days=91)
    )

    with patch.multiple(
        "routers.notifications.crud",
        list_trip_share_invitations_for_user=MagicMock(return_value=[]),
        list_trip_share_invitations_from_user=MagicMock(return_value=[]),
        list_feedbacks_for_user=MagicMock(return_value=[]),
        get_user_planned_trips=MagicMock(
            return_value=[booked_recent, not_booked, no_end_date, still_upcoming, too_old]
        ),
    ):
        res = client.get("/api/notifications", headers=auth_headers)

    items = res.json()["items"]
    assert len(items) == 1
    item = items[0]
    assert item["id"] == "trip_completed:1"
    assert item["type"] == "trip_completed"
    assert item["meta"]["trip_id"] == 1
    assert item["meta"]["trip_title"] == "Berlin"
    assert item["meta"]["end_date"] == (today - timedelta(days=5)).isoformat()


def test_items_are_sorted_newest_first_and_missing_dates_last(client, auth_headers, auth_user):
    install_auth_override(app, auth_user)

    old_invitation = SimpleNamespace(
        id=1,
        source_trip_id=1,
        from_user_id=1,
        created_at=datetime(2020, 1, 1),
    )
    new_invitation = SimpleNamespace(
        id=2,
        source_trip_id=1,
        from_user_id=1,
        created_at=datetime(2026, 1, 1),
    )
    undated_feedback = SimpleNamespace(
        id=1, solved=True, message="hi", created_at=None
    )

    with patch.multiple(
        "routers.notifications.crud",
        list_trip_share_invitations_for_user=MagicMock(
            return_value=[old_invitation, new_invitation]
        ),
        list_trip_share_invitations_from_user=MagicMock(return_value=[]),
        list_feedbacks_for_user=MagicMock(return_value=[undated_feedback]),
        get_user_planned_trips=MagicMock(return_value=[]),
        get_planned_trip=MagicMock(return_value=None),
        get_user=MagicMock(return_value=None),
    ):
        res = client.get("/api/notifications", headers=auth_headers)

    items = res.json()["items"]
    assert [item["id"] for item in items] == ["share:2", "share:1", "feedback_solved:1"]


def test_iso_dt_helper():
    assert notifications._iso_dt(None) is None
    dt = datetime(2026, 3, 4, 5, 6, 7)
    assert notifications._iso_dt(dt) is dt
    assert notifications._iso_dt(date(2026, 3, 4)) == datetime(2026, 3, 4, 0, 0, 0)
    assert notifications._iso_dt("not-a-date") is None


def test_preview_helper_truncates_long_text():
    short = "  Hello   world  "
    assert notifications._preview(short) == "Hello world"

    long_text = "x" * 200
    result = notifications._preview(long_text, limit=120)
    assert len(result) == 120
    assert result.endswith("…")
    assert result[:-1] == "x" * 119
