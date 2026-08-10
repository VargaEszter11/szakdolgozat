"""
Integration tests for trip stop endpoints.
"""


class TestCreateTripStop:
    """Integration tests for POST /api/trip-stops."""

    def test_create_trip_stop_success(self, client, planned_trip, auth_headers):
        response = client.post(
            "/api/trip-stops",
            headers=auth_headers,
            json={
                "trip_id": planned_trip["id"],
                "place_name": "Vienna",
                "country": "AT",
                "stop_order": 1,
                "arrival_date": "2026-07-03",
                "departure_date": "2026-07-05",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["place_name"] == "Vienna"
        assert data["trip_id"] == planned_trip["id"]

    def test_create_trip_stop_trip_not_found(self, client, auth_headers):
        response = client.post(
            "/api/trip-stops",
            headers=auth_headers,
            json={
                "trip_id": 9999,
                "place_name": "Nowhere",
            },
        )

        assert response.status_code == 404


class TestGetTripStop:
    """Integration tests for GET /api/trip-stops/{stop_id}."""

    def test_get_trip_stop_success(self, client, planned_trip, auth_headers):
        create_response = client.post(
            "/api/trip-stops",
            headers=auth_headers,
            json={
                "trip_id": planned_trip["id"],
                "place_name": "Bratislava",
                "country": "SK",
                "stop_order": 1,
            },
        )
        stop_id = create_response.json()["id"]

        response = client.get(f"/api/trip-stops/{stop_id}", headers=auth_headers)

        assert response.status_code == 200
        assert response.json()["place_name"] == "Bratislava"

    def test_get_trip_stop_not_found(self, client, auth_headers):
        response = client.get("/api/trip-stops/9999", headers=auth_headers)

        assert response.status_code == 404


class TestListTripStops:
    """Integration tests for GET /api/trips/{trip_id}/stops."""

    def test_get_trip_stops_success(self, client, planned_trip, auth_headers):
        client.post(
            "/api/trip-stops",
            headers=auth_headers,
            json={
                "trip_id": planned_trip["id"],
                "place_name": "Krakow",
                "country": "PL",
                "stop_order": 1,
            },
        )
        client.post(
            "/api/trip-stops",
            headers=auth_headers,
            json={
                "trip_id": planned_trip["id"],
                "place_name": "Warsaw",
                "country": "PL",
                "stop_order": 2,
            },
        )

        response = client.get(
            f"/api/trips/{planned_trip['id']}/stops",
            headers=auth_headers,
        )

        assert response.status_code == 200
        stops = response.json()
        assert len(stops) == 2

    def test_get_trip_stops_trip_not_found(self, client, auth_headers):
        response = client.get("/api/trips/9999/stops", headers=auth_headers)

        assert response.status_code == 404


class TestUpdateTripStop:
    """Integration tests for PUT /api/trip-stops/{stop_id}."""

    def test_update_trip_stop_success(self, client, planned_trip, auth_headers):
        create_response = client.post(
            "/api/trip-stops",
            headers=auth_headers,
            json={
                "trip_id": planned_trip["id"],
                "place_name": "Ljubljana",
                "country": "SI",
                "stop_order": 1,
            },
        )
        stop_id = create_response.json()["id"]

        response = client.put(
            f"/api/trip-stops/{stop_id}",
            headers=auth_headers,
            json={"place_name": "Lake Bled", "activities": "Hiking"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["place_name"] == "Lake Bled"
        assert data["activities"] == "Hiking"

    def test_update_trip_stop_not_found(self, client, auth_headers):
        response = client.put(
            "/api/trip-stops/9999",
            headers=auth_headers,
            json={"place_name": "Missing"},
        )

        assert response.status_code == 404


class TestDeleteTripStop:
    """Integration tests for DELETE /api/trip-stops/{stop_id}."""

    def test_delete_trip_stop_success(self, client, planned_trip, auth_headers):
        create_response = client.post(
            "/api/trip-stops",
            headers=auth_headers,
            json={
                "trip_id": planned_trip["id"],
                "place_name": "Zagreb",
                "country": "HR",
                "stop_order": 1,
            },
        )
        stop_id = create_response.json()["id"]

        response = client.delete(f"/api/trip-stops/{stop_id}", headers=auth_headers)

        assert response.status_code == 204
        assert client.get(f"/api/trip-stops/{stop_id}", headers=auth_headers).status_code == 404

    def test_delete_trip_stop_not_found(self, client, auth_headers):
        response = client.delete("/api/trip-stops/9999", headers=auth_headers)

        assert response.status_code == 404
