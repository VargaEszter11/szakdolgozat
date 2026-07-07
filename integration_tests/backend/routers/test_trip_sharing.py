"""
Integration tests for trip sharing endpoints.
"""


class TestTripShareLink:
    """Integration tests for public share link endpoints."""

    def test_create_share_link_success(self, client, test_user, planned_trip):
        response = client.post(
            f"/api/planned-trips/{planned_trip['id']}/share-link",
            json={"user_id": test_user["id"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["share_token"]
        assert "token=" in data["share_url"]

    def test_create_share_link_not_owner(self, client, test_user_2, planned_trip):
        response = client.post(
            f"/api/planned-trips/{planned_trip['id']}/share-link",
            json={"user_id": test_user_2["id"]},
        )

        assert response.status_code == 403

    def test_create_share_link_trip_not_found(self, client, test_user):
        response = client.post(
            "/api/planned-trips/9999/share-link",
            json={"user_id": test_user["id"]},
        )

        assert response.status_code == 404

    def test_get_shared_trip_by_token(self, client, test_user, planned_trip):
        link_response = client.post(
            f"/api/planned-trips/{planned_trip['id']}/share-link",
            json={"user_id": test_user["id"]},
        )
        token = link_response.json()["share_token"]

        client.post(
            "/api/trip-stops",
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

    def test_revoke_share_link(self, client, test_user, planned_trip):
        link_response = client.post(
            f"/api/planned-trips/{planned_trip['id']}/share-link",
            json={"user_id": test_user["id"]},
        )
        token = link_response.json()["share_token"]

        revoke_response = client.request(
            "DELETE",
            f"/api/planned-trips/{planned_trip['id']}/share-link",
            json={"user_id": test_user["id"]},
        )

        assert revoke_response.status_code == 204
        assert client.get(f"/api/shared-trips/{token}").status_code == 404


class TestTripShareInvitations:
    """Integration tests for user-to-user trip sharing."""

    def test_share_trip_with_user(self, client, test_user, test_user_2, planned_trip):
        response = client.post(
            f"/api/planned-trips/{planned_trip['id']}/share",
            json={
                "from_user_id": test_user["id"],
                "to_user_id": test_user_2["id"],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"
        assert data["to_user_id"] == test_user_2["id"]
        assert data["source_trip_id"] == planned_trip["id"]

    def test_share_trip_with_self(self, client, test_user, planned_trip):
        response = client.post(
            f"/api/planned-trips/{planned_trip['id']}/share",
            json={
                "from_user_id": test_user["id"],
                "to_user_id": test_user["id"],
            },
        )

        assert response.status_code == 400

    def test_list_trip_share_invitations(self, client, test_user, test_user_2, planned_trip):
        client.post(
            f"/api/planned-trips/{planned_trip['id']}/share",
            json={
                "from_user_id": test_user["id"],
                "to_user_id": test_user_2["id"],
            },
        )

        response = client.get(
            f"/api/users/{test_user_2['id']}/trip-share-invitations?status=pending"
        )

        assert response.status_code == 200
        invitations = response.json()
        assert len(invitations) == 1
        assert invitations[0]["from_user_id"] == test_user["id"]

    def test_accept_trip_share_invitation(self, client, test_user, test_user_2, planned_trip):
        share_response = client.post(
            f"/api/planned-trips/{planned_trip['id']}/share",
            json={
                "from_user_id": test_user["id"],
                "to_user_id": test_user_2["id"],
            },
        )
        invitation_id = share_response.json()["id"]

        response = client.post(
            f"/api/trip-share-invitations/{invitation_id}/accept",
            json={"user_id": test_user_2["id"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        assert data["result_trip_id"] is not None

        trips_response = client.get(f"/api/users/{test_user_2['id']}/planned-trips")
        assert len(trips_response.json()) == 1

    def test_decline_trip_share_invitation(self, client, test_user, test_user_2, planned_trip):
        share_response = client.post(
            f"/api/planned-trips/{planned_trip['id']}/share",
            json={
                "from_user_id": test_user["id"],
                "to_user_id": test_user_2["id"],
            },
        )
        invitation_id = share_response.json()["id"]

        response = client.post(
            f"/api/trip-share-invitations/{invitation_id}/decline",
            json={"user_id": test_user_2["id"]},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "declined"

    def test_accept_invitation_not_recipient(self, client, test_user, test_user_2, planned_trip):
        share_response = client.post(
            f"/api/planned-trips/{planned_trip['id']}/share",
            json={
                "from_user_id": test_user["id"],
                "to_user_id": test_user_2["id"],
            },
        )
        invitation_id = share_response.json()["id"]

        response = client.post(
            f"/api/trip-share-invitations/{invitation_id}/accept",
            json={"user_id": test_user["id"]},
        )

        assert response.status_code == 403
