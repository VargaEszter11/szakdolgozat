"""Shared auth overrides for router unit tests."""

from types import SimpleNamespace

import pytest

from utils.auth_deps import create_access_token, get_current_user


def fake_user(user_id: int = 1, username: str = "testuser", email: str = "t@example.com"):
    return SimpleNamespace(id=user_id, username=username, email=email)


@pytest.fixture
def auth_user():
    return fake_user()


@pytest.fixture
def auth_headers(auth_user):
    token = create_access_token(user_id=int(auth_user.id), username=str(auth_user.username))
    return {"Authorization": f"Bearer {token}"}


def install_auth_override(app, user=None):
    current = user or fake_user()
    app.dependency_overrides[get_current_user] = lambda: current
    return current
