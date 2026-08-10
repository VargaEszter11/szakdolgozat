"""
Integration tests for route planner and geocoding endpoints.
"""
from unittest.mock import AsyncMock, patch


class TestGeocode:
    """Integration tests for POST /api/geocode."""

    @patch("travel_types.plan_requests.geocode_place", new_callable=AsyncMock)
    def test_geocode_places(self, mock_geocode, client, auth_headers):
        mock_geocode.return_value = (47.5, 19.0)

        response = client.post(
            "/api/geocode",
            headers=auth_headers,
            json={"places": ["Budapest", "Vienna"]},
        )

        assert response.status_code == 200
        results = response.json()
        assert len(results) == 2
        assert results[0]["lat"] == 47.5
        assert results[0]["lon"] == 19.0


class TestTravelPlanGeneration:
    """Integration tests for travel plan generation endpoints."""

    @patch("routers.route_planner.generate_visited_plan", new_callable=AsyncMock)
    def test_generate_visited_plan(self, mock_generate, client, test_user, auth_headers):
        mock_generate.return_value = {"type": "visited", "plans": []}

        response = client.post(
            "/generate_travel_plans/visited",
            headers=auth_headers,
            json={
                "visitedPlaces": ["Paris"],
                "startingPoint": "Budapest",
                "startDate": "2026-07-01",
                "endDate": "2026-07-10",
                "userId": test_user["id"],
            },
        )

        assert response.status_code == 200
        assert response.json()["type"] == "visited"

    @patch("routers.route_planner.generate_unvisited_plan", new_callable=AsyncMock)
    def test_generate_unvisited_plan(self, mock_generate, client, test_user, auth_headers):
        mock_generate.return_value = {"type": "unvisited", "plans": []}

        response = client.post(
            "/generate_travel_plans/unvisited",
            headers=auth_headers,
            json={
                "startingPoint": "Budapest",
                "startDate": "2026-07-01",
                "endDate": "2026-07-10",
                "userId": test_user["id"],
            },
        )

        assert response.status_code == 200
        assert response.json()["type"] == "unvisited"

    @patch("routers.route_planner.generate_random_plan", new_callable=AsyncMock)
    def test_generate_random_plan(self, mock_generate, client, auth_headers):
        mock_generate.return_value = {"type": "random", "plans": []}

        response = client.post(
            "/generate_travel_plans/random",
            headers=auth_headers,
            json={
                "startingPoint": "Budapest",
                "startDate": "2026-07-01",
                "endDate": "2026-07-10",
            },
        )

        assert response.status_code == 200
        assert response.json()["type"] == "random"
