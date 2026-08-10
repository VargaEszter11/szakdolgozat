"""
Integration tests for visited place update and delete endpoints.
"""


class TestUpdateVisitedPlace:
    """Integration tests for PUT /api/visited-places/{place_id}."""

    def test_update_visited_place_success(self, client, visited_place, auth_headers):
        response = client.put(
            f"/api/visited-places/{visited_place['id']}",
            headers=auth_headers,
            json={
                "place_name": "Prague Castle",
                "description": "Historic landmark",
                "rating": 5,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["place_name"] == "Prague Castle"
        assert data["description"] == "Historic landmark"
        assert data["rating"] == 5

    def test_update_visited_place_not_found(self, client, auth_headers):
        response = client.put(
            "/api/visited-places/9999",
            headers=auth_headers,
            json={"place_name": "Missing"},
        )

        assert response.status_code == 404


class TestDeleteVisitedPlace:
    """Integration tests for DELETE /api/visited-places/{place_id}."""

    def test_delete_visited_place_success(self, client, visited_place, auth_headers):
        response = client.delete(
            f"/api/visited-places/{visited_place['id']}",
            headers=auth_headers,
        )

        assert response.status_code == 204
        assert client.get(
            f"/api/visited-places/{visited_place['id']}",
            headers=auth_headers,
        ).status_code == 404

    def test_delete_visited_place_not_found(self, client, auth_headers):
        response = client.delete("/api/visited-places/9999", headers=auth_headers)

        assert response.status_code == 404
