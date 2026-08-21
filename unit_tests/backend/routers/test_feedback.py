from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from database import get_db
from routers import feedback, admin
from utils.auth_deps import get_current_user
from .conftest import install_auth_override


app = FastAPI()
app.include_router(feedback.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


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


def test_submit_feedback_requires_auth(client):
    res = client.post("/api/feedback", data={"message": "Hello"})
    assert res.status_code == 401


def test_submit_feedback_empty_after_strip(client, auth_headers):
    install_auth_override(app)
    res = client.post(
        "/api/feedback",
        data={"message": "   "},
        headers=auth_headers,
    )
    assert res.status_code == 400
    assert "empty" in res.json()["detail"].lower()


def test_submit_feedback_success(client, auth_headers, auth_user):
    install_auth_override(app, auth_user)
    created = SimpleNamespace(
        id=7,
        user_id=auth_user.id,
        message="Great app",
        image_path=None,
        created_at=datetime(2026, 1, 2, 12, 0, 0),
    )

    with patch("routers.feedback.crud.create_feedback", return_value=created) as create_mock:
        res = client.post(
            "/api/feedback",
            data={"message": "  Great app  "},
            headers=auth_headers,
        )

    assert res.status_code == 201
    body = res.json()
    assert body["id"] == 7
    assert body["user_id"] == auth_user.id
    assert body["username"] == auth_user.username
    assert body["email"] == auth_user.email
    assert body["message"] == "Great app"
    assert body["image_path"] is None
    create_mock.assert_called_once()
    assert create_mock.call_args.kwargs["message"] == "Great app"
    assert create_mock.call_args.kwargs["user_id"] == auth_user.id
    assert create_mock.call_args.kwargs["image_path"] is None


def test_submit_feedback_with_image(client, auth_headers, auth_user, tmp_path, monkeypatch):
    install_auth_override(app, auth_user)
    monkeypatch.setattr(
        "routers.feedback.save_feedback_image",
        lambda content, content_type: "/uploads/feedback_images/abc.jpg",
    )
    created = SimpleNamespace(
        id=8,
        user_id=auth_user.id,
        message="With photo",
        image_path="/uploads/feedback_images/abc.jpg",
        created_at=datetime(2026, 1, 2, 12, 0, 0),
    )

    with patch("routers.feedback.crud.create_feedback", return_value=created) as create_mock:
        res = client.post(
            "/api/feedback",
            data={"message": "With photo"},
            files={"image": ("shot.jpg", b"fake-bytes", "image/jpeg")},
            headers=auth_headers,
        )

    assert res.status_code == 201
    assert res.json()["image_path"] == "/uploads/feedback_images/abc.jpg"
    assert create_mock.call_args.kwargs["image_path"] == "/uploads/feedback_images/abc.jpg"


def test_admin_list_feedback_requires_secret(monkeypatch, client):
    monkeypatch.setenv("ADMIN_SECRET", "secret")
    res = client.get("/api/admin/feedback", headers={"X-Admin-Secret": "wrong"})
    assert res.status_code == 401


def test_admin_list_feedback_ok(monkeypatch, client):
    monkeypatch.setenv("ADMIN_SECRET", "secret")
    row = SimpleNamespace(
        id=1,
        user_id=3,
        message="Nice",
        image_path="/uploads/feedback_images/x.jpg",
        created_at=datetime(2026, 3, 1, 10, 0, 0),
    )
    user = SimpleNamespace(username="alice", email="a@example.com")

    with patch("routers.admin.crud.list_feedbacks", return_value=[row]), \
         patch("routers.admin.crud.get_user", return_value=user):
        res = client.get(
            "/api/admin/feedback",
            headers={"X-Admin-Secret": "secret"},
        )

    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["id"] == 1
    assert data[0]["username"] == "alice"
    assert data[0]["email"] == "a@example.com"
    assert data[0]["message"] == "Nice"
    assert data[0]["image_path"] == "/uploads/feedback_images/x.jpg"


def test_admin_list_feedback_missing_user_fallback(monkeypatch, client):
    monkeypatch.setenv("ADMIN_SECRET", "secret")
    row = SimpleNamespace(
        id=2,
        user_id=99,
        message="Orphan",
        image_path=None,
        created_at=datetime(2026, 3, 1, 10, 0, 0),
    )

    with patch("routers.admin.crud.list_feedbacks", return_value=[row]), \
         patch("routers.admin.crud.get_user", return_value=None):
        res = client.get(
            "/api/admin/feedback",
            headers={"X-Admin-Secret": "secret"},
        )

    assert res.status_code == 200
    assert res.json()[0]["username"] == "user#99"
    assert res.json()[0]["email"] is None


def test_admin_delete_feedback_not_found(monkeypatch, client):
    monkeypatch.setenv("ADMIN_SECRET", "secret")

    with patch("routers.admin.crud.delete_feedback", return_value=False):
        res = client.delete(
            "/api/admin/feedback/123",
            headers={"X-Admin-Secret": "secret"},
        )

    assert res.status_code == 404


def test_admin_delete_feedback_ok(monkeypatch, client, db_mock):
    monkeypatch.setenv("ADMIN_SECRET", "secret")

    with patch("routers.admin.crud.delete_feedback", return_value=True) as delete_mock:
        res = client.delete(
            "/api/admin/feedback/5",
            headers={"X-Admin-Secret": "secret"},
        )

    assert res.status_code == 200
    assert res.json() == {"success": True}
    delete_mock.assert_called_once_with(db_mock, 5)
