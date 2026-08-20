"""
Integration tests for plan request orchestration (formerly plan_generation).
"""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from travel_types import plan_requests as pr
from travel_types.unvisited import UnvisitedGenerationRequest


class TestPlanRequestsHelpersWithDatabase:
    """Helpers that read user / airport state from the test database."""

    def test_clean_plan_city_names_uses_airport_city(self, db, european_airports):
        plan = {"plan": [{"iata": "FCO", "city": "Fiumicino"}]}

        pr.clean_plan_city_names(plan, db)

        assert plan["plan"][0]["city"] == "Rome"

    def test_planner_context_uses_request_dates(self, db, test_user):
        request = SimpleNamespace(
            startDate="2026-07-01",
            endDate="2026-07-08",
            plannerUserId=test_user["id"],
            userId=test_user["id"],
        )

        length, _ = pr.planner_context(request, db)

        assert length == 7


class TestPlanRequestsGeneration:
    """End-to-end generate_* orchestration with external I/O mocked."""

    @pytest.mark.asyncio
    async def test_generate_visited_plan_with_location(self, db, test_user, monkeypatch):
        async def fake_coords(name):
            return 47.5, 19.0

        async def fake_nearest(lat, lon, db=None):
            return {"iata": "BUD", "name": "Budapest"}

        async def fake_cache(database, iata):
            return [{"iata": "FCO", "city": "Rome", "country": "IT"}]

        async def fake_visited(*args, **kwargs):
            return json.dumps(
                {
                    "startingPoint": "Budapest",
                    "plan": [{"city": "Rome", "iata": "FCO", "days": 4}],
                }
            )

        monkeypatch.setattr(pr, "get_coordinates", fake_coords)
        monkeypatch.setattr(pr, "nearest_airport", fake_nearest)
        monkeypatch.setattr(pr, "get_direct_destinations_cached", fake_cache)
        monkeypatch.setattr(pr, "generate_travel_plan_visited", fake_visited)
        monkeypatch.setattr(pr, "normalize_planner_response", lambda plan: plan)

        request = pr.GenerationRequest(
            visitedPlaces=["Rome"],
            startingPoint="Budapest",
            startDate="2026-07-01",
            endDate="2026-07-05",
            userId=test_user["id"],
            people=2,
        )

        result = await pr.generate_visited_plan(request, db)

        assert result["nearest_airport"]["iata"] == "BUD"
        assert result["draft_plan"]["startDate"] == "2026-07-01"
        assert result["draft_plan"]["tripLengthDays"] == 4
        assert result["starting_point_coords"] == {"lat": 47.5, "lon": 19.0}

    @pytest.mark.asyncio
    async def test_generate_unvisited_plan_uses_db_exclusions(
        self,
        db,
        test_user,
        visited_place,
        monkeypatch,
    ):
        captured = {}

        async def fake_with_location(func, *args, **kwargs):
            captured["forbidden"] = args[3]
            return {"ok": True}

        monkeypatch.setattr(pr, "generate_plan_with_location", fake_with_location)
        monkeypatch.setattr(pr, "planner_context", lambda request, database: (5, "deepseek"))

        request = UnvisitedGenerationRequest(
            startingPoint="Budapest",
            startDate="2026-07-01",
            endDate="2026-07-06",
            userId=test_user["id"],
            additionalExclusions=["Berlin"],
        )

        result = await pr.generate_unvisited_plan(request, db)

        assert result == {"ok": True}
        assert "Prague, CZ" in captured["forbidden"] or "Prague" in str(captured["forbidden"])
        assert "Berlin" in captured["forbidden"]
