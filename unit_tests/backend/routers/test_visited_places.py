import asyncio

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

import routers.visited_places as vp

@pytest.fixture
def db():
    return MagicMock()

@pytest.mark.asyncio
async def test_create_visited_place_user_not_found(db):
    place = MagicMock(user_id=1, place_name="Budapest", country="HU")

    with patch("routers.visited_places.crud.get_user", return_value=None):
        with pytest.raises(HTTPException) as exc:
            await vp.create_visited_place(place, db)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_create_visited_place_geocode_success(db):
    place = MagicMock(user_id=1, place_name="Budapest", country="HU")
    place.model_dump.return_value = {
        "user_id": 1,
        "place_name": "Budapest",
        "country": "HU",
    }

    with patch("routers.visited_places.crud.get_user", return_value=True), \
         patch("routers.visited_places.geocode_place", return_value=(47.5, 19.0)), \
         patch("routers.visited_places.crud.create_visited_place", return_value={"id": 1}) as create_mock:

        result = await vp.create_visited_place(place, db)

    assert result == {"id": 1}
    create_mock.assert_called_once()


@pytest.mark.asyncio
async def test_create_visited_place_geocode_failure(db):
    place = MagicMock(user_id=1, place_name="Budapest", country="HU")

    with patch("routers.visited_places.crud.get_user", return_value=True), \
         patch("routers.visited_places.geocode_place", side_effect=Exception("fail")), \
         patch("routers.visited_places.crud.create_visited_place", return_value={"id": 1}) as create_mock:

        result = await vp.create_visited_place(place, db)

    assert result == {"id": 1}
    create_mock.assert_called_once()

def test_get_visited_place_not_found(db):
    with patch("routers.visited_places.crud.get_visited_place", return_value=None):
        with pytest.raises(HTTPException):
            vp.get_visited_place(1, db)


def test_get_visited_place_success(db):
    place = {"id": 1}

    with patch("routers.visited_places.crud.get_visited_place", return_value=place):
        result = vp.get_visited_place(1, db)

    assert result == place

def test_list_visited_places_by_user_not_found(db):
    with patch("routers.visited_places.crud.get_user", return_value=None):
        with pytest.raises(HTTPException):
            vp.list_visited_places(user_id=1, skip=0, limit=10, db=db)


def test_list_visited_places_by_user(db):
    with patch("routers.visited_places.crud.get_user", return_value=True), \
         patch("routers.visited_places.crud.get_user_visited_places", return_value=[1, 2]):

        result = vp.list_visited_places(user_id=1, skip=0, limit=10, db=db)

    assert result == [1, 2]


def test_list_visited_places_all(db):
    with patch("routers.visited_places.crud.get_visited_places", return_value=[3, 4]):

        result = vp.list_visited_places(user_id=None, skip=0, limit=10, db=db)

    assert result == [3, 4]

def test_update_visited_place_not_found(db):
    with patch("routers.visited_places.crud.update_visited_place", return_value=None):
        with pytest.raises(HTTPException):
            vp.update_visited_place(1, MagicMock(), db)


def test_update_visited_place_success(db):
    with patch("routers.visited_places.crud.update_visited_place", return_value={"id": 1}):
        result = vp.update_visited_place(1, MagicMock(), db)

    assert result == {"id": 1}

def test_delete_visited_place_not_found(db):
    with patch("routers.visited_places.crud.delete_visited_place", return_value=False):
        with pytest.raises(HTTPException):
            vp.delete_visited_place(1, db)


def test_delete_visited_place_success(db):
    with patch("routers.visited_places.crud.delete_visited_place", return_value=True):
        result = vp.delete_visited_place(1, db)

    assert result is None

def test_create_place_image_not_found(db):
    body = MagicMock(image_path="x.jpg")

    with patch("routers.visited_places.crud.get_visited_place", return_value=None):
        with pytest.raises(HTTPException):
            vp.create_place_image(1, body, db)


def test_create_place_image_success(db):
    body = MagicMock(image_path="x.jpg")

    with patch("routers.visited_places.crud.get_visited_place", return_value=True), \
         patch("routers.visited_places.crud.create_image", return_value={"id": 1}) as create_mock:

        result = vp.create_place_image(1, body, db)

    assert result == {"id": 1}
    create_mock.assert_called_once()

@pytest.mark.asyncio
async def test_upload_place_image_success(db):
    file = MagicMock()
    file.read = MagicMock(return_value=asyncio.Future())
    file.read.return_value.set_result(b"img")
    file.content_type = "image/png"

    with patch("routers.visited_places.crud.get_visited_place", return_value=True), \
         patch("routers.visited_places.save_place_image", return_value="uploads/x.png"), \
         patch("routers.visited_places.crud.create_image", return_value={"id": 1}):

        result = await vp.upload_place_image(1, file, db)

    assert result == {"id": 1}


@pytest.mark.asyncio
async def test_upload_place_image_invalid(db):
    file = MagicMock()
    file.read = MagicMock(return_value=asyncio.Future())
    file.read.return_value.set_result(b"img")

    with patch("routers.visited_places.crud.get_visited_place", return_value=True), \
         patch("routers.visited_places.save_place_image", side_effect=ValueError("bad file")):

        with pytest.raises(HTTPException):
            await vp.upload_place_image(1, file, db)

def test_list_place_images(db):
    with patch("routers.visited_places.crud.get_visited_place", return_value=True), \
         patch("routers.visited_places.crud.get_images", return_value=[1, 2]):

        result = vp.list_place_images(1, db)

    assert result == [1, 2]

def test_read_image_not_found(db):
    with patch("routers.visited_places.crud.get_image", return_value=None):
        with pytest.raises(HTTPException):
            vp.read_image(1, db)


def test_read_image_success(db):
    with patch("routers.visited_places.crud.get_image", return_value={"id": 1}):
        result = vp.read_image(1, db)

    assert result == {"id": 1}

def test_update_place_image(db):
    with patch("routers.visited_places.crud.update_image", return_value={"id": 1}):
        result = vp.update_place_image(1, MagicMock(), db)

    assert result == {"id": 1}


def test_update_place_image_not_found(db):
    with patch("routers.visited_places.crud.update_image", return_value=None):
        with pytest.raises(HTTPException):
            vp.update_place_image(1, MagicMock(), db)

def test_delete_place_image_success(db):
    with patch("routers.visited_places.crud.delete_image", return_value=True):
        result = vp.delete_place_image(1, db)

    assert result is None


def test_delete_place_image_not_found(db):
    with patch("routers.visited_places.crud.delete_image", return_value=False):
        with pytest.raises(HTTPException):
            vp.delete_place_image(1, db)