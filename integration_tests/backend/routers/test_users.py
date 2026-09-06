"""
Integration tests for user management endpoints.
"""
from utils.auth_deps import create_access_token


class TestCreateUser:
    """Integration tests for POST /api/users."""

    def test_create_user_success(self, client):
        response = client.post(
            "/api/users",
            json={
                "username": "apiuser",
                "email": "apiuser@example.com",
                "password": "ApiPass123!",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "apiuser"
        assert data["email"] == "apiuser@example.com"
        assert "id" in data

    def test_create_user_duplicate_username(self, client, test_user):
        response = client.post(
            "/api/users",
            json={
                "username": test_user["username"],
                "email": "unique@example.com",
                "password": "ApiPass123!",
            },
        )

        assert response.status_code == 400


class TestGetUser:
    """Integration tests for GET /api/users/{user_id}."""

    def test_get_user_success(self, client, test_user, auth_headers):
        response = client.get(f"/api/users/{test_user['id']}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user["id"]
        assert data["username"] == test_user["username"]

    def test_get_user_forbidden_other_user(self, client, auth_headers):
        response = client.get("/api/users/9999", headers=auth_headers)

        assert response.status_code == 403

    def test_get_user_home_city_defaults_to_none(self, client, test_user, auth_headers):
        response = client.get(f"/api/users/{test_user['id']}", headers=auth_headers)

        assert response.status_code == 200
        assert response.json()["home_city"] is None


class TestListUsers:
    """Integration tests for GET /api/users."""

    def test_list_users(self, client, test_user, test_user_2, auth_headers):
        response = client.get("/api/users", headers=auth_headers)

        assert response.status_code == 200
        users = response.json()
        usernames = {u["username"] for u in users}
        assert test_user["username"] not in usernames
        assert test_user_2["username"] in usernames

    def test_search_users(self, client, test_user, test_user_2, auth_headers_2):
        response = client.get(
            f"/api/users?search={test_user['username']}",
            headers=auth_headers_2,
        )

        assert response.status_code == 200
        users = response.json()
        assert any(u["username"] == test_user["username"] for u in users)

    def test_list_users_excludes_self(self, client, test_user, test_user_2, auth_headers):
        response = client.get("/api/users", headers=auth_headers)

        assert response.status_code == 200
        users = response.json()
        assert all(u["id"] != test_user["id"] for u in users)
        assert any(u["id"] == test_user_2["id"] for u in users)


class TestUpdateUser:
    """Integration tests for PUT /api/users/{user_id}."""

    def test_update_user_success(self, client, test_user, auth_headers):
        response = client.put(
            f"/api/users/{test_user['id']}",
            headers=auth_headers,
            json={"username": "updateduser"},
        )

        assert response.status_code == 200
        assert response.json()["username"] == "updateduser"

    def test_update_user_username_taken(self, client, test_user, test_user_2, auth_headers):
        response = client.put(
            f"/api/users/{test_user['id']}",
            headers=auth_headers,
            json={"username": test_user_2["username"]},
        )

        assert response.status_code == 400

    def test_update_user_forbidden_other_user(self, client, auth_headers):
        response = client.put(
            "/api/users/9999",
            headers=auth_headers,
            json={"username": "ghost"},
        )

        assert response.status_code == 403

    def test_update_user_sets_home_city(self, client, test_user, auth_headers):
        response = client.put(
            f"/api/users/{test_user['id']}",
            headers=auth_headers,
            json={"home_city": "Budapest"},
        )

        assert response.status_code == 200
        assert response.json()["home_city"] == "Budapest"

        refetched = client.get(f"/api/users/{test_user['id']}", headers=auth_headers)
        assert refetched.json()["home_city"] == "Budapest"

    def test_update_user_can_clear_home_city(self, client, test_user, auth_headers):
        client.put(
            f"/api/users/{test_user['id']}",
            headers=auth_headers,
            json={"home_city": "Vienna"},
        )

        response = client.put(
            f"/api/users/{test_user['id']}",
            headers=auth_headers,
            json={"home_city": ""},
        )

        assert response.status_code == 200
        assert response.json()["home_city"] == ""

    def test_update_user_sets_tutorial_completed(self, client, test_user, auth_headers):
        response = client.put(
            f"/api/users/{test_user['id']}",
            headers=auth_headers,
            json={"tutorial_completed": True},
        )

        assert response.status_code == 200
        assert response.json()["tutorial_completed"] is True

        refetched = client.get(f"/api/users/{test_user['id']}", headers=auth_headers)
        assert refetched.json()["tutorial_completed"] is True

        login = client.post(
            "/api/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"],
            },
        )
        assert login.status_code == 200
        assert login.json()["tutorial_completed"] is True


class TestDeleteUser:
    """Integration tests for DELETE /api/users/{user_id}."""

    def test_delete_user_success(self, client, db):
        from database import crud, schemas

        user = crud.create_user(
            db=db,
            user=schemas.UserCreate(
                username="deleteme",
                email="deleteme@example.com",
                password="DeleteMe123!",
            ),
        )
        db.commit()

        headers = {
            "Authorization": f"Bearer {create_access_token(user_id=int(user.id), username='deleteme')}"
        }
        response = client.delete(f"/api/users/{user.id}", headers=headers)

        assert response.status_code == 204
        assert client.get(f"/api/users/{user.id}", headers=headers).status_code == 401

    def test_delete_user_forbidden_other_user(self, client, auth_headers):
        response = client.delete("/api/users/9999", headers=auth_headers)

        assert response.status_code == 403


class TestUserRelations:
    """Integration tests for user nested resource endpoints."""

    def test_get_user_visited_places(self, client, test_user, visited_place, auth_headers):
        response = client.get(
            f"/api/users/{test_user['id']}/visited-places",
            headers=auth_headers,
        )

        assert response.status_code == 200
        places = response.json()
        assert len(places) == 1
        assert places[0]["place_name"] == visited_place["place_name"]

    def test_get_user_visited_places_forbidden(self, client, auth_headers):
        response = client.get("/api/users/9999/visited-places", headers=auth_headers)

        assert response.status_code == 403

    def test_get_user_planned_trips(self, client, test_user, planned_trip, auth_headers):
        response = client.get(
            f"/api/users/{test_user['id']}/planned-trips",
            headers=auth_headers,
        )

        assert response.status_code == 200
        trips = response.json()
        assert len(trips) == 1
        assert trips[0]["title"] == planned_trip["title"]

    def test_get_user_planned_trips_forbidden(self, client, auth_headers):
        response = client.get("/api/users/9999/planned-trips", headers=auth_headers)

        assert response.status_code == 403
