"""
Integration tests for adding visited places endpoint.
"""


class TestAddVisitedPlace:
    """Integration tests for adding visited places."""

    def test_add_visited_place_success(self, client, test_user, auth_headers):
        """Test successfully adding a visited place."""
        response = client.post(
            "/api/visited-places",
            headers=auth_headers,
            json={
                "user_id": test_user["id"],
                "place_name": "Eiffel Tower",
                "country": "FR",
                "date": "2024-01-15",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["place_name"] == "Eiffel Tower"
        assert data["country"] == "FR"
        assert data["user_id"] == test_user["id"]
        assert "id" in data

    def test_add_visited_place_without_country(self, client, test_user, auth_headers):
        """Test adding a visited place without specifying country."""
        response = client.post(
            "/api/visited-places",
            headers=auth_headers,
            json={
                "user_id": test_user["id"],
                "place_name": "Big Ben",
                "date": "2024-02-20",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["place_name"] == "Big Ben"
        assert data["user_id"] == test_user["id"]

    def test_add_visited_place_unauthorized(self, client):
        """Test adding a visited place without auth."""
        response = client.post(
            "/api/visited-places",
            json={
                "user_id": 9999,
                "place_name": "Statue of Liberty",
                "country": "US",
                "date": "2024-03-10",
            },
        )

        assert response.status_code == 401

    def test_add_multiple_visited_places(self, client, test_user, auth_headers):
        """Test adding multiple visited places for the same user."""
        places = [
            {
                "user_id": test_user["id"],
                "place_name": "Colosseum",
                "country": "IT",
                "date": "2023-06-15",
            },
            {
                "user_id": test_user["id"],
                "place_name": "Sagrada Familia",
                "country": "ES",
                "date": "2023-07-20",
            },
            {
                "user_id": test_user["id"],
                "place_name": "Acropolis",
                "country": "GR",
                "date": "2023-08-10",
            },
        ]

        responses = []
        for place_data in places:
            response = client.post(
                "/api/visited-places",
                headers=auth_headers,
                json=place_data,
            )
            responses.append(response)

        assert all(r.status_code == 201 for r in responses)

        place_ids = [r.json()["id"] for r in responses]
        assert len(place_ids) == 3
        assert len(set(place_ids)) == 3

    def test_add_visited_place_missing_place_name(self, client, test_user, auth_headers):
        """Test adding a visited place without place_name."""
        response = client.post(
            "/api/visited-places",
            headers=auth_headers,
            json={
                "user_id": test_user["id"],
                "country": "FR",
                "date": "2024-01-15",
            },
        )

        assert response.status_code == 422

    def test_add_visited_place_missing_user_id(self, client, auth_headers):
        """Test adding a visited place without user_id (schema still requires it)."""
        response = client.post(
            "/api/visited-places",
            headers=auth_headers,
            json={
                "place_name": "Eiffel Tower",
                "country": "FR",
                "date": "2024-01-15",
            },
        )

        assert response.status_code == 422

    def test_add_visited_place_with_description(self, client, test_user, auth_headers):
        """Test adding a visited place with description."""
        response = client.post(
            "/api/visited-places",
            headers=auth_headers,
            json={
                "user_id": test_user["id"],
                "place_name": "Taj Mahal",
                "country": "IN",
                "date": "2024-04-05",
                "description": "Beautiful marble mausoleum, must see!",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "Beautiful marble mausoleum, must see!"
