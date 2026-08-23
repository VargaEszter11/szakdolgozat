import base64
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from routers import admin

app = FastAPI()
app.include_router(admin.router, prefix="/api")


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


def test_admin_ping_not_configured(monkeypatch, client):
    monkeypatch.delenv("ADMIN_SECRET", raising=False)

    res = client.get("/api/admin/ping", headers={"X-Admin-Secret": "anything"})

    assert res.status_code == 503
    assert "not configured" in res.json()["detail"].lower()


def test_admin_ping_invalid_secret(monkeypatch, client):
    monkeypatch.setenv("ADMIN_SECRET", "correct-secret")

    res = client.get("/api/admin/ping", headers={"X-Admin-Secret": "wrong"})

    assert res.status_code == 401


def test_admin_ping_ok(monkeypatch, client):
    monkeypatch.setenv("ADMIN_SECRET", "correct-secret")

    res = client.get("/api/admin/ping", headers={"X-Admin-Secret": "correct-secret"})

    assert res.status_code == 200
    assert res.json() == {"ok": True}


def test_json_safe():
    assert admin._json_safe(date(2024, 1, 2)) == "2024-01-02"
    assert admin._json_safe(datetime(2024, 1, 2, 3, 4, 5)) == "2024-01-02T03:04:05"
    assert admin._json_safe(Decimal("12.5")) == 12.5
    assert admin._json_safe("plain") == "plain"
    assert admin._json_safe(None) is None


def test_row_to_dict():
    row = SimpleNamespace(id=1, name="Ada")
    mapper = MagicMock()
    mapper.column_attrs = [SimpleNamespace(key="id"), SimpleNamespace(key="name")]
    inspected = MagicMock(mapper=mapper)

    with patch("routers.admin.inspect", return_value=inspected):
        assert admin._row_to_dict(row) == {"id": 1, "name": "Ada"}


def test_parse_value_converts_column_types():
    date_col = MagicMock()
    date_col.type = MagicMock()
    type(date_col.type).__name__ = "Date"

    datetime_col = MagicMock()
    datetime_col.type = MagicMock()
    type(datetime_col.type).__name__ = "DateTime"

    numeric_col = MagicMock()
    numeric_col.type = MagicMock()
    type(numeric_col.type).__name__ = "Numeric"

    columns = {
        "d": date_col,
        "dt": datetime_col,
        "n": numeric_col,
        "s": MagicMock(type=MagicMock()),
    }
    type(columns["s"].type).__name__ = "String"

    model = object()
    with patch("routers.admin.inspect", return_value=MagicMock(columns=columns)):
        assert admin._parse_value(model, "missing", "x") == "x"
        assert admin._parse_value(model, "d", None) is None
        assert admin._parse_value(model, "d", "2024-05-01") == date(2024, 5, 1)
        assert admin._parse_value(model, "dt", "2024-05-01T10:00:00") == datetime(2024, 5, 1, 10, 0, 0)
        assert admin._parse_value(model, "n", "3.14") == Decimal("3.14")
        assert admin._parse_value(model, "s", "hello") == "hello"


def test_admin_export(monkeypatch, client, db_mock, tmp_path):
    monkeypatch.setenv("ADMIN_SECRET", "secret")
    app.dependency_overrides[admin.get_db] = override_get_db(db_mock)

    img_dir = tmp_path / "place_images"
    img_dir.mkdir()
    (img_dir / "photo.jpg").write_bytes(b"img-bytes")
    monkeypatch.setattr(admin, "PLACE_IMAGES_DIR", img_dir)
    monkeypatch.setattr(admin, "ensure_place_images_dir", lambda: None)
    monkeypatch.setattr(admin, "_row_to_dict", lambda row: dict(row))

    table_rows = {
        "users": [{"id": 1}],
        "password_reset_tokens": [],
        "airlines": [],
        "airports": [],
        "direct_routes": [],
        "planned_trips": [],
        "visited_places": [],
        "planned_trip_stops": [],
        "images": [{"id": 9, "image_path": "uploads/place_images/photo.jpg"}],
        "trip_share_links": [],
        "trip_share_invitations": [],
        "feedbacks": [
            {
                "id": 3,
                "user_id": 1,
                "message": "hello",
                "image_path": "/uploads/feedback_images/fb.jpg",
            }
        ],
    }

    def query_side_effect(model):
        name = next(n for n, m in admin._EXPORT_MODELS if m is model)
        q = MagicMock()
        q.all.return_value = table_rows[name]
        return q

    db_mock.query.side_effect = query_side_effect

    fb_dir = tmp_path / "feedback_images"
    fb_dir.mkdir()
    (fb_dir / "fb.jpg").write_bytes(b"fb-bytes")
    monkeypatch.setattr(admin, "FEEDBACK_IMAGES_DIR", fb_dir)
    monkeypatch.setattr(admin, "ensure_feedback_images_dir", lambda: None)

    res = client.get("/api/admin/export", headers={"X-Admin-Secret": "secret"})

    assert res.status_code == 200
    body = res.json()
    assert body["version"] == 1
    assert body["users"] == [{"id": 1}]
    assert body["password_reset_tokens"] == []
    assert body["feedbacks"][0]["id"] == 3
    assert body["image_files"]["photo.jpg"] == base64.b64encode(b"img-bytes").decode("ascii")
    assert body["feedback_image_files"]["fb.jpg"] == base64.b64encode(b"fb-bytes").decode("ascii")
    assert "feedbacks" in {name for name, _ in admin._EXPORT_MODELS}
    assert "password_reset_tokens" in {name for name, _ in admin._EXPORT_MODELS}
    assert "feedbacks" in admin._SEQUENCE_TABLES
    assert "password_reset_tokens" in admin._SEQUENCE_TABLES


