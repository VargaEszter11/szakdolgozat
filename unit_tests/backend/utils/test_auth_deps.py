from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from utils import auth_deps


def test_create_and_decode_access_token(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "unit-test-secret")
    token = auth_deps.create_access_token(user_id=7, username="alice")
    assert isinstance(token, str) and token

    user = SimpleNamespace(id=7, username="alice")
    db = MagicMock()
    monkeypatch.setattr(auth_deps.crud, "get_user", lambda database, user_id: user if user_id == 7 else None)

    creds = SimpleNamespace(credentials=token)
    got = auth_deps.get_current_user(creds=creds, db=db)
    assert got.id == 7


def test_get_current_user_missing_token():
    with pytest.raises(HTTPException) as exc:
        auth_deps.get_current_user(creds=None, db=MagicMock())
    assert exc.value.status_code == 401


def test_require_self_forbidden():
    with pytest.raises(HTTPException) as exc:
        auth_deps.require_self(2, SimpleNamespace(id=1))
    assert exc.value.status_code == 403
