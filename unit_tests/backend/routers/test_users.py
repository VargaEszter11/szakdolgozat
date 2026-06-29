import pytest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

from fastapi import HTTPException

import routers.users as users_router

@pytest.fixture
def db():
    return MagicMock()

def test_create_user_username_exists(db):
    request = MagicMock(username="john", email="john@test.com")

    with patch("routers.users.crud.get_user_by_username", return_value=True):
        with pytest.raises(HTTPException) as exc:
            users_router.create_user(request, db)

    assert exc.value.status_code == 400


def test_create_user_email_exists(db):
    request = MagicMock(username="john", email="john@test.com")

    with patch("routers.users.crud.get_user_by_username", return_value=None), \
         patch("routers.users.crud.get_user_by_email", return_value=True):

        with pytest.raises(HTTPException):
            users_router.create_user(request, db)


def test_create_user_success(db):
    request = MagicMock(username="john", email="john@test.com")

    with patch("routers.users.crud.get_user_by_username", return_value=None), \
         patch("routers.users.crud.get_user_by_email", return_value=None), \
         patch("routers.users.crud.create_user", return_value={"id": 1}):

        result = users_router.create_user(request, db)

    assert result is not None

def test_get_user_not_found(db):
    with patch("routers.users.crud.get_user", return_value=None):
        with pytest.raises(HTTPException):
            users_router.get_user(1, db)


def test_get_user_success(db):
    user = {"id": 1}

    with patch("routers.users.crud.get_user", return_value=user):
        result = users_router.get_user(1, db)

    assert result == user

def test_list_users(db):
    with patch("routers.users.crud.get_users", return_value=[1, 2, 3]):
        result = users_router.list_users(skip=0, limit=10, db=db)

    assert result == [1, 2, 3]

def test_update_user_username_taken(db):
    user_update = MagicMock(username="newname", email=None)

    with patch("routers.users.crud.get_user_by_username", return_value=SimpleNamespace(id=99)):
        with pytest.raises(HTTPException):
            users_router.update_user(1, user_update, db)


def test_update_user_email_taken(db):
    user_update = MagicMock(username=None, email="x@test.com")

    with patch("routers.users.crud.get_user_by_username", return_value=None), \
         patch("routers.users.crud.get_user_by_email", return_value=SimpleNamespace(id=99)):

        with pytest.raises(HTTPException):
            users_router.update_user(1, user_update, db)


def test_update_user_not_found(db):
    user_update = MagicMock(username=None, email=None)

    with patch("routers.users.crud.get_user_by_username", return_value=None), \
         patch("routers.users.crud.get_user_by_email", return_value=None), \
         patch("routers.users.crud.update_user", return_value=None):

        with pytest.raises(HTTPException):
            users_router.update_user(1, user_update, db)


def test_update_user_success(db):
    user_update = MagicMock(username=None, email=None)

    with patch("routers.users.crud.get_user_by_username", return_value=None), \
         patch("routers.users.crud.get_user_by_email", return_value=None), \
         patch("routers.users.crud.update_user", return_value={"id": 1}):

        result = users_router.update_user(1, user_update, db)

    assert result == {"id": 1}

def test_delete_user_not_found(db):
    with patch("routers.users.crud.delete_user", return_value=False):
        with pytest.raises(HTTPException):
            users_router.delete_user(1, db)


def test_delete_user_success(db):
    with patch("routers.users.crud.delete_user", return_value=True):
        result = users_router.delete_user(1, db)

    assert result is None

def test_get_user_visited_places(db):
    place = SimpleNamespace(
        id=1,
        user_id=1,
        place_name="Paris",
        country="FR",
        date=None,
        rating=None,
        description=None,
        photo_path="legacy.jpg",
        latitude=None,
        longitude=None,
        images=[],
    )

    with patch("routers.users.crud.get_user", return_value=True), \
         patch("routers.users.crud.get_user_visited_places", return_value=[place]):

        result = users_router.get_user_visited_places(1, db)

    assert isinstance(result, list)
    assert len(result) == 1

def test_get_user_planned_trips(db):
    with patch("routers.users.crud.get_user", return_value=True), \
         patch("routers.users.crud.get_user_planned_trips", return_value=[{"id": 1}]):

        result = users_router.get_user_planned_trips(1, db)

    assert result == [{"id": 1}]