"""Unit tests for off-airport typed place access."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.travel_types import place_access as pa


@pytest.mark.asyncio
async def test_resolve_direct_ground_when_close(monkeypatch):
    origin = SimpleNamespace(iata="BUD", latitude=47.44, longitude=19.26, country_code="HU")
    db = MagicMock()

    monkeypatch.setattr(pa, "_airport_by_iata", lambda database, iata: origin)
    monkeypatch.setattr(pa, "_has_coordinates", lambda airport: True)
    monkeypatch.setattr(pa, "geocode_place", AsyncMock(return_value=(47.5, 19.1)))
    monkeypatch.setattr(
        pa,
        "nearest_airport",
        AsyncMock(return_value={"iata": "BUD", "city": "Budapest", "country": "HU", "distance_km": 10}),
    )
    monkeypatch.setattr(pa, "can_use_ground_transport", lambda a, b: True)

    result = await pa.resolve_place_access(
        db,
        "Szentendre",
        current_airport="BUD",
        preferred_transport="allModes",
    )

    assert result is not None
    assert result["kind"] == "direct_ground"
    assert result["city"] == "Szentendre"
    assert result["transport"] in {"bus", "train"}
    assert result["off_airport"] is True


@pytest.mark.asyncio
async def test_resolve_via_airport_when_far(monkeypatch):
    origin = SimpleNamespace(iata="BUD", latitude=47.44, longitude=19.26, country_code="HU")
    access = SimpleNamespace(iata="SZG", latitude=47.79, longitude=13.0, country_code="AT")
    db = MagicMock()

    monkeypatch.setattr(
        pa,
        "_airport_by_iata",
        lambda database, iata: origin if iata == "BUD" else access,
    )
    monkeypatch.setattr(pa, "_has_coordinates", lambda airport: True)
    # ~400+ km away so not "close" from BUD for the test — use far coords
    monkeypatch.setattr(pa, "geocode_place", AsyncMock(return_value=(47.56, 13.65)))  # Hallstatt-ish
    monkeypatch.setattr(
        pa,
        "nearest_airport",
        AsyncMock(return_value={"iata": "SZG", "city": "Salzburg", "country": "AT", "distance_km": 50}),
    )

    # Force "not worth direct ground from current" by failing ground-area check from BUD,
    # while access airport remains close enough for transfer.
    def fake_ground(a, b):
        return getattr(a, "iata", None) == "SZG"

    monkeypatch.setattr(pa, "can_use_ground_transport", fake_ground)
    monkeypatch.setattr(pa, "calculate_distance_km", lambda *args: 500.0)

    # Override distance specifically for transfer calculation after nearest is chosen:
    distances = iter([700.0, 40.0])  # from current too far; from access ok

    def distance_side_effect(*args):
        return next(distances)

    monkeypatch.setattr(pa, "calculate_distance_km", distance_side_effect)
    monkeypatch.setattr(pa, "can_use_ground_transport", lambda a, b: True)

    result = await pa.resolve_place_access(
        db,
        "Hallstatt",
        current_airport="BUD",
        preferred_transport="allModes",
    )

    assert result is not None
    assert result["kind"] == "via_airport"
    assert result["access_iata"] == "SZG"
    assert result["ground_transfer"]["city"] == "Hallstatt"
    assert result["ground_transfer"]["transport"] in {"bus", "train"}


@pytest.mark.asyncio
async def test_resolve_none_when_train_bus_but_too_far(monkeypatch):
    origin = SimpleNamespace(iata="BUD", latitude=47.44, longitude=19.26, country_code="HU")
    db = MagicMock()

    monkeypatch.setattr(pa, "_airport_by_iata", lambda database, iata: origin)
    monkeypatch.setattr(pa, "_has_coordinates", lambda airport: True)
    monkeypatch.setattr(pa, "geocode_place", AsyncMock(return_value=(41.9, 12.5)))
    monkeypatch.setattr(
        pa,
        "nearest_airport",
        AsyncMock(return_value={"iata": "FCO", "city": "Rome", "country": "IT", "distance_km": 20}),
    )
    monkeypatch.setattr(pa, "calculate_distance_km", lambda *args: 900.0)
    monkeypatch.setattr(pa, "can_use_ground_transport", lambda a, b: True)

    result = await pa.resolve_place_access(
        db,
        "Somewhere remote",
        current_airport="BUD",
        preferred_transport="trainBus",
    )

    assert result is None


@pytest.mark.asyncio
async def test_resolve_none_for_flight_only_off_airport(monkeypatch):
    origin = SimpleNamespace(iata="BUD", latitude=47.44, longitude=19.26, country_code="HU")
    access = SimpleNamespace(iata="SZG", latitude=47.79, longitude=13.0, country_code="AT")
    db = MagicMock()

    monkeypatch.setattr(
        pa,
        "_airport_by_iata",
        lambda database, iata: origin if iata == "BUD" else access,
    )
    monkeypatch.setattr(pa, "_has_coordinates", lambda airport: True)
    monkeypatch.setattr(pa, "geocode_place", AsyncMock(return_value=(47.56, 13.65)))
    monkeypatch.setattr(
        pa,
        "nearest_airport",
        AsyncMock(return_value={"iata": "SZG", "city": "Salzburg", "country": "AT", "distance_km": 50}),
    )
    monkeypatch.setattr(pa, "calculate_distance_km", lambda *args: 400.0)
    monkeypatch.setattr(pa, "can_use_ground_transport", lambda a, b: True)

    result = await pa.resolve_place_access(
        db,
        "Hallstatt",
        current_airport="BUD",
        preferred_transport="flight",
    )

    assert result is None


def test_candidates_for_unmatched_places_direct_and_via():
    resolutions = [
        {
            "kind": "direct_ground",
            "city": "Szentendre",
            "country": "HU",
            "iata": "BUD",
            "transport": "bus",
            "distance_km": 20,
            "requested_place": "Szentendre",
            "off_airport": True,
        },
        {
            "kind": "via_airport",
            "access_iata": "SZG",
            "access_city": "Salzburg",
            "access_country": "AT",
            "requested_place": "Hallstatt",
            "ground_transfer": {
                "city": "Hallstatt",
                "country": "AT",
                "iata": "SZG",
                "transport": "bus",
                "distance_km": 70,
                "requested_place": "Hallstatt",
                "off_airport": True,
            },
        },
    ]

    out = pa.candidates_for_unmatched_places(
        resolutions,
        reachable_iatas={"SZG", "VIE"},
        current_airport="BUD",
    )

    assert any(item.get("city") == "Szentendre" and item.get("off_airport") for item in out)
    via = next(item for item in out if item.get("via_place_access"))
    assert via["iata"] == "SZG"
    assert via["ground_transfer"]["city"] == "Hallstatt"


def test_candidates_skips_unreachable_access_airport():
    resolutions = [
        {
            "kind": "via_airport",
            "access_iata": "SZG",
            "access_city": "Salzburg",
            "access_country": "AT",
            "requested_place": "Hallstatt",
            "ground_transfer": {
                "city": "Hallstatt",
                "country": "AT",
                "iata": "SZG",
                "transport": "bus",
                "requested_place": "Hallstatt",
            },
        }
    ]

    out = pa.candidates_for_unmatched_places(
        resolutions,
        reachable_iatas={"VIE"},
        current_airport="BUD",
    )

    assert out == []


def test_home_hub_transfer_from_coords_when_far(monkeypatch):
    hub = SimpleNamespace(
        iata="KSC",
        city="Kosice",
        country_code="SK",
        latitude=48.66,
        longitude=21.24,
    )
    db = MagicMock()
    monkeypatch.setattr(pa, "_airport_by_iata", lambda database, iata: hub)
    monkeypatch.setattr(pa, "_has_coordinates", lambda airport: True)
    monkeypatch.setattr(pa, "can_use_ground_transport", lambda a, b: True)

    # Miskolc-ish coordinates (~70km from KSC)
    result = pa.home_hub_transfer_from_coords(
        db,
        home_lat=48.10,
        home_lon=20.79,
        hub_iata="KSC",
        preferred_transport="allModes",
    )
    assert result is not None
    assert result["access_city"] == "Kosice"
    assert result["local_transport"] in {"bus", "train"}
    assert result["distance_km"] >= 25


def test_home_hub_transfer_none_when_close(monkeypatch):
    hub = SimpleNamespace(
        iata="BUD",
        city="Budapest",
        country_code="HU",
        latitude=47.44,
        longitude=19.26,
    )
    db = MagicMock()
    monkeypatch.setattr(pa, "_airport_by_iata", lambda database, iata: hub)
    monkeypatch.setattr(pa, "_has_coordinates", lambda airport: True)
    monkeypatch.setattr(pa, "can_use_ground_transport", lambda a, b: True)

    result = pa.home_hub_transfer_from_coords(
        db,
        home_lat=47.50,
        home_lon=19.05,
        hub_iata="BUD",
        preferred_transport="allModes",
    )
    assert result is None