def test_admin_import_invalid_payload_list_rejected_by_schema(monkeypatch, client, db_mock):
    monkeypatch.setenv("ADMIN_SECRET", "secret")
    app.dependency_overrides[admin.get_db] = override_get_db(db_mock)

    res = client.post(
        "/api/admin/import",
        headers={"X-Admin-Secret": "secret"},
        json=["not-a-dict"],
    )

    assert res.status_code == 422


def test_admin_import_invalid_payload_direct():
    with pytest.raises(HTTPException) as exc:
        admin.admin_import(["not-a-dict"], db=MagicMock(), _=None)  # type: ignore[arg-type]
    assert exc.value.status_code == 400
    assert "Invalid export file" in str(exc.value.detail)


def test_admin_import_missing_version(monkeypatch, client, db_mock):
    monkeypatch.setenv("ADMIN_SECRET", "secret")
    app.dependency_overrides[admin.get_db] = override_get_db(db_mock)

    res = client.post(
        "/api/admin/import",
        headers={"X-Admin-Secret": "secret"},
        json={"users": []},
    )

    assert res.status_code == 400


def test_admin_import_success(monkeypatch, client, db_mock, tmp_path):
    monkeypatch.setenv("ADMIN_SECRET", "secret")
    app.dependency_overrides[admin.get_db] = override_get_db(db_mock)

    img_dir = tmp_path / "place_images"
    monkeypatch.setattr(admin, "PLACE_IMAGES_DIR", img_dir)
    monkeypatch.setattr(admin, "ensure_place_images_dir", lambda: img_dir.mkdir(parents=True, exist_ok=True))
    fb_dir = tmp_path / "feedback_images"
    monkeypatch.setattr(admin, "FEEDBACK_IMAGES_DIR", fb_dir)
    monkeypatch.setattr(admin, "ensure_feedback_images_dir", lambda: fb_dir.mkdir(parents=True, exist_ok=True))
    monkeypatch.setattr(admin, "_parse_value", lambda model, key, value: value)

    # Avoid constructing real SQLAlchemy models with arbitrary kwargs.
    created = []

    class FakeModel:
        def __init__(self, **kwargs):
            created.append(kwargs)

    original_models = list(admin._EXPORT_MODELS)
    monkeypatch.setattr(
        admin,
        "_EXPORT_MODELS",
        [(name, FakeModel) for name, _model in original_models],
    )

    payload = {
        "version": 1,
        "image_files": {"a.png": base64.b64encode(b"png").decode("ascii")},
        "feedback_image_files": {"fb.jpg": base64.b64encode(b"fb").decode("ascii")},
        "users": [{"id": 1, "username": "ada"}],
    }
    for name, _model in original_models:
        payload.setdefault(name, [])

    res = client.post(
        "/api/admin/import",
        headers={"X-Admin-Secret": "secret"},
        json=payload,
    )

    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["counts"]["users"] == 1
    assert created[0]["username"] == "ada"
    assert (img_dir / "a.png").read_bytes() == b"png"
    assert (fb_dir / "fb.jpg").read_bytes() == b"fb"
    db_mock.commit.assert_called()


def test_admin_import_rolls_back_on_failure(monkeypatch, client, db_mock):
    monkeypatch.setenv("ADMIN_SECRET", "secret")
    app.dependency_overrides[admin.get_db] = override_get_db(db_mock)
    db_mock.execute.side_effect = RuntimeError("boom")

    res = client.post(
        "/api/admin/import",
        headers={"X-Admin-Secret": "secret"},
        json={"version": 1},
    )

    assert res.status_code == 400
    assert "Import failed" in res.json()["detail"]
    db_mock.rollback.assert_called()
