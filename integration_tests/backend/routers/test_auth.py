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

    @patch("routers.auth.get_google_client_secret")
    @patch("routers.auth.get_google_client_id")
    def test_google_login_not_configured(self, mock_client_id, mock_client_secret, client):
        mock_client_id.return_value = ""
        mock_client_secret.return_value = ""

        response = client.post(
            "/api/google-login",
            json={"code": "some-code"},
        )

        assert response.status_code == 500

    @patch("routers.auth.get_google_client_secret")
    @patch("routers.auth.get_google_client_id")
    @patch("routers.auth._exchange_google_code")
    @patch("routers.auth.id_token.verify_oauth2_token")
    def test_google_login_existing_user(
        self, mock_verify, mock_exchange, mock_client_id, mock_client_secret, client, test_user
    ):
        mock_client_id.return_value = "test-client-id"
        mock_client_secret.return_value = "test-client-secret"
        mock_exchange.return_value = {"id_token": "some-token"}
        mock_verify.return_value = {
            "email_verified": True,
            "email": test_user["email"],
            "name": "Test User",
        }

        response = client.post(
            "/api/google-login",
            json={"code": "valid-code"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["user_id"] == test_user["id"]

    @patch("routers.auth.get_google_client_secret")
    @patch("routers.auth.get_google_client_id")
    @patch("routers.auth._exchange_google_code")
    @patch("routers.auth.id_token.verify_oauth2_token")
    def test_google_login_creates_new_user(
        self, mock_verify, mock_exchange, mock_client_id, mock_client_secret, client
    ):
        mock_client_id.return_value = "test-client-id"
        mock_client_secret.return_value = "test-client-secret"
        mock_exchange.return_value = {"id_token": "some-token"}
        mock_verify.return_value = {
            "email_verified": True,
            "email": "googleuser@example.com",
            "name": "Google User",
        }

        response = client.post(
            "/api/google-login",
            json={"code": "valid-code"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["user_id"] > 0

    @patch("routers.auth.get_google_client_secret")
    @patch("routers.auth.get_google_client_id")
    @patch("routers.auth._exchange_google_code")
    def test_google_login_invalid_code(
        self, mock_exchange, mock_client_id, mock_client_secret, client
    ):
        mock_client_id.return_value = "test-client-id"
        mock_client_secret.return_value = "test-client-secret"
        mock_exchange.side_effect = ValueError("invalid code")

        response = client.post(
            "/api/google-login",
            json={"code": "bad-code"},
        )

        assert response.status_code == 401

    @patch("routers.auth.get_google_client_secret")
    @patch("routers.auth.get_google_client_id")
    @patch("routers.auth._exchange_google_code")
    @patch("routers.auth.id_token.verify_oauth2_token")
    def test_google_login_invalid_token(
        self, mock_verify, mock_exchange, mock_client_id, mock_client_secret, client
    ):
        mock_client_id.return_value = "test-client-id"
        mock_client_secret.return_value = "test-client-secret"
        mock_exchange.return_value = {"id_token": "bad-token"}
        mock_verify.side_effect = ValueError("invalid token")

        response = client.post(
            "/api/google-login",
            json={"code": "some-code"},
        )

        assert response.status_code == 401


class TestForgotPassword:
    """Integration tests for the email-based password reset flow."""

    @staticmethod
    def _request_reset_token(client, email):
        """Request a reset email and pull the raw token out of the mocked send call."""
        with patch("routers.auth.send_password_reset_email") as mock_send:
            response = client.post("/api/forgot-password/request", json={"email": email})
        return response, mock_send

    def test_forgot_password_request_known_email_sends_token(self, client, test_user):
        response, mock_send = self._request_reset_token(client, test_user["email"])

        assert response.status_code == 200
        assert response.json()["success"] is True
        mock_send.assert_called_once()
        reset_url = mock_send.call_args.args[1]
        assert "token=" in reset_url

    def test_forgot_password_request_unknown_email_still_returns_generic_success(self, client):
        response, mock_send = self._request_reset_token(client, "nobody@example.com")

        assert response.status_code == 200
        assert response.json()["success"] is True
        mock_send.assert_not_called()

    def test_forgot_password_reset_success(self, client, test_user):
        response, mock_send = self._request_reset_token(client, test_user["email"])
        reset_url = mock_send.call_args.args[1]
        token = reset_url.split("token=", 1)[1]

        reset_response = client.post(
            "/api/forgot-password/reset",
            json={
                "token": token,
                "new_password": "NewPassword789",
            },
        )

        assert reset_response.status_code == 200
        assert reset_response.json()["success"] is True

        login_response = client.post(
            "/api/login",
            json={
                "username": test_user["username"],
                "password": "NewPassword789",
            },
        )
        assert login_response.status_code == 200

    def test_forgot_password_reset_token_cannot_be_reused(self, client, test_user):
        response, mock_send = self._request_reset_token(client, test_user["email"])
        reset_url = mock_send.call_args.args[1]
        token = reset_url.split("token=", 1)[1]

        first = client.post(
            "/api/forgot-password/reset",
            json={"token": token, "new_password": "NewPassword789"},
        )
        assert first.status_code == 200

        second = client.post(
            "/api/forgot-password/reset",
            json={"token": token, "new_password": "AnotherPassword123"},
        )
        assert second.status_code == 400

    def test_forgot_password_reset_invalid_token(self, client):
        response = client.post(
            "/api/forgot-password/reset",
            json={
                "token": "not-a-real-token",
                "new_password": "NewPassword789",
            },
        )

        assert response.status_code == 400
