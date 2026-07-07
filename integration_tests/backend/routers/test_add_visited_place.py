"""
Integration tests for adding visited places endpoint.
"""
import pytest


class TestAddVisitedPlace:
    """Integration tests for adding visited places."""

    def test_add_visited_place_success(self, client, test_user):
        """Test successfully adding a visited place."""
        response = client.post(
            "/api/visited-places",
            json={
                "user_id": test_user["id"],
                "place_name": "Eiffel Tower",
                "country": "FR",
                "visit_date": "2024-01-15"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["place_name"] == "Eiffel Tower"
        assert data["country"] == "FR"
        assert data["user_id"] == test_user["id"]
        assert "id" in data

    def test_add_visited_place_without_country(self, client, test_user):
        """Test adding a visited place without specifying country."""
        response = client.post(
            "/api/visited-places",
            json={
                "user_id": test_user["id"],
                "place_name": "Big Ben",
                "visit_date": "2024-02-20"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["place_name"] == "Big Ben"
        assert data["user_id"] == test_user["id"]

    def test_add_visited_place_nonexistent_user(self, client):
        """Test adding a visited place for a non-existent user."""
        response = client.post(
            "/api/visited-places",
            json={
                "user_id": 9999,
                "place_name": "Statue of Liberty",
                "country": "US",
                "visit_date": "2024-03-10"
            }
        )

        assert response.status_code == 404
        assert "User not found" in response.json().get("detail", "")

    def test_add_multiple_visited_places(self, client, test_user):
        """Test adding multiple visited places for the same user."""
        places = [
            {
                "user_id": test_user["id"],
                "place_name": "Colosseum",
                "country": "IT",
                "visit_date": "2023-06-15"
            },
            {
                "user_id": test_user["id"],
                "place_name": "Sagrada Familia",
                "country": "ES",
                "visit_date": "2023-07-20"
            },
            {
                "user_id": test_user["id"],
                "place_name": "Acropolis",
                "country": "GR",
                "visit_date": "2023-08-10"
            }
        ]

        responses = []
        for place_data in places:
            response = client.post("/api/visited-places", json=place_data)
            responses.append(response)

        # All should be successful
        assert all(r.status_code == 201 for r in responses)

        # Verify all places were added
        place_ids = [r.json()["id"] for r in responses]
        assert len(place_ids) == 3
        assert len(set(place_ids)) == 3  # All unique IDs

    def test_add_visited_place_missing_place_name(self, client, test_user):
        """Test adding a visited place without place_name."""
        response = client.post(
            "/api/visited-places",
            json={
                "user_id": test_user["id"],
                "country": "FR",
                "visit_date": "2024-01-15"
            }
        )

        assert response.status_code == 422  # Validation error

    def test_add_visited_place_missing_user_id(self, client):
        """Test adding a visited place without user_id."""
        response = client.post(
            "/api/visited-places",
            json={
                "place_name": "Eiffel Tower",
                "country": "FR",
                "visit_date": "2024-01-15"
            }
        )

        assert response.status_code == 422  # Validation error

    def test_add_visited_place_with_description(self, client, test_user):
        """Test adding a visited place with description."""
        response = client.post(
            "/api/visited-places",
            json={
                "user_id": test_user["id"],
                "place_name": "Taj Mahal",
                "country": "IN",
                "visit_date": "2024-04-05",
                "description": "Beautiful marble mausoleum, must see!"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "Beautiful marble mausoleum, must see!"
