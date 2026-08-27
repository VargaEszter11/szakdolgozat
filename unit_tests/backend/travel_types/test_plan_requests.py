from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from backend.travel_types import plan_requests as pg


def test_travel_length_days_ok_and_invalid():
    assert pg.travel_length_days("2026-07-01", "2026-07-08") == 7
    with pytest.raises(HTTPException) as exc:
        pg.travel_length_days("2026-07-08", "2026-07-01")
    assert exc.value.status_code == 400
    with pytest.raises(HTTPException) as exc_same:
        pg.travel_length_days("2026-07-01", "2026-07-01")
    assert exc_same.value.status_code == 400
    assert "after" in str(exc_same.value.detail).lower()


def test_parse_planner_json():
    assert pg.parse_planner_json('{"ok": true}') == {"ok": True}
    assert pg.parse_planner_json('```json\n{"trips": []}\n```') == {"trips": []}
    assert pg.parse_planner_json("not-json") == {"raw": "not-json"}


def test_set_requested_dates_nested_and_flat():
    nested = {"trips": [{}]}
    out = pg.set_requested_dates(nested, start_date="s", end_date="e", travel_length=3)
    assert out["trips"][0]["startDate"] == "s"
    assert out["trips"][0]["tripLengthDays"] == 3

    flat = {}
    out2 = pg.set_requested_dates(flat, start_date="s", end_date="e", travel_length=2)
    assert out2["endDate"] == "e"
    assert out2["tripLengthDays"] == 2


def test_planner_account_id():
    assert pg.planner_account_id(SimpleNamespace(plannerUserId=9, userId=1)) == 9
    assert pg.planner_account_id(SimpleNamespace(plannerUserId=None, userId=4)) == 4


def test_planner_context(monkeypatch):
    req = SimpleNamespace(startDate="2026-07-01", endDate="2026-07-04", plannerUserId=1, userId=1)
    length, _ = pg.planner_context(req, MagicMock())
    assert length == 3


def test_apply_people_to_booking_links(monkeypatch):
    monkeypatch.setattr(pg, "booking_url", lambda *a, **k: "https://updated")
    plan = {
        "trips": [
            {
                "plan": [
                    {
                        "booking_url": "https://old",
                        "airline_iata": "FR",
                        "origin_airport_iata": "BUD",
                        "destination_airport_iata": "CIA",
                        "arrivalDate": "2026-07-02",
                    },
                    {"city": "X"},
                ]
            }
        ]
    }
    pg.apply_people_to_booking_links(plan, people=2)
    assert plan["trips"][0]["plan"][0]["booking_url"] == "https://updated"
    assert "booking_url" not in plan["trips"][0]["plan"][1]


def test_clean_plan_city_names():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(
        city="Rome",
        name="Rome Fiumicino",
    )
    plan = {"plan": [{"iata": "FCO", "city": "Fiumicino"}, {"city": "NoIata"}]}
    pg.clean_plan_city_names(plan, db)
    assert plan["plan"][0]["city"] == "Rome"
    assert plan["plan"][1]["city"] == "NoIata"


def test_clean_plan_city_names_uses_iata_city_override():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(
        city="Kraków John Paul II International Airport",
        name="Kraków John Paul II International Airport",
    )
    plan = {"plan": [{"iata": "KRK", "city": "Kraków Airport"}]}
    pg.clean_plan_city_names(plan, db)
    assert plan["plan"][0]["city"] == "Krakow"


def test_clean_plan_city_names_prefers_requested_place_on_flight_hub():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(city="Fiumicino")
    plan = {
        "plan": [
            {
                "iata": "FCO",
                "city": "Fiumicino",
                "requested_place": "Rome, Italy",
            }
        ]
    }
    pg.clean_plan_city_names(plan, db)
    assert plan["plan"][0]["city"] == "Rome"
    db.query.assert_not_called()


def test_clean_plan_city_names_keeps_off_airport_place():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(city="Split")
    plan = {
        "plan": [
            {
                "iata": "SPU",
                "city": "Trogir",
                "off_airport": True,
                "requested_place": "trogir",
            }
        ]
    }
    pg.clean_plan_city_names(plan, db)
    assert plan["plan"][0]["city"] == "Trogir"
    db.query.assert_not_called()


def test_clean_plan_city_names_keeps_return_home_place():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(city="Kosice")
    plan = {
        "plan": [
            {
                "iata": "KSC",
                "city": "Miskolc",
                "is_return_home": True,
            }
        ]
    }
    pg.clean_plan_city_names(plan, db)
    assert plan["plan"][0]["city"] == "Miskolc"
    db.query.assert_not_called()


