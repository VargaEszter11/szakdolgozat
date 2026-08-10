import asyncio

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from types import SimpleNamespace

import routers.visited_places as vp
from .auth_test_utils import fake_user


@pytest.fixture
def db():
    return MagicMock()


def owned_place(**overrides):
    data = {"id": 1, "user_id": 1, "place_name": "Budapest", "country": "HU"}
    data.update(overrides)
    return SimpleNamespace(**data)


@pytest.mark.asyncio
async def test_create_visited_place_geocode_success(db):
    place = MagicMock(user_id=1, place_name="Budapest", country="HU")
    place.model_dump.return_value = {
        "user_id": 1,
        "place_name": "Budapest",
        "country": "HU",
    }

    with patch("routers.visited_places.geocode_place", return_value=(47.5, 19.0)), \
         patch("routers.visited_places.crud.create_visited_place", return_value={"id": 1}) as create_mock:

        result = await vp.create_visited_place(place, db, fake_user(1))

    assert result == {"id": 1}
    create_mock.assert_called_once()


@pytest.mark.asyncio
async def test_create_visited_place_geocode_failure(db):
    place = MagicMock(user_id=1, place_name="Budapest", country="HU")
    place.model_dump.return_value = {
        "user_id": 1,
        "place_name": "Budapest",
        "country": "HU",
    }

    with patch("routers.visited_places.geocode_place", side_effect=Exception("fail")), \
         patch("routers.visited_places.crud.create_visited_place", return_value={"id": 1}) as create_mock:

        result = await vp.create_visited_place(place, db, fake_user(1))

    assert result == {"id": 1}
    create_mock.assert_called_once()


def test_get_visited_place_not_found(db):
    with patch("routers.visited_places.crud.get_visited_place", return_value=None):
        with pytest.raises(HTTPException) as exc:
            vp.get_visited_place(1, db, fake_user(1))

    assert exc.value.status_code == 404


def test_get_visited_place_success(db):
    place = owned_place()

    with patch("routers.visited_places.crud.get_visited_place", return_value=place):
        result = vp.get_visited_place(1, db, fake_user(1))

    assert result == place


def test_list_visited_places(db):
    with patch("routers.visited_places.crud.get_user_visited_places", return_value=[1, 2]):
        result = vp.list_visited_places(skip=0, limit=10, db=db, current_user=fake_user(1))

    assert result == [1, 2]


def test_update_visited_place_not_found(db):
    with patch("routers.visited_places.crud.get_visited_place", return_value=None):
        with pytest.raises(HTTPException) as exc:
            vp.update_visited_place(1, MagicMock(), db, fake_user(1))

    assert exc.value.status_code == 404


def test_update_visited_place_success(db):
    with patch("routers.visited_places.crud.get_visited_place", return_value=owned_place()), \
         patch("routers.visited_places.crud.update_visited_place", return_value={"id": 1}):
        result = vp.update_visited_place(1, MagicMock(), db, fake_user(1))

    assert result == {"id": 1}


def test_delete_visited_place_not_found(db):
    with patch("routers.visited_places.crud.get_visited_place", return_value=None):
        with pytest.raises(HTTPException) as exc:
            vp.delete_visited_place(1, db, fake_user(1))

    assert exc.value.status_code == 404


def test_delete_visited_place_success(db):
    with patch("routers.visited_places.crud.get_visited_place", return_value=owned_place()), \
         patch("routers.visited_places.crud.delete_visited_place", return_value=True):
        result = vp.delete_visited_place(1, db, fake_user(1))

    assert result is None


def test_create_place_image_not_found(db):
    body = MagicMock(image_path="x.jpg")

    with patch("routers.visited_places.crud.get_visited_place", return_value=None):
        with pytest.raises(HTTPException):
            vp.create_place_image(1, body, db, fake_user(1))


def test_create_place_image_success(db):
    body = MagicMock(image_path="x.jpg")

    with patch("routers.visited_places.crud.get_visited_place", return_value=owned_place()), \
         patch("routers.visited_places.crud.create_image", return_value={"id": 1}) as create_mock:

        result = vp.create_place_image(1, body, db, fake_user(1))

    assert result == {"id": 1}
    create_mock.assert_called_once()


@pytest.mark.asyncio
async def test_upload_place_image_success(db):
    file = MagicMock()
    file.read = MagicMock(return_value=asyncio.Future())
    file.read.return_value.set_result(b"img")
    file.content_type = "image/png"

    with patch("routers.visited_places.crud.get_visited_place", return_value=owned_place()), \
         patch("routers.visited_places.save_place_image", return_value="uploads/x.png"), \
         patch("routers.visited_places.crud.create_image", return_value={"id": 1}):

        result = await vp.upload_place_image(1, file, db, fake_user(1))

    assert result == {"id": 1}


@pytest.mark.asyncio
async def test_upload_place_image_invalid(db):
    file = MagicMock()
    file.read = MagicMock(return_value=asyncio.Future())
    file.read.return_value.set_result(b"img")

    with patch("routers.visited_places.crud.get_visited_place", return_value=owned_place()), \
         patch("routers.visited_places.save_place_image", side_effect=ValueError("bad file")):

        with pytest.raises(HTTPException):
            await vp.upload_place_image(1, file, db, fake_user(1))


def test_list_place_images(db):
    with patch("routers.visited_places.crud.get_visited_place", return_value=owned_place()), \
         patch("routers.visited_places.crud.get_images", return_value=[1, 2]):

        result = vp.list_place_images(1, db, fake_user(1))

    assert result == [1, 2]


def test_read_image_not_found(db):
    with patch("routers.visited_places.crud.get_image", return_value=None):
        with pytest.raises(HTTPException):
            vp.read_image(1, db, fake_user(1))


def test_read_image_success(db):
    image = SimpleNamespace(id=1, visited_place_id=1)
    with patch("routers.visited_places.crud.get_image", return_value=image), \
         patch("routers.visited_places.crud.get_visited_place", return_value=owned_place()):
        result = vp.read_image(1, db, fake_user(1))

    assert result == image


def test_update_place_image(db):
    image = SimpleNamespace(id=1, visited_place_id=1)
    with patch("routers.visited_places.crud.get_image", return_value=image), \
         patch("routers.visited_places.crud.get_visited_place", return_value=owned_place()), \
         patch("routers.visited_places.crud.update_image", return_value={"id": 1}):
        result = vp.update_place_image(1, MagicMock(), db, fake_user(1))

    assert result == {"id": 1}


def test_update_place_image_not_found(db):
    with patch("routers.visited_places.crud.get_image", return_value=None):
        with pytest.raises(HTTPException):
            vp.update_place_image(1, MagicMock(), db, fake_user(1))


def test_delete_place_image_success(db):
    image = SimpleNamespace(id=1, visited_place_id=1)
    with patch("routers.visited_places.crud.get_image", return_value=image), \
         patch("routers.visited_places.crud.get_visited_place", return_value=owned_place()), \
         patch("routers.visited_places.crud.delete_image", return_value=True):
        result = vp.delete_place_image(1, db, fake_user(1))

    assert result is None


def test_delete_place_image_not_found(db):
    with patch("routers.visited_places.crud.get_image", return_value=None):
        with pytest.raises(HTTPException):
            vp.delete_place_image(1, db, fake_user(1))
