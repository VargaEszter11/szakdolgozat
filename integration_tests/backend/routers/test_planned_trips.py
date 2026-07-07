"""
Integration tests for planned trip endpoints.
"""


class TestCreatePlannedTrip:
    """Integration tests for POST /api/planned-trips."""

    def test_create_planned_trip_success(self, client, test_user):
        response = client.post(
            "/api/planned-trips",
            json={
                "user_id": test_user["id"],
                "title": "Balkan Tour",
                "start_date": "2026-08-01",
                "end_date": "2026-08-15",
                "start_city": "Budapest",
                "people": 3,
                "is_booked": False,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Balkan Tour"
        assert data["user_id"] == test_user["id"]
        assert data["people"] == 3

    def test_create_planned_trip_user_not_found(self, client):
        response = client.post(
            "/api/planned-trips",
            json={
                "user_id": 9999,
                "title": "Ghost Trip",
                "people": 1,
                "is_booked": False,
            },
        )

        assert response.status_code == 404


class TestGetPlannedTrip:
    """Integration tests for GET /api/planned-trips/{trip_id}."""

    def test_get_planned_trip_success(self, client, planned_trip):
        response = client.get(f"/api/planned-trips/{planned_trip['id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == planned_trip["id"]
        assert data["title"] == planned_trip["title"]

    def test_get_planned_trip_not_found(self, client):
        response = client.get("/api/planned-trips/9999")

        assert response.status_code == 404


class TestListPlannedTrips:
    """Integration tests for GET /api/planned-trips."""

    def test_list_planned_trips_by_user(self, client, test_user, planned_trip):
        response = client.get(f"/api/planned-trips?user_id={test_user['id']}")

        assert response.status_code == 200
        trips = response.json()
        assert len(trips) == 1
        assert trips[0]["id"] == planned_trip["id"]

    def test_list_planned_trips_all(self, client, planned_trip):
        response = client.get("/api/planned-trips")

        assert response.status_code == 200
        trips = response.json()
        assert len(trips) >= 1

    def test_list_planned_trips_user_not_found(self, client):
        response = client.get("/api/planned-trips?user_id=9999")

        assert response.status_code == 404


class TestUpdatePlannedTrip:
    """Integration tests for PUT /api/planned-trips/{trip_id}."""

    def test_update_planned_trip_success(self, client, planned_trip):
        response = client.put(
            f"/api/planned-trips/{planned_trip['id']}",
            json={"title": "Updated Trip Title", "people": 4},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Trip Title"
        assert data["people"] == 4

    def test_update_planned_trip_not_found(self, client):
        response = client.put(
            "/api/planned-trips/9999",
            json={"title": "Missing"},
        )

        assert response.status_code == 404


class TestDeletePlannedTrip:
    """Integration tests for DELETE /api/planned-trips/{trip_id}."""

    def test_delete_planned_trip_success(self, client, planned_trip):
        response = client.delete(f"/api/planned-trips/{planned_trip['id']}")

        assert response.status_code == 204
        assert client.get(f"/api/planned-trips/{planned_trip['id']}").status_code == 404

    def test_delete_planned_trip_not_found(self, client):
        response = client.delete("/api/planned-trips/9999")

        assert response.status_code == 404
