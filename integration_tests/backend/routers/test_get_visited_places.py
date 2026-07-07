"""
Integration tests for retrieving visited places endpoints.
"""
import pytest


class TestGetVisitedPlaces:
    """Integration tests for retrieving visited places."""

    def test_get_visited_places_by_user(self, client, test_user):
        """Test retrieving visited places filtered by user."""
        # Add some places first
        places_data = [
            {"place_name": "Rome", "country": "IT", "visit_date": "2023-05-10"},
            {"place_name": "Paris", "country": "FR", "visit_date": "2023-06-15"},
            {"place_name": "Barcelona", "country": "ES", "visit_date": "2023-07-20"}
        ]

        added_ids = []
        for place in places_data:
            place["user_id"] = test_user["id"]
            response = client.post("/api/visited-places", json=place)
            added_ids.append(response.json()["id"])

        # Retrieve places by user
        response = client.get(f"/api/visited-places?user_id={test_user['id']}")

        assert response.status_code == 200
        places = response.json()
        assert len(places) == 3
        assert all(p["user_id"] == test_user["id"] for p in places)

    def test_get_visited_places_all(self, client, test_user, test_user_2):
        """Test retrieving all visited places without user filter."""
        # Add places for both users
        for user in [test_user, test_user_2]:
            for i in range(2):
                response = client.post(
                    "/api/visited-places",
                    json={
                        "user_id": user["id"],
                        "place_name": f"Place {user['username']}_{i}",
                        "country": "XX",
                        "visit_date": "2024-01-01"
                    }
                )
                assert response.status_code == 201

        # Retrieve all places
        response = client.get("/api/visited-places")

        assert response.status_code == 200
        places = response.json()
        assert len(places) == 4

    def test_get_visited_places_empty_list(self, client, test_user):
        """Test retrieving visited places when user has none."""
        response = client.get(f"/api/visited-places?user_id={test_user['id']}")

        assert response.status_code == 200
        places = response.json()
        assert len(places) == 0

    def test_get_visited_places_nonexistent_user(self, client):
        """Test retrieving visited places for non-existent user."""
        response = client.get("/api/visited-places?user_id=9999")

        assert response.status_code == 404

    def test_get_visited_places_with_pagination(self, client, test_user):
        """Test retrieving all visited places with skip and limit (without user filter)."""
        # Add 5 places
        for i in range(5):
            client.post(
                "/api/visited-places",
                json={
                    "user_id": test_user["id"],
                    "place_name": f"Place {i}",
                    "country": "XX",
                    "visit_date": "2024-01-01"
                }
            )

        # Get all places without user filter to test pagination parameters
        # (Note: pagination only works when user_id filter is NOT applied)
        response = client.get("/api/visited-places?skip=0&limit=2")
        assert response.status_code == 200
        places = response.json()
        assert len(places) <= 2

        # Get next batch
        response = client.get("/api/visited-places?skip=2&limit=2")
        assert response.status_code == 200
        places = response.json()
        assert len(places) <= 2

    def test_get_visited_place_by_id(self, client, test_user):
        """Test retrieving a specific visited place by ID."""
        # Add a place
        add_response = client.post(
            "/api/visited-places",
            json={
                "user_id": test_user["id"],
                "place_name": "Venice",
                "country": "IT",
                "visit_date": "2024-05-15",
                "description": "City of water and art"
            }
        )
        place_id = add_response.json()["id"]

        # Retrieve the place by ID
        response = client.get(f"/api/visited-places/{place_id}")

        assert response.status_code == 200
        place = response.json()
        assert place["id"] == place_id
        assert place["place_name"] == "Venice"
        assert place["country"] == "IT"
        assert place["description"] == "City of water and art"

    def test_get_visited_place_by_id_not_found(self, client):
        """Test retrieving a non-existent visited place by ID."""
        response = client.get("/api/visited-places/9999")

        assert response.status_code == 404
        assert "not found" in response.json().get("detail", "").lower()

    def test_get_visited_places_isolation_between_users(self, client, test_user, test_user_2):
        """Test that users can only see their own places."""
        # User 1 adds a place
        place1_response = client.post(
            "/api/visited-places",
            json={
                "user_id": test_user["id"],
                "place_name": "User1 Place",
                "country": "XX",
                "visit_date": "2024-01-01"
            }
        )
        assert place1_response.status_code == 201

        # User 2 adds a place
        place2_response = client.post(
            "/api/visited-places",
            json={
                "user_id": test_user_2["id"],
                "place_name": "User2 Place",
                "country": "YY",
                "visit_date": "2024-01-01"
            }
        )
        assert place2_response.status_code == 201

        # User 1 retrieves their places
        response1 = client.get(f"/api/visited-places?user_id={test_user['id']}")
        places1 = response1.json()
        assert len(places1) == 1
        assert places1[0]["place_name"] == "User1 Place"

        # User 2 retrieves their places
        response2 = client.get(f"/api/visited-places?user_id={test_user_2['id']}")
        places2 = response2.json()
        assert len(places2) == 1
        assert places2[0]["place_name"] == "User2 Place"