@pytest.mark.asyncio
async def test_get_coordinates_success_and_404(monkeypatch):
    async def ok(place):
        return 1.0, 2.0

    monkeypatch.setattr(pg, "geocode_place", ok)
    assert await pg.get_coordinates("Budapest") == (1.0, 2.0)

    async def fail(place):
        raise ValueError("missing")

    monkeypatch.setattr(pg, "geocode_place", fail)
    with pytest.raises(HTTPException) as exc:
        await pg.get_coordinates("Nowhere")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_geocode_places(monkeypatch):
    async def fake(place, language="en"):
        if place == "bad":
            raise RuntimeError("fail")
        return 10.0, 20.0

    monkeypatch.setattr(pg, "geocode_place", fake)
    out = await pg.geocode_places(pg.GeocodeRequest(places=["", "Paris", "bad"], language="en"))
    assert out[0] is None
    assert out[1] == {"lat": 10.0, "lon": 20.0}
    assert out[2] is None


@pytest.mark.asyncio
async def test_generate_plan_with_location(monkeypatch):
    async def coords(name):
        return 47.5, 19.0

    def nearest(lat, lon, db=None):
        return {"iata": "BUD"}

    async def cache(db, iata):
        return [{"iata": "VIE"}]

    async def draft(*args, **kwargs):
        return '{"plan":[{"city":"Vienna"}]}'

    monkeypatch.setattr(pg, "get_coordinates", coords)
    monkeypatch.setattr(pg, "nearest_airport", nearest)
    monkeypatch.setattr(pg, "get_direct_destinations_cached", cache)
    monkeypatch.setattr(pg, "normalize_planner_response", lambda plan: plan)

    result = await pg.generate_plan_with_location(
        draft,
        starting_point="Budapest",
        start_date="2026-07-01",
        end_date="2026-07-05",
        people=2,
        travel_length=4,
        db=MagicMock(),
        preferredTransport="allModes",
    )
    assert result["nearest_airport"]["iata"] == "BUD"
    assert result["draft_plan"]["startDate"] == "2026-07-01"
    assert result["starting_point_coords"] == {"lat": 47.5, "lon": 19.0}


@pytest.mark.asyncio
async def test_generate_plan_wrappers_delegate(monkeypatch):
    async def fake_with_location(func, *args, **kwargs):
        return {"ok": True, "func": func.__name__, "args": args}

    monkeypatch.setattr(pg, "generate_plan_with_location", fake_with_location)
    monkeypatch.setattr(pg, "planner_context", lambda request, db: (5, "deepseek"))
    monkeypatch.setattr(pg, "build_unvisited_forbidden_places", lambda db, user_id, extras: ["Paris"])
    monkeypatch.setattr(
        pg,
        "build_visited_places_from_db",
        lambda db, user_id, client: ["Paris, France", "Rome, Italy"],
    )
    monkeypatch.setattr(pg, "merge_exclusion_lists", lambda *groups: [p for g in groups for p in (g or [])])

    visited_req = pg.GenerationRequest(
        visitedPlaces=["Vienna"],
        startingPoint="Budapest",
        startDate="2026-07-01",
        endDate="2026-07-06",
    )
    assert (await pg.generate_visited_plan(visited_req, MagicMock()))["func"] == "generate_travel_plan_visited"

    visited_db_req = pg.GenerationRequest(
        visitedPlaces=[],
        extraPlaces=["Berlin"],
        userId=1,
        startingPoint="Budapest",
        startDate="2026-07-01",
        endDate="2026-07-06",
    )
    out = await pg.generate_visited_plan(visited_db_req, MagicMock())
    assert out["func"] == "generate_travel_plan_visited"
    assert out["args"][3] == ["Paris, France", "Rome, Italy"]

    with pytest.raises(HTTPException) as exc:
        await pg.generate_visited_plan(
            pg.GenerationRequest(
                visitedPlaces=[],
                extraPlaces=[],
                startingPoint="Budapest",
                startDate="2026-07-01",
                endDate="2026-07-06",
            ),
            MagicMock(),
        )
    assert exc.value.status_code == 400

    unvisited_req = pg.UnvisitedGenerationRequest(
        startingPoint="Budapest",
        startDate="2026-07-01",
        endDate="2026-07-06",
        userId=1,
        additionalExclusions=["Rome"],
    )
    assert (await pg.generate_unvisited_plan(unvisited_req, MagicMock()))["func"] == "generate_travel_plan_unvisited"

    random_req = pg.RandomGenerationRequest(
        startingPoint="Budapest",
        startDate="2026-07-01",
        endDate="2026-07-06",
    )
    assert (await pg.generate_random_plan(random_req, MagicMock()))["func"] == "generate_travel_plan_random"
