"""
Integration tests for unvisited travel-plan generation.
"""
import json
from unittest.mock import AsyncMock

import pytest

from travel_types import plan_builder, unvisited


class TestUnvisitedForbiddenPlacesWithDatabase:
    """Forbidden-place building from persisted visited places."""

    def test_build_forbidden_places_merges_db_and_extras(
        self,
        db,
        test_user,
        visited_place,
    ):
        forbidden = unvisited.build_unvisited_forbidden_places(
            db,
            test_user["id"],
            ["Berlin"],
        )

        assert "Berlin" in forbidden
        assert any("Prague" in item for item in forbidden)


class TestUnvisitedPlanWithDatabase:
    """unvisited generator DB-planner path and LLM filtering."""

    @pytest.mark.asyncio
    async def test_generate_with_airport_uses_db_planner(
        self,
        db,
        european_airports,
        bud_fco_route,
        monkeypatch,
        patch_plan_builder_db,
    ):
        from database import models

        db.add(
            models.DirectRoute(
                id=2,
                airline_iata="FR",
                airline_name="Ryanair",
                flight_number="FR4321",
                origin_iata="FCO",
                destination_iata="BUD",
                is_seasonal=False,
                is_active=True,
            )
        )
        db.commit()

        patch_plan_builder_db(plan_builder)
        monkeypatch.setattr(
            "travel_types.route_candidates.get_direct_destinations_cached",
            AsyncMock(
                side_effect=lambda database, current_airport: (
                    [{"iata": "FCO", "city": "Rome", "country": "IT", "airline_iata": "FR"}]
                    if current_airport == "BUD"
                    else [{"iata": "BUD", "city": "Budapest", "country": "HU", "airline_iata": "FR"}]
                )
            ),
        )
        monkeypatch.setattr(
            plan_builder,
            "call_llm_api",
            AsyncMock(
                return_value=json.dumps(
                    {
                        "city": "Rome",
                        "country": "IT",
                        "iata": "FCO",
                        "days": 4,
                        "transportFromPreviousCity": "flight",
                        "activities": ["pasta"],
                    }
                )
            ),
        )

        raw = await unvisited.generate_travel_plan_unvisited(
            startingPoint="Budapest, Hungary",
            travelLength=4,
            preferences=[],
            forbidden_places=["Paris, France"],
            start_date="2026-08-01",
            end_date="2026-08-05",
            starting_airport_iata="BUD",
            llm_provider="deepseek",
        )

        data = json.loads(raw)
        assert data["strategy"] == "unvisited"
        assert data["plan"][0]["iata"] == "FCO"

    @pytest.mark.asyncio
    async def test_generate_without_airport_excludes_forbidden_from_prompt(self, monkeypatch):
        captured = {}

        async def fake_llm(prompt, provider):
            captured["prompt"] = prompt
            return '{"plan":[]}'

        monkeypatch.setattr(unvisited, "call_llm_api", fake_llm)

        await unvisited.generate_travel_plan_unvisited(
            startingPoint="Budapest",
            travelLength=4,
            preferences=[],
            forbidden_places=["Paris, France"],
            direct_destinations=[
                {"city": "Paris", "country": "France", "iata": "CDG"},
                {"city": "Vienna", "country": "Austria", "iata": "VIE"},
            ],
            start_date="2026-07-01",
            end_date="2026-07-05",
        )

        assert "Vienna, Austria (IATA: VIE)" in captured["prompt"]
        assert "Paris, France (IATA: CDG)" not in captured["prompt"]
        assert "ALREADY VISITED" in captured["prompt"]
