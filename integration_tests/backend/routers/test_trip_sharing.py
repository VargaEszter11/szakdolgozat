"""
Integration tests for trip sharing endpoints.
"""


class TestTripShareLink:
    """Integration tests for public share link endpoints."""

    def test_create_share_link_success(self, client, planned_trip, auth_headers):
        response = client.post(
            f"/api/planned-trips/{planned_trip['id']}/share-link",
            headers=auth_headers,
            json={},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["share_token"]
        assert "token=" in data["share_url"]

    def test_create_share_link_not_owner(self, client, planned_trip, auth_headers_2):
        response = client.post(
            f"/api/planned-trips/{planned_trip['id']}/share-link",
            headers=auth_headers_2,
            json={},
        )

        assert response.status_code == 403

    def test_create_share_link_trip_not_found(self, client, auth_headers):
        response = client.post(
            "/api/planned-trips/9999/share-link",
            headers=auth_headers,
            json={},
        )

        assert response.status_code == 404

    def test_get_shared_trip_by_token(self, client, planned_trip, auth_headers):
        link_response = client.post(
            f"/api/planned-trips/{planned_trip['id']}/share-link",
            headers=auth_headers,
            json={},
        )
        token = link_response.json()["share_token"]

        client.post(
            "/api/trip-stops",
            headers=auth_headers,
            json={
                "trip_id": planned_trip["id"],
                "place_name": "Vienna",
                "country": "AT",
                "stop_order": 1,
            },
        )

        response = client.get(f"/api/shared-trips/{token}")

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == planned_trip["title"]
        assert len(data["stops"]) == 1

    def test_get_shared_trip_invalid_token(self, client):
        response = client.get("/api/shared-trips/invalid-token")

        assert response.status_code == 404

    def test_revoke_share_link(self, client, planned_trip, auth_headers):
        link_response = client.post(
            f"/api/planned-trips/{planned_trip['id']}/share-link",
            headers=auth_headers,
            json={},
        )
        token = link_response.json()["share_token"]

        revoke_response = client.request(
            "DELETE",
            f"/api/planned-trips/{planned_trip['id']}/share-link",
            headers=auth_headers,
            json={},
        )

        assert revoke_response.status_code == 204
        assert client.get(f"/api/shared-trips/{token}").status_code == 404


class TestTripShareInvitations:
    """Integration tests for user-to-user trip sharing."""

    def test_share_trip_with_user(self, client, test_user_2, planned_trip, auth_headers):
        response = client.post(
            f"/api/planned-trips/{planned_trip['id']}/share",
            headers=auth_headers,
            json={"to_user_id": test_user_2["id"]},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"
        assert data["to_user_id"] == test_user_2["id"]
        assert data["source_trip_id"] == planned_trip["id"]

    def test_share_trip_with_self(self, client, test_user, planned_trip, auth_headers):
        response = client.post(
            f"/api/planned-trips/{planned_trip['id']}/share",
            headers=auth_headers,
            json={"to_user_id": test_user["id"]},
        )

        assert response.status_code == 400

    def test_list_trip_share_invitations(
        self, client, test_user, test_user_2, planned_trip, auth_headers, auth_headers_2
    ):
        client.post(
            f"/api/planned-trips/{planned_trip['id']}/share",
            headers=auth_headers,
            json={"to_user_id": test_user_2["id"]},
        )

        response = client.get(
            f"/api/users/{test_user_2['id']}/trip-share-invitations?status=pending",
            headers=auth_headers_2,
        )

        assert response.status_code == 200
        invitations = response.json()
        assert len(invitations) == 1
        assert invitations[0]["from_user_id"] == test_user["id"]

    def test_accept_trip_share_invitation(
        self, client, test_user_2, planned_trip, auth_headers, auth_headers_2
    ):
        share_response = client.post(
            f"/api/planned-trips/{planned_trip['id']}/share",
            headers=auth_headers,
            json={"to_user_id": test_user_2["id"]},
        )
        invitation_id = share_response.json()["id"]

        response = client.post(
            f"/api/trip-share-invitations/{invitation_id}/accept",
            headers=auth_headers_2,
            json={},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        assert data["result_trip_id"] is not None

        trips_response = client.get(
            f"/api/users/{test_user_2['id']}/planned-trips",
            headers=auth_headers_2,
        )
        assert len(trips_response.json()) == 1

    def test_decline_trip_share_invitation(
        self, client, test_user_2, planned_trip, auth_headers, auth_headers_2
    ):
        share_response = client.post(
            f"/api/planned-trips/{planned_trip['id']}/share",
            headers=auth_headers,
            json={"to_user_id": test_user_2["id"]},
        )
        invitation_id = share_response.json()["id"]

        response = client.post(
            f"/api/trip-share-invitations/{invitation_id}/decline",
            headers=auth_headers_2,
            json={},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "declined"

    def test_accept_invitation_not_recipient(
        self, client, test_user_2, planned_trip, auth_headers
    ):
        share_response = client.post(
            f"/api/planned-trips/{planned_trip['id']}/share",
            headers=auth_headers,
            json={"to_user_id": test_user_2["id"]},
        )
        invitation_id = share_response.json()["id"]

        response = client.post(
            f"/api/trip-share-invitations/{invitation_id}/accept",
            headers=auth_headers,
            json={},
        )

        assert response.status_code == 403
