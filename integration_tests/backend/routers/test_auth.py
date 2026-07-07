"""
Integration tests for authentication endpoints beyond login.
"""
from unittest.mock import patch


class TestRegister:
    """Integration tests for user registration."""

    def test_register_success(self, client):
        response = client.post(
            "/api/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "SecurePass123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "registered" in data["message"].lower()

    def test_register_duplicate_username(self, client, test_user):
        response = client.post(
            "/api/register",
            json={
                "username": test_user["username"],
                "email": "other@example.com",
                "password": "SecurePass123",
            },
        )

        assert response.status_code == 400
        assert "username" in response.json()["detail"].lower()

    def test_register_duplicate_email(self, client, test_user):
        response = client.post(
            "/api/register",
            json={
                "username": "anotheruser",
                "email": test_user["email"],
                "password": "SecurePass123",
            },
        )

        assert response.status_code == 400
        assert "email" in response.json()["detail"].lower()


class TestGoogleAuth:
    """Integration tests for Google OAuth endpoints."""

    @patch("routers.auth.get_google_client_id")
    def test_google_config(self, mock_client_id, client):
        mock_client_id.return_value = "test-client-id"

        response = client.get("/api/google-config")

        assert response.status_code == 200
        assert response.json()["client_id"] == "test-client-id"

    @patch("routers.auth.get_google_client_id")
    def test_google_login_not_configured(self, mock_client_id, client):
        mock_client_id.return_value = ""

        response = client.post(
            "/api/google-login",
            json={"credential": "some-token"},
        )

        assert response.status_code == 500

    @patch("routers.auth.get_google_client_id")
    @patch("routers.auth.id_token.verify_oauth2_token")
    def test_google_login_existing_user(self, mock_verify, mock_client_id, client, test_user):
        mock_client_id.return_value = "test-client-id"
        mock_verify.return_value = {
            "email_verified": True,
            "email": test_user["email"],
            "name": "Test User",
        }

        response = client.post(
            "/api/google-login",
            json={"credential": "valid-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["user_id"] == test_user["id"]

    @patch("routers.auth.get_google_client_id")
    @patch("routers.auth.id_token.verify_oauth2_token")
    def test_google_login_creates_new_user(self, mock_verify, mock_client_id, client):
        mock_client_id.return_value = "test-client-id"
        mock_verify.return_value = {
            "email_verified": True,
            "email": "googleuser@example.com",
            "name": "Google User",
        }

        response = client.post(
            "/api/google-login",
            json={"credential": "valid-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["user_id"] > 0

    @patch("routers.auth.get_google_client_id")
    @patch("routers.auth.id_token.verify_oauth2_token")
    def test_google_login_invalid_token(self, mock_verify, mock_client_id, client):
        mock_client_id.return_value = "test-client-id"
        mock_verify.side_effect = ValueError("invalid token")

        response = client.post(
            "/api/google-login",
            json={"credential": "bad-token"},
        )

        assert response.status_code == 401


class TestForgotPassword:
    """Integration tests for password reset flow."""

    def test_forgot_password_verify_success(self, client, test_user):
        response = client.post(
            "/api/forgot-password/verify",
            json={
                "username": test_user["username"],
                "email": test_user["email"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["user_id"] == test_user["id"]

    def test_forgot_password_verify_wrong_email(self, client, test_user):
        response = client.post(
            "/api/forgot-password/verify",
            json={
                "username": test_user["username"],
                "email": "wrong@example.com",
            },
        )

        assert response.status_code == 404

    def test_forgot_password_reset_success(self, client, test_user):
        verify_response = client.post(
            "/api/forgot-password/verify",
            json={
                "username": test_user["username"],
                "email": test_user["email"],
            },
        )
        user_id = verify_response.json()["user_id"]

        response = client.post(
            "/api/forgot-password/reset",
            json={
                "user_id": user_id,
                "new_password": "NewPassword789",
            },
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

        login_response = client.post(
            "/api/login",
            json={
                "username": test_user["username"],
                "password": "NewPassword789",
            },
        )
        assert login_response.status_code == 200

    def test_forgot_password_reset_user_not_found(self, client):
        response = client.post(
            "/api/forgot-password/reset",
            json={
                "user_id": 9999,
                "new_password": "NewPassword789",
            },
        )

        assert response.status_code == 404
