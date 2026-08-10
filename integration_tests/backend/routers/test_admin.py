"""
Integration tests for admin export/import endpoints.
"""
import base64
import re

import pytest

from routers import admin


ADMIN_SECRET = "integration-admin-secret"
ADMIN_HEADERS = {"X-Admin-Secret": ADMIN_SECRET}


@pytest.fixture
def admin_secret(monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET", ADMIN_SECRET)


@pytest.fixture
def sqlite_admin_sql(monkeypatch):
    """Translate Postgres-only wipe/sequence SQL into SQLite-safe statements."""
    real_text = admin.text

    def adapted_text(clause):
        sql = clause if isinstance(clause, str) else str(clause)
        if "TRUNCATE TABLE" in sql:
            match = re.search(r'TRUNCATE TABLE "([^"]+)"', sql)
            assert match is not None
            return real_text(f'DELETE FROM "{match.group(1)}"')
        if "pg_get_serial_sequence" in sql or "DO $$" in sql:
            return real_text("SELECT 1")
        return real_text(clause)

    monkeypatch.setattr(admin, "text", adapted_text)


class TestAdminAuth:
    def test_ping_not_configured(self, client, monkeypatch):
        monkeypatch.delenv("ADMIN_SECRET", raising=False)

        response = client.get("/api/admin/ping", headers=ADMIN_HEADERS)

        assert response.status_code == 503

    def test_ping_invalid_secret(self, client, admin_secret):
        response = client.get(
            "/api/admin/ping",
            headers={"X-Admin-Secret": "wrong-secret"},
        )

        assert response.status_code == 401

    def test_ping_ok(self, client, admin_secret):
        response = client.get("/api/admin/ping", headers=ADMIN_HEADERS)

        assert response.status_code == 200
        assert response.json() == {"ok": True}


class TestAdminExport:
    def test_export_includes_seeded_data(
        self,
        client,
        admin_secret,
        test_user,
        visited_place,
        planned_trip,
        auth_headers,
        tmp_path,
        monkeypatch,
    ):
        img_dir = tmp_path / "place_images"
        img_dir.mkdir()
        photo = img_dir / "seed.png"
        photo.write_bytes(b"seed-bytes")
        monkeypatch.setattr(admin, "PLACE_IMAGES_DIR", img_dir)
        monkeypatch.setattr(admin, "ensure_place_images_dir", lambda: None)

        image_response = client.post(
            f"/api/visited-places/{visited_place['id']}/images",
            headers=auth_headers,
            json={"image_path": str(photo)},
        )
        assert image_response.status_code == 201

        response = client.get("/api/admin/export", headers=ADMIN_HEADERS)

        assert response.status_code == 200
        data = response.json()
        assert data["version"] == 1
        assert any(u["id"] == test_user["id"] for u in data["users"])
        assert any(p["id"] == visited_place["id"] for p in data["visited_places"])
        assert any(t["id"] == planned_trip["id"] for t in data["planned_trips"])
        assert data["image_files"]["seed.png"] == base64.b64encode(b"seed-bytes").decode("ascii")

    def test_export_requires_admin(self, client, monkeypatch):
        monkeypatch.delenv("ADMIN_SECRET", raising=False)

        response = client.get("/api/admin/export", headers=ADMIN_HEADERS)

        assert response.status_code == 503


class TestAdminImport:
    def test_import_rejects_missing_version(self, client, admin_secret):
        response = client.post(
            "/api/admin/import",
            headers=ADMIN_HEADERS,
            json={"users": []},
        )

        assert response.status_code == 400
        assert "Invalid export file" in response.json()["detail"]

    def test_import_round_trip(
        self,
        client,
        admin_secret,
        sqlite_admin_sql,
        test_user,
        visited_place,
        planned_trip,
        auth_headers,
        tmp_path,
        monkeypatch,
        db,
    ):
        img_dir = tmp_path / "place_images"
        img_dir.mkdir()
        photo = img_dir / "roundtrip.png"
        photo.write_bytes(b"roundtrip-bytes")
        monkeypatch.setattr(admin, "PLACE_IMAGES_DIR", img_dir)
        monkeypatch.setattr(admin, "ensure_place_images_dir", lambda: img_dir.mkdir(parents=True, exist_ok=True))

        image_response = client.post(
            f"/api/visited-places/{visited_place['id']}/images",
            headers=auth_headers,
            json={"image_path": str(photo)},
        )
        assert image_response.status_code == 201

        exported = client.get("/api/admin/export", headers=ADMIN_HEADERS)
        assert exported.status_code == 200
        payload = exported.json()

        # Mutate live data so a successful import is observable.
        client.put(
            f"/api/visited-places/{visited_place['id']}",
            headers=auth_headers,
            json={"place_name": "ChangedCity"},
        )
        assert client.get(
            f"/api/visited-places/{visited_place['id']}",
            headers=auth_headers,
        ).json()["place_name"] == "ChangedCity"

        imported = client.post("/api/admin/import", headers=ADMIN_HEADERS, json=payload)

        assert imported.status_code == 200
        body = imported.json()
        assert body["success"] is True
        assert body["counts"]["users"] >= 1
        assert body["counts"]["visited_places"] >= 1
        assert body["counts"]["planned_trips"] >= 1

        restored = client.get(
            f"/api/visited-places/{visited_place['id']}",
            headers=auth_headers,
        )
        assert restored.status_code == 200
        assert restored.json()["place_name"] == visited_place["place_name"]

        assert (img_dir / "roundtrip.png").read_bytes() == b"roundtrip-bytes"

    def test_import_failure_rolls_back(
        self,
        client,
        admin_secret,
        sqlite_admin_sql,
        test_user,
        auth_headers,
        monkeypatch,
    ):
        monkeypatch.setattr(admin, "ensure_place_images_dir", lambda: None)

        # Force failure after wipe by making model construction explode on users insert.
        original_models = list(admin._EXPORT_MODELS)

        class BoomUser:
            def __init__(self, **kwargs):
                raise RuntimeError("forced-import-failure")

        patched = []
        for name, model in original_models:
            patched.append((name, BoomUser if name == "users" else model))
        monkeypatch.setattr(admin, "_EXPORT_MODELS", patched)

        response = client.post(
            "/api/admin/import",
            headers=ADMIN_HEADERS,
            json={
                "version": 1,
                "users": [{"id": 1, "username": "x", "email": "x@y.com", "password": "hash"}],
                "airlines": [],
                "airports": [],
                "direct_routes": [],
                "planned_trips": [],
                "visited_places": [],
                "planned_trip_stops": [],
                "images": [],
                "trip_share_links": [],
                "trip_share_invitations": [],
            },
        )

        assert response.status_code == 400
        assert "Import failed" in response.json()["detail"]

        # Original user should still be queryable after rollback.
        users = client.get("/api/users/", headers=auth_headers)
        assert users.status_code == 200
        # Current user is excluded from search listing.
        assert all(u["id"] != test_user["id"] for u in users.json())
        # Confirm user still exists via self endpoint.
        me = client.get(f"/api/users/{test_user['id']}", headers=auth_headers)
        assert me.status_code == 200
        assert me.json()["id"] == test_user["id"]
