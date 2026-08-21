"""
Integration tests for user feedback submission and admin feedback endpoints.
"""
from pathlib import Path

import pytest

from database import models


ADMIN_SECRET = "integration-admin-secret"
ADMIN_HEADERS = {"X-Admin-Secret": ADMIN_SECRET}


@pytest.fixture
def admin_secret(monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET", ADMIN_SECRET)


class TestSubmitFeedback:
    def test_requires_auth(self, client):
        response = client.post("/api/feedback", data={"message": "Hello"})
        assert response.status_code == 401

    def test_rejects_empty_message(self, client, auth_headers):
        response = client.post(
            "/api/feedback",
            data={"message": "   "},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_creates_feedback(self, client, auth_headers, test_user, db):
        response = client.post(
            "/api/feedback",
            data={"message": "  Love the trip planner  "},
            headers=auth_headers,
        )

        assert response.status_code == 201
        body = response.json()
        assert body["user_id"] == test_user["id"]
        assert body["username"] == test_user["username"]
        assert body["message"] == "Love the trip planner"
        assert body["image_path"] is None
        assert "id" in body
        assert "created_at" in body

        row = db.query(models.Feedback).filter(models.Feedback.id == body["id"]).one()
        assert row.message == "Love the trip planner"
        assert int(row.user_id) == int(test_user["id"])

    def test_creates_feedback_with_image(self, client, auth_headers, test_user, db, tmp_path, monkeypatch):
        from utils import feedback_image_upload as fui

        img_dir = tmp_path / "feedback_images"
        img_dir.mkdir()
        monkeypatch.setattr(fui, "FEEDBACK_IMAGES_DIR", img_dir)

        response = client.post(
            "/api/feedback",
            data={"message": "Bug screenshot"},
            files={"image": ("shot.png", b"\x89PNG\r\n\x1a\n", "image/png")},
            headers=auth_headers,
        )

        assert response.status_code == 201
        body = response.json()
        assert body["message"] == "Bug screenshot"
        assert body["image_path"]
        assert body["image_path"].startswith("/uploads/feedback_images/")

        saved = img_dir / Path(body["image_path"]).name
        assert saved.is_file()
        assert saved.read_bytes().startswith(b"\x89PNG")

        row = db.query(models.Feedback).filter(models.Feedback.id == body["id"]).one()
        assert row.image_path == body["image_path"]


class TestAdminFeedback:
    def test_list_requires_admin(self, client, admin_secret):
        response = client.get(
            "/api/admin/feedback",
            headers={"X-Admin-Secret": "wrong"},
        )
        assert response.status_code == 401

    def test_list_and_delete(
        self,
        client,
        admin_secret,
        auth_headers,
        test_user,
        db,
    ):
        create = client.post(
            "/api/feedback",
            data={"message": "Please add dark mode"},
            headers=auth_headers,
        )
        assert create.status_code == 201
        feedback_id = create.json()["id"]

        listed = client.get("/api/admin/feedback", headers=ADMIN_HEADERS)
        assert listed.status_code == 200
        items = listed.json()
        assert any(item["id"] == feedback_id for item in items)
        match = next(item for item in items if item["id"] == feedback_id)
        assert match["message"] == "Please add dark mode"
        assert match["username"] == test_user["username"]
        assert match["user_id"] == test_user["id"]

        deleted = client.delete(
            f"/api/admin/feedback/{feedback_id}",
            headers=ADMIN_HEADERS,
        )
        assert deleted.status_code == 200
        assert deleted.json() == {"success": True}
        assert db.query(models.Feedback).filter(models.Feedback.id == feedback_id).first() is None

        listed_after = client.get("/api/admin/feedback", headers=ADMIN_HEADERS)
        assert all(item["id"] != feedback_id for item in listed_after.json())

    def test_delete_missing(self, client, admin_secret):
        response = client.delete("/api/admin/feedback/999999", headers=ADMIN_HEADERS)
        assert response.status_code == 404
