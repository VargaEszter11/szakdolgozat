"""
Integration tests for retrieving visited places endpoints.
"""


class TestGetVisitedPlaces:
    """Integration tests for retrieving visited places."""

    def test_get_visited_places_by_user(self, client, test_user, auth_headers):
        """Test retrieving visited places for the authenticated user."""
        places_data = [
            {"place_name": "Rome", "country": "IT", "date": "2023-05-10"},
            {"place_name": "Paris", "country": "FR", "date": "2023-06-15"},
            {"place_name": "Barcelona", "country": "ES", "date": "2023-07-20"},
        ]

        for place in places_data:
            place["user_id"] = test_user["id"]
            response = client.post("/api/visited-places", headers=auth_headers, json=place)
            assert response.status_code == 201

        response = client.get("/api/visited-places", headers=auth_headers)

        assert response.status_code == 200
        places = response.json()
        assert len(places) == 3
        assert all(p["user_id"] == test_user["id"] for p in places)

    def test_get_visited_places_only_own(
        self, client, test_user, test_user_2, auth_headers, auth_headers_2
    ):
        """List endpoint returns only the authenticated user's places."""
        for user, headers in ((test_user, auth_headers), (test_user_2, auth_headers_2)):
            for i in range(2):
                response = client.post(
                    "/api/visited-places",
                    headers=headers,
                    json={
                        "user_id": user["id"],
                        "place_name": f"Place {user['username']}_{i}",
                        "country": "XX",
                        "date": "2024-01-01",
                    },
                )
                assert response.status_code == 201

        response = client.get("/api/visited-places", headers=auth_headers)

        assert response.status_code == 200
        places = response.json()
        assert len(places) == 2
        assert all(p["user_id"] == test_user["id"] for p in places)

    def test_get_visited_places_empty_list(self, client, auth_headers):
        """Test retrieving visited places when user has none."""
        response = client.get("/api/visited-places", headers=auth_headers)

        assert response.status_code == 200
        assert response.json() == []

    def test_get_visited_places_unauthorized(self, client):
        """Unauthenticated list returns 401."""
        response = client.get("/api/visited-places")

        assert response.status_code == 401

    def test_get_visited_place_by_id(self, client, test_user, auth_headers):
        """Test retrieving a specific visited place by ID."""
        add_response = client.post(
            "/api/visited-places",
            headers=auth_headers,
            json={
                "user_id": test_user["id"],
                "place_name": "Venice",
                "country": "IT",
                "date": "2024-05-15",
                "description": "City of water and art",
            },
        )
        place_id = add_response.json()["id"]

        response = client.get(f"/api/visited-places/{place_id}", headers=auth_headers)

        assert response.status_code == 200
        place = response.json()
        assert place["id"] == place_id
        assert place["place_name"] == "Venice"
        assert place["country"] == "IT"
        assert place["description"] == "City of water and art"

    def test_get_visited_place_by_id_not_found(self, client, auth_headers):
        """Test retrieving a non-existent visited place by ID."""
        response = client.get("/api/visited-places/9999", headers=auth_headers)

        assert response.status_code == 404
        assert "not found" in response.json().get("detail", "").lower()

    def test_get_visited_places_isolation_between_users(
        self, client, test_user, test_user_2, auth_headers, auth_headers_2
    ):
        """Test that users can only see their own places."""
        place1_response = client.post(
            "/api/visited-places",
            headers=auth_headers,
            json={
                "user_id": test_user["id"],
                "place_name": "User1 Place",
                "country": "XX",
                "date": "2024-01-01",
            },
        )
        assert place1_response.status_code == 201

        place2_response = client.post(
            "/api/visited-places",
            headers=auth_headers_2,
            json={
                "user_id": test_user_2["id"],
                "place_name": "User2 Place",
                "country": "YY",
                "date": "2024-01-01",
            },
        )
        assert place2_response.status_code == 201

        response1 = client.get("/api/visited-places", headers=auth_headers)
        places1 = response1.json()
        assert len(places1) == 1
        assert places1[0]["place_name"] == "User1 Place"

        response2 = client.get("/api/visited-places", headers=auth_headers_2)
        places2 = response2.json()
        assert len(places2) == 1
        assert places2[0]["place_name"] == "User2 Place"
