import pytest
from sqlalchemy.orm import Session
from typing import cast

from backend.utils.direct_destinations_cache import get_direct_destinations_cached


def fake_session() -> Session:
    return cast(Session, object())


@pytest.mark.asyncio
async def test_get_direct_destinations_cached_returns_empty_list_when_db_is_none():
    result = await get_direct_destinations_cached(None, "BUD")

    assert result == []


@pytest.mark.asyncio
async def test_get_direct_destinations_cached_returns_empty_list_when_origin_is_empty():
    result = await get_direct_destinations_cached(None, "")

    assert result == []


@pytest.mark.asyncio
async def test_get_direct_destinations_cached_strips_and_uppercases_origin_code(monkeypatch):
    fake_db = fake_session()
    destinations = [
        {"iata": "FCO", "city": "Rome"},
        {"iata": "CDG", "city": "Paris"},
    ]

    called_with = {}

    def fake_list_active_destinations_from_origin(db, code):
        called_with["db"] = db
        called_with["code"] = code
        return destinations

    monkeypatch.setattr(
        "database.crud.list_active_destinations_from_origin",
        fake_list_active_destinations_from_origin,
    )

    result = await get_direct_destinations_cached(fake_db, " bud ")

    assert result == destinations
    assert called_with["db"] is fake_db
    assert called_with["code"] == "BUD"

@pytest.mark.asyncio
async def test_get_direct_destinations_cached_returns_empty_list_when_crud_raises(monkeypatch):
    fake_db = fake_session()

    def fake_list_active_destinations_from_origin(db, code):
        raise RuntimeError("database error")

    monkeypatch.setattr(
        "database.crud.list_active_destinations_from_origin",
        fake_list_active_destinations_from_origin,
    )

    result = await get_direct_destinations_cached(fake_db, "BUD")

    assert result == []