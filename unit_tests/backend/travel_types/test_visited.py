from unittest.mock import AsyncMock

import pytest

from backend.travel_types import visited


def test_matching_destinations():
    destinations = [
        {"city": "Vienna", "country": "Austria", "iata": "VIE"},
        {"city": "Rome", "country": "Italy", "iata": "FCO"},
        {"city": "", "country": "X", "iata": "XXX"},
    ]
    out = visited._matching_destinations(destinations, ["vien", "Rome, Italy", "nowhere"])
    assert "Vienna, Austria (IATA: VIE)" in out
    assert "Rome, Italy (IATA: FCO)" in out
    assert all("XXX" not in item for item in out)


@pytest.mark.asyncio
async def test_generate_travel_plan_visited_uses_db_planner(monkeypatch):
    run_db_planner = AsyncMock(return_value='{"strategy":"visited"}')
    call_llm_api = AsyncMock()
    monkeypatch.setattr(visited, "run_db_planner", run_db_planner)
    monkeypatch.setattr(visited, "call_llm_api", call_llm_api)

    raw = await visited.generate_travel_plan_visited(
        startingPoint="Budapest",
        travelLength=5,
        preferences=["food"],
        visitedPlaces=["Vienna"],
        extra_places=["Prague"],
        starting_airport_iata="BUD",
        start_date="2026-07-01",
        end_date="2026-07-06",
        preferredTransport="flight",
        llm_provider="deepseek",
    )

    assert raw == '{"strategy":"visited"}'
    run_db_planner.assert_awaited_once()
    assert run_db_planner.await_args is not None
    kwargs = run_db_planner.await_args.kwargs
    assert kwargs["strategy"] == "visited"
    assert kwargs["visited_places"] == ["Vienna", "Prague"]
    assert kwargs["extra_places"] == ["Prague"]
    assert kwargs["preferred_transport"] == "flight"
    call_llm_api.assert_not_called()


@pytest.mark.asyncio
async def test_generate_travel_plan_visited_falls_back_to_llm(monkeypatch):
    captured = {}

    async def fake_llm(prompt, provider):
        captured["prompt"] = prompt
        captured["provider"] = provider
        return '{"plan":[]}'

    run_db_planner = AsyncMock()
    monkeypatch.setattr(visited, "call_llm_api", fake_llm)
    monkeypatch.setattr(visited, "run_db_planner", run_db_planner)

    raw = await visited.generate_travel_plan_visited(
        startingPoint="Budapest",
        travelLength=4,
        preferences=["museums"],
        visitedPlaces=["Vienna"],
        extra_places=["Rome"],
        direct_destinations=[
            {"city": "Vienna", "country": "Austria", "iata": "VIE"},
            {"city": "Berlin", "country": "Germany", "iata": "BER"},
        ],
        start_date="2026-07-01",
        end_date="2026-07-05",
        language="en",
        llm_provider="deepseek",
        starting_airport_iata=None,
    )

    assert raw == '{"plan":[]}'
    assert captured["provider"] == "deepseek"
    assert "Vienna, Austria (IATA: VIE)" in captured["prompt"]
    assert "Berlin, Germany (IATA: BER)" not in captured["prompt"]
    assert "ONLY choose destinations from this list" in captured["prompt"]
    assert "Vienna" in captured["prompt"] and "Rome" in captured["prompt"]
    run_db_planner.assert_not_called()
