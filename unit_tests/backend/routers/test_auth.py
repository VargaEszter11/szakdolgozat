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
    assert response.json().get("access_token")
    assert response.json().get("token_type") == "bearer"


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

@patch("routers.auth.get_google_client_secret")
@patch("routers.auth.get_google_client_id")
def test_google_login_not_configured(mock_client_id, mock_client_secret):
    mock_client_id.return_value = ""
    mock_client_secret.return_value = ""

    response = client.post(
        "/api/google-login",
        json={"code": "fake-code"}
    )

    assert response.status_code == 500


@patch("routers.auth.get_google_client_secret")
@patch("routers.auth.get_google_client_id")
@patch("routers.auth._exchange_google_code")
def test_google_login_invalid_code(mock_exchange, mock_client_id, mock_client_secret):
    mock_client_id.return_value = "client-id"
    mock_client_secret.return_value = "client-secret"
    mock_exchange.side_effect = Exception("exchange failed")

    response = client.post(
        "/api/google-login",
        json={"code": "bad-code"}
    )

    assert response.status_code == 401


@patch("routers.auth.get_google_client_secret")
@patch("routers.auth.get_google_client_id")
@patch("routers.auth._exchange_google_code")
@patch("routers.auth.id_token.verify_oauth2_token")
def test_google_login_invalid_token(
    mock_verify_token, mock_exchange, mock_client_id, mock_client_secret
):
    mock_client_id.return_value = "client-id"
    mock_client_secret.return_value = "client-secret"
    mock_exchange.return_value = {"id_token": "bad-token"}
    mock_verify_token.side_effect = Exception("invalid")

    response = client.post(
        "/api/google-login",
        json={"code": "some-code"}
    )

    assert response.status_code == 401


@patch("routers.auth.get_google_client_secret")
@patch("routers.auth.get_google_client_id")
@patch("routers.auth._exchange_google_code")
@patch("routers.auth.id_token.verify_oauth2_token")
def test_google_login_unverified_email(
    mock_verify_token, mock_exchange, mock_client_id, mock_client_secret
):
    mock_client_id.return_value = "client-id"
    mock_client_secret.return_value = "client-secret"
    mock_exchange.return_value = {"id_token": "some-token"}
    mock_verify_token.return_value = {
        "email_verified": False,
        "email": "test@example.com"
    }

    response = client.post(
        "/api/google-login",
        json={"code": "some-code"}
    )

    assert response.status_code == 401


@patch("routers.auth.get_google_client_secret")
@patch("routers.auth.get_google_client_id")
@patch("routers.auth._exchange_google_code")
@patch("routers.auth.id_token.verify_oauth2_token")
@patch("routers.auth.crud.get_user_by_email")
@patch("routers.auth.crud.create_google_user")
def test_google_login_create_user(
    mock_create,
    mock_get_email,
    mock_verify_token,
    mock_exchange,
    mock_client_id,
    mock_client_secret,
):
    mock_client_id.return_value = "client-id"
    mock_client_secret.return_value = "client-secret"
    mock_exchange.return_value = {"id_token": "some-token"}
    mock_verify_token.return_value = {
        "email_verified": True,
        "email": "test@example.com",
        "name": "Test User",
        "picture": "https://example.com/avatar.png"
    }

    mock_get_email.return_value = None
    mock_create.return_value = MagicMock(id=1, username="google_user")

    response = client.post(
        "/api/google-login",
        json={"code": "valid-code"}
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["avatar_url"] == "https://example.com/avatar.png"
    assert response.json().get("access_token")
    assert response.json().get("token_type") == "bearer"
    assert response.json().get("access_token")

@patch("routers.auth.get_google_client_id")
def test_google_config(mock_client_id):
    mock_client_id.return_value = "abc123"

    response = client.get("/api/google-config")

    assert response.status_code == 200
    assert response.json()["client_id"] == "abc123"

@patch("routers.auth.send_password_reset_email")
@patch("routers.auth.crud.create_password_reset_token")
@patch("routers.auth.crud.get_user_by_email")
def test_forgot_password_request_known_email(mock_get_email, mock_create_token, mock_send_email):
    mock_get_email.return_value = MagicMock(id=1, email="a@b.com")
    mock_create_token.return_value = "raw-token"

    response = client.post(
        "/api/forgot-password/request",
        json={"email": "a@b.com"}
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    mock_create_token.assert_called_once()
    mock_send_email.assert_called_once()


@patch("routers.auth.send_password_reset_email")
@patch("routers.auth.crud.create_password_reset_token")
@patch("routers.auth.crud.get_user_by_email")
def test_forgot_password_request_unknown_email_still_returns_generic_success(
    mock_get_email, mock_create_token, mock_send_email
):
    mock_get_email.return_value = None

    response = client.post(
        "/api/forgot-password/request",
        json={"email": "nobody@example.com"}
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    mock_create_token.assert_not_called()
    mock_send_email.assert_not_called()


@patch("routers.auth.crud.consume_password_reset_token")
@patch("routers.auth.crud.update_user_password")
@patch("routers.auth.crud.get_valid_password_reset_token")
def test_forgot_password_reset_success(mock_get_token, mock_update, mock_consume):
    mock_get_token.return_value = MagicMock(user_id=1)
    mock_update.return_value = MagicMock(id=1)

    response = client.post(
        "/api/forgot-password/reset",
        json={
            "token": "valid-token",
            "new_password": "newsecret"
        }
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    mock_consume.assert_called_once()


@patch("routers.auth.crud.get_valid_password_reset_token")
def test_forgot_password_reset_invalid_token(mock_get_token):
    mock_get_token.return_value = None

    response = client.post(
        "/api/forgot-password/reset",
        json={
            "token": "bad-token",
            "new_password": "newsecret"
        }
    )

    assert response.status_code == 400