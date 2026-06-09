import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

import main  # your FastAPI app


client = TestClient(main.app)

@patch("routers.auth.crud.get_user_by_username")
@patch("routers.auth.crud.get_user_by_email")
@patch("routers.auth.crud.create_user")
def test_register_success(mock_create, mock_get_email, mock_get_username):
    mock_get_username.return_value = None
    mock_get_email.return_value = None

    response = client.post(
        "/api/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "secret123"
        }
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "registered" in response.json()["message"].lower()


@patch("routers.auth.crud.get_user_by_username")
def test_register_username_exists(mock_get_username):
    mock_get_username.return_value = MagicMock()

    response = client.post(
        "/api/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "secret123"
        }
    )

    assert response.status_code == 400


@patch("routers.auth.crud.get_user_by_username")
@patch("routers.auth.crud.get_user_by_email")
def test_register_email_exists(mock_get_email, mock_get_username):
    mock_get_username.return_value = None
    mock_get_email.return_value = MagicMock()

    response = client.post(
        "/api/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "secret123"
        }
    )

    assert response.status_code == 400

@patch("routers.auth.crud.get_user_by_username")
@patch("routers.auth.crud.verify_password")
def test_login_success(mock_verify, mock_get_user):
    mock_get_user.return_value = MagicMock(id=1, username="testuser", password="hashed")
    mock_verify.return_value = True

    response = client.post(
        "/api/login",
        json={
            "username": "testuser",
            "password": "secret123"
        }
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["username"] == "testuser"


@patch("routers.auth.crud.get_user_by_username")
def test_login_user_not_found(mock_get_user):
    mock_get_user.return_value = None

    response = client.post(
        "/api/login",
        json={
            "username": "wrong",
            "password": "secret"
        }
    )

    assert response.status_code == 401


@patch("routers.auth.crud.get_user_by_username")
@patch("routers.auth.crud.verify_password")
def test_login_wrong_password(mock_verify, mock_get_user):
    mock_get_user.return_value = MagicMock(id=1, username="testuser", password="hashed")
    mock_verify.return_value = False

    response = client.post(
        "/api/login",
        json={
            "username": "testuser",
            "password": "wrong"
        }
    )

    assert response.status_code == 401

@patch("routers.auth.get_google_client_id")
def test_google_login_not_configured(mock_client_id):
    mock_client_id.return_value = ""

    response = client.post(
        "/api/google-login",
        json={"credential": "fake-token"}
    )

    assert response.status_code == 500


@patch("routers.auth.get_google_client_id")
@patch("routers.auth.id_token.verify_oauth2_token")
def test_google_login_invalid_token(mock_verify_token, mock_client_id):
    mock_client_id.return_value = "client-id"
    mock_verify_token.side_effect = Exception("invalid")

    response = client.post(
        "/api/google-login",
        json={"credential": "bad-token"}
    )

    assert response.status_code == 401


@patch("routers.auth.get_google_client_id")
@patch("routers.auth.id_token.verify_oauth2_token")
def test_google_login_unverified_email(mock_verify_token, mock_client_id):
    mock_client_id.return_value = "client-id"
    mock_verify_token.return_value = {
        "email_verified": False,
        "email": "test@example.com"
    }

    response = client.post(
        "/api/google-login",
        json={"credential": "token"}
    )

    assert response.status_code == 401


@patch("routers.auth.get_google_client_id")
@patch("routers.auth.id_token.verify_oauth2_token")
@patch("routers.auth.crud.get_user_by_email")
@patch("routers.auth.crud.create_google_user")
def test_google_login_create_user(
    mock_create,
    mock_get_email,
    mock_verify_token,
    mock_client_id
):
    mock_client_id.return_value = "client-id"
    mock_verify_token.return_value = {
        "email_verified": True,
        "email": "test@example.com",
        "name": "Test User"
    }

    mock_get_email.return_value = None
    mock_create.return_value = MagicMock(id=1, username="google_user")

    response = client.post(
        "/api/google-login",
        json={"credential": "valid-token"}
    )

    assert response.status_code == 200
    assert response.json()["success"] is True

@patch("routers.auth.get_google_client_id")
def test_google_config(mock_client_id):
    mock_client_id.return_value = "abc123"

    response = client.get("/api/google-config")

    assert response.status_code == 200
    assert response.json()["client_id"] == "abc123"

@patch("routers.auth.crud.get_user_by_username")
def test_forgot_password_verify_success(mock_get_user):
    mock_get_user.return_value = MagicMock(id=1, email="a@b.com")

    response = client.post(
        "/api/forgot-password/verify",
        json={
            "username": "test",
            "email": "a@b.com"
        }
    )

    assert response.status_code == 200
    assert response.json()["success"] is True


@patch("routers.auth.crud.get_user_by_username")
def test_forgot_password_verify_fail(mock_get_user):
    mock_get_user.return_value = None

    response = client.post(
        "/api/forgot-password/verify",
        json={
            "username": "test",
            "email": "wrong@b.com"
        }
    )

    assert response.status_code == 404

@patch("routers.auth.crud.update_user")
def test_forgot_password_reset_success(mock_update):
    mock_update.return_value = MagicMock(id=1)

    response = client.post(
        "/api/forgot-password/reset",
        json={
            "user_id": 1,
            "new_password": "newsecret"
        }
    )

    assert response.status_code == 200
    assert response.json()["success"] is True


@patch("routers.auth.crud.update_user")
def test_forgot_password_reset_user_not_found(mock_update):
    mock_update.return_value = None

    response = client.post(
        "/api/forgot-password/reset",
        json={
            "user_id": 999,
            "new_password": "newsecret"
        }
    )

    assert response.status_code == 404