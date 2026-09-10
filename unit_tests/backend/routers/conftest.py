"""Shared auth overrides for router unit tests."""

from typing import Any, cast

import pytest

from utils.auth_deps import create_access_token, get_current_user

from .auth_test_utils import fake_user


@pytest.fixture
def auth_user():
    return fake_user()


@pytest.fixture
def auth_headers(auth_user):
    user = cast(Any, auth_user)
    token = create_access_token(user_id=int(user.id), username=str(user.username))
    return {"Authorization": f"Bearer {token}"}


def install_auth_override(app, user=None):
    current = user or fake_user()
    app.dependency_overrides[get_current_user] = lambda: current
    return current
