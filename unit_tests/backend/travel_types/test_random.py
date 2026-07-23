from unittest.mock import AsyncMock

import pytest

from backend.travel_types import random as random_plan


@pytest.mark.asyncio
async def test_generate_travel_plan_random_uses_db_planner_when_airport(monkeypatch):
    run_db_planner = AsyncMock(return_value='{"startingPoint":"Budapest","plan":[]}')
    call_llm_api = AsyncMock(return_value="should-not-call")
    monkeypatch.setattr(random_plan, "run_db_planner", run_db_planner)
    monkeypatch.setattr(random_plan, "call_llm_api", call_llm_api)

    raw = await random_plan.generate_travel_plan_random(
        startingPoint="Budapest",
        travelLength=5,
        preferences=["food"],
        start_date="2026-07-01",
        end_date="2026-07-06",
        starting_airport_iata="BUD",
        preferredTransport="allModes",
        llm_provider="deepseek",
    )

    data = random_plan.from_json(raw)
    assert "trips" in data
    assert data["trips"][0]["startingPoint"] == "Budapest"
    run_db_planner.assert_awaited_once()
    call_llm_api.assert_not_called()


@pytest.mark.asyncio
async def test_generate_travel_plan_random_falls_back_to_llm(monkeypatch):
    captured = {}

    async def fake_llm(prompt, provider):
        captured["prompt"] = prompt
        captured["provider"] = provider
        return '{"trips":[]}'

    run_db_planner = AsyncMock()
    monkeypatch.setattr(random_plan, "call_llm_api", fake_llm)
    monkeypatch.setattr(random_plan, "run_db_planner", run_db_planner)

    raw = await random_plan.generate_travel_plan_random(
        startingPoint="Budapest",
        travelLength=4,
        preferences=["museums"],
        direct_destinations=[{"city": "Vienna", "country": "Austria", "iata": "VIE"}],
        start_date="2026-07-01",
        end_date="2026-07-05",
        language="en",
        llm_provider="ollama",
        starting_airport_iata=None,
    )

    assert raw == '{"trips":[]}'
    assert captured["provider"] == "ollama"
    assert "Available airport-linked destinations" in captured["prompt"]
    assert "Vienna, Austria (IATA: VIE)" in captured["prompt"]
    assert "random" in captured["prompt"]
    run_db_planner.assert_not_called()


@pytest.mark.asyncio
async def test_generate_travel_plan_random_llm_with_empty_destinations(monkeypatch):
    from backend.travel_types.common import NO_DIRECT_FLIGHTS_MESSAGE

    async def fake_llm(prompt, provider):
        return prompt

    monkeypatch.setattr(random_plan, "call_llm_api", fake_llm)
    out = await random_plan.generate_travel_plan_random(
        startingPoint="Budapest",
        travelLength=3,
        preferences=[],
        direct_destinations=[],
        start_date="2026-01-01",
        end_date="2026-01-04",
    )
    assert NO_DIRECT_FLIGHTS_MESSAGE in out
