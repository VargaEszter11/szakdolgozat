"""Helpers for authenticated TestClient / direct router calls in unit tests."""

from typing import Any

from database import models
from utils.auth_deps import get_current_user


def fake_user(
    user_id: int = 1, username: str = "testuser", email: str = "t@example.com"
) -> models.User:
    return models.User(
        id=user_id,
        username=username,
        email=email,
        password="unused",
        email_verified=True,
    )


def override_current_user(app, user: Any = None, *, dependency=get_current_user):
    """Override get_current_user on a FastAPI app for unit tests."""
    current = user or fake_user()
    app.dependency_overrides[dependency] = lambda: current
    return current
