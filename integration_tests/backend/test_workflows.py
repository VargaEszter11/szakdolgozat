"""
Integration tests for complete workflows combining multiple features.
"""
import pytest


class TestLoginAndAddPlaceFlow:
    """Integration tests for combined login and add place workflow."""

    def test_login_then_add_place(self, client, test_user):
        """Test a complete flow: login then add a visited place."""
        # Step 1: Login
        login_response = client.post(
            "/api/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"]
            }
        )

        assert login_response.status_code == 200
        login_data = login_response.json()
        assert login_data["success"] is True
        user_id = login_data["user_id"]

        # Step 2: Add a visited place with the logged-in user ID
        place_response = client.post(
            "/api/visited-places",
            json={
                "user_id": user_id,
                "place_name": "Machu Picchu",
                "country": "PE",
                "visit_date": "2024-06-01",
                "description": "Ancient Inca citadel"
            }
        )

        assert place_response.status_code == 201
        place_data = place_response.json()
        assert place_data["user_id"] == user_id
        assert place_data["place_name"] == "Machu Picchu"

    def test_login_add_multiple_places_retrieve(self, client, test_user):
        """Test complete workflow: login, add multiple places, retrieve them."""
        # Step 1: Login
        login_response = client.post(
            "/api/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"]
            }
        )
        assert login_response.status_code == 200
        user_id = login_response.json()["user_id"]

        # Step 2: Add multiple places
        places = [
            "Mount Kilimanjaro",
            "Great Barrier Reef",
            "Niagara Falls"
        ]

        for place_name in places:
            response = client.post(
                "/api/visited-places",
                json={
                    "user_id": user_id,
                    "place_name": place_name,
                    "country": "XX",
                    "visit_date": "2024-01-01"
                }
            )
            assert response.status_code == 201

        # Step 3: Retrieve all places for the user
        retrieve_response = client.get(f"/api/visited-places?user_id={user_id}")

        assert retrieve_response.status_code == 200
        retrieved_places = retrieve_response.json()
        assert len(retrieved_places) == 3

        place_names = [p["place_name"] for p in retrieved_places]
        assert all(name in place_names for name in places)
