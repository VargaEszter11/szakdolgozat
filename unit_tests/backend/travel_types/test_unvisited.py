from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.travel_types import unvisited


def test_format_user_visited_place_strings():
    places = [
        SimpleNamespace(place_name="Paris", country="France"),
        SimpleNamespace(place_name="Rome", country=None),
        SimpleNamespace(place_name="", country=""),
    ]
    assert unvisited.format_user_visited_place_strings(places) == ["Paris, France", "Rome"]


def test_merge_exclusion_lists_dedupes():
    assert unvisited.merge_exclusion_lists(["Paris, France"], [" Paris, France ", "Berlin"]) == [
        "Paris, France",
        "Berlin",
    ]


def test_build_unvisited_forbidden_places(monkeypatch):
    monkeypatch.setattr(
        "database.crud.get_user_visited_places",
        lambda db, user_id: [SimpleNamespace(place_name="Vienna", country="Austria")],
    )
    out = unvisited.build_unvisited_forbidden_places(MagicMock(), 3, ["Berlin"])
    assert out == ["Vienna, Austria", "Berlin"]


def test_build_visited_places_from_db(monkeypatch):
    monkeypatch.setattr(
        "database.crud.get_user_visited_places",
        lambda db, user_id: [
            SimpleNamespace(place_name="Paris", country="France"),
            SimpleNamespace(place_name="Rome", country="Italy"),
        ],
    )
    out = unvisited.build_visited_places_from_db(MagicMock(), 2, ["Berlin"])
    assert out == ["Paris, France", "Rome, Italy", "Berlin"]

    empty_db = unvisited.build_visited_places_from_db(MagicMock(), 2, [])
    assert empty_db == ["Paris, France", "Rome, Italy"]


def test_extract_city_and_is_visited():
    assert unvisited._extract_city("Paris, France") == "paris"
    assert unvisited._extract_city("Rome") == "rome"

    assert unvisited._is_visited("Paris", "France", {"paris"}, []) is True
    assert unvisited._is_visited("Lyon", "France", set(), ["paris, france"]) is False
    assert unvisited._is_visited("Paris", "France", set(), ["pari"]) is True
    assert unvisited._is_visited("New York", "USA", set(), ["york"]) is True


@pytest.mark.asyncio
async def test_generate_travel_plan_unvisited_uses_db_planner(monkeypatch):
    run_db_planner = AsyncMock(return_value='{"strategy":"unvisited"}')
    call_llm_api = AsyncMock()
    monkeypatch.setattr(unvisited, "run_db_planner", run_db_planner)
    monkeypatch.setattr(unvisited, "call_llm_api", call_llm_api)

    raw = await unvisited.generate_travel_plan_unvisited(
        startingPoint="Budapest",
        travelLength=5,
        preferences=[],
        forbidden_places=["Paris, France"],
        starting_airport_iata="BUD",
        start_date="2026-07-01",
        end_date="2026-07-06",
    )

    assert raw == '{"strategy":"unvisited"}'
    run_db_planner.assert_awaited_once()
    assert run_db_planner.await_args is not None
    kwargs = run_db_planner.await_args.kwargs
    assert kwargs["strategy"] == "unvisited"
    assert kwargs["forbidden_places"] == ["Paris, France"]
    call_llm_api.assert_not_called()


@pytest.mark.asyncio
async def test_generate_travel_plan_unvisited_llm_filters_forbidden(monkeypatch):
    captured = {}

    async def fake_llm(prompt, provider):
        captured["prompt"] = prompt
        return '{"plan":[]}'

    run_db_planner = AsyncMock()
    monkeypatch.setattr(unvisited, "call_llm_api", fake_llm)
    monkeypatch.setattr(unvisited, "run_db_planner", run_db_planner)

    raw = await unvisited.generate_travel_plan_unvisited(
        startingPoint="Budapest",
        travelLength=4,
        preferences=["hiking"],
        forbidden_places=["Paris, France", "Rome"],
        direct_destinations=[
            {"city": "Paris", "country": "France", "iata": "CDG"},
            {"city": "Vienna", "country": "Austria", "iata": "VIE"},
        ],
        start_date="2026-07-01",
        end_date="2026-07-05",
        language="en",
        llm_provider="deepseek",
        starting_airport_iata=None,
    )

    assert raw == '{"plan":[]}'
    assert "Vienna, Austria (IATA: VIE)" in captured["prompt"]
    assert "Paris, France (IATA: CDG)" not in captured["prompt"]
    assert "ALREADY VISITED" in captured["prompt"]
    assert "Paris" in captured["prompt"]
    run_db_planner.assert_not_called()
