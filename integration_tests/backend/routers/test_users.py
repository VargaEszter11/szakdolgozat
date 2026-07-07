"""
Integration tests for user management endpoints.
"""


class TestCreateUser:
    """Integration tests for POST /api/users."""

    def test_create_user_success(self, client):
        response = client.post(
            "/api/users",
            json={
                "username": "apiuser",
                "email": "apiuser@example.com",
                "password": "ApiPass123",
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
                "password": "ApiPass123",
            },
        )

        assert response.status_code == 400


class TestGetUser:
    """Integration tests for GET /api/users/{user_id}."""

    def test_get_user_success(self, client, test_user):
        response = client.get(f"/api/users/{test_user['id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user["id"]
        assert data["username"] == test_user["username"]

    def test_get_user_not_found(self, client):
        response = client.get("/api/users/9999")

        assert response.status_code == 404


class TestListUsers:
    """Integration tests for GET /api/users."""

    def test_list_users(self, client, test_user, test_user_2):
        response = client.get("/api/users")

        assert response.status_code == 200
        users = response.json()
        assert len(users) >= 2
        usernames = {u["username"] for u in users}
        assert test_user["username"] in usernames
        assert test_user_2["username"] in usernames

    def test_search_users(self, client, test_user):
        response = client.get(f"/api/users?search={test_user['username']}")

        assert response.status_code == 200
        users = response.json()
        assert any(u["username"] == test_user["username"] for u in users)

    def test_list_users_exclude_user(self, client, test_user, test_user_2):
        response = client.get(f"/api/users?exclude_user_id={test_user['id']}")

        assert response.status_code == 200
        users = response.json()
        assert all(u["id"] != test_user["id"] for u in users)
        assert any(u["id"] == test_user_2["id"] for u in users)


class TestUpdateUser:
    """Integration tests for PUT /api/users/{user_id}."""

    def test_update_user_success(self, client, test_user):
        response = client.put(
            f"/api/users/{test_user['id']}",
            json={"username": "updateduser"},
        )

        assert response.status_code == 200
        assert response.json()["username"] == "updateduser"

    def test_update_user_username_taken(self, client, test_user, test_user_2):
        response = client.put(
            f"/api/users/{test_user['id']}",
            json={"username": test_user_2["username"]},
        )

        assert response.status_code == 400

    def test_update_user_not_found(self, client):
        response = client.put(
            "/api/users/9999",
            json={"username": "ghost"},
        )

        assert response.status_code == 404


class TestDeleteUser:
    """Integration tests for DELETE /api/users/{user_id}."""

    def test_delete_user_success(self, client, db):
        from database import crud, schemas

        user = crud.create_user(
            db=db,
            user=schemas.UserCreate(
                username="deleteme",
                email="deleteme@example.com",
                password="DeleteMe123",
            ),
        )
        db.commit()

        response = client.delete(f"/api/users/{user.id}")

        assert response.status_code == 204
        assert client.get(f"/api/users/{user.id}").status_code == 404

    def test_delete_user_not_found(self, client):
        response = client.delete("/api/users/9999")

        assert response.status_code == 404


class TestUserRelations:
    """Integration tests for user nested resource endpoints."""

    def test_get_user_visited_places(self, client, test_user, visited_place):
        response = client.get(f"/api/users/{test_user['id']}/visited-places")

        assert response.status_code == 200
        places = response.json()
        assert len(places) == 1
        assert places[0]["place_name"] == visited_place["place_name"]

    def test_get_user_visited_places_user_not_found(self, client):
        response = client.get("/api/users/9999/visited-places")

        assert response.status_code == 404

    def test_get_user_planned_trips(self, client, test_user, planned_trip):
        response = client.get(f"/api/users/{test_user['id']}/planned-trips")

        assert response.status_code == 200
        trips = response.json()
        assert len(trips) == 1
        assert trips[0]["title"] == planned_trip["title"]

    def test_get_user_planned_trips_user_not_found(self, client):
        response = client.get("/api/users/9999/planned-trips")

        assert response.status_code == 404
