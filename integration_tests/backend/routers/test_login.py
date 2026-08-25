"""
Integration tests for user login endpoint.
"""
import pytest


class TestLogin:
    """Integration tests for user login endpoint."""

    def test_login_success(self, client, test_user):
        """Test successful login with correct credentials."""
        response = client.post(
            "/api/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"]
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["username"] == test_user["username"]
        assert data["user_id"] == test_user["id"]
        assert data.get("access_token")
        assert data.get("token_type") == "bearer"
        assert data.get("tutorial_completed") is False

    def test_login_user_not_found(self, client):
        """Test login with non-existent username."""
        response = client.post(
            "/api/login",
            json={
                "username": "nonexistent",
                "password": "SomePassword123"
            }
        )

        assert response.status_code == 401
        assert "detail" in response.json()

    def test_login_wrong_password(self, client, test_user):
        """Test login with correct username but wrong password."""
        response = client.post(
            "/api/login",
            json={
                "username": test_user["username"],
                "password": "WrongPassword123"
            }
        )

        assert response.status_code == 401
        assert "detail" in response.json()

    def test_login_missing_username(self, client):
        """Test login request with missing username."""
        response = client.post(
            "/api/login",
            json={"password": "SomePassword123"}
        )

        assert response.status_code == 422  # Validation error

    def test_login_missing_password(self, client):
        """Test login request with missing password."""
        response = client.post(
            "/api/login",
            json={"username": "testuser"}
        )

        assert response.status_code == 422  # Validation error

    def test_login_empty_credentials(self, client):
        """Test login with empty username and password."""
        response = client.post(
            "/api/login",
            json={
                "username": "",
                "password": ""
            }
        )

        assert response.status_code == 401
