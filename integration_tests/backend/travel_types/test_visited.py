"""
Integration tests for visited travel-plan generation.
"""
import json
from unittest.mock import AsyncMock

import pytest

from travel_types import plan_builder, visited


class TestVisitedMatching:
    """Destination matching used by the visited LLM fallback path."""

    def test_matching_destinations_from_requested_labels(self):
        destinations = [
            {"city": "Vienna", "country": "Austria", "iata": "VIE"},
            {"city": "Rome", "country": "Italy", "iata": "FCO"},
        ]

        matched = visited._matching_destinations(destinations, ["vien", "Rome, Italy"])

        assert "Vienna, Austria (IATA: VIE)" in matched
        assert "Rome, Italy (IATA: FCO)" in matched


class TestVisitedPlanWithDatabase:
    """visited generator DB-planner path and LLM fallback."""

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
                        "activities": ["Colosseum"],
                    }
                )
            ),
        )

        raw = await visited.generate_travel_plan_visited(
            startingPoint="Budapest, Hungary",
            travelLength=4,
            preferences=["history"],
            visitedPlaces=["Rome"],
            start_date="2026-08-01",
            end_date="2026-08-05",
            starting_airport_iata="BUD",
            llm_provider="deepseek",
        )

        data = json.loads(raw)
        assert data["strategy"] == "visited"
        assert data["plan"][0]["iata"] == "FCO"

    @pytest.mark.asyncio
    async def test_generate_without_airport_uses_matching_destinations(self, monkeypatch):
        captured = {}

        async def fake_llm(prompt, provider):
            captured["prompt"] = prompt
            return '{"plan":[]}'

        monkeypatch.setattr(visited, "call_llm_api", fake_llm)

        await visited.generate_travel_plan_visited(
            startingPoint="Budapest",
            travelLength=4,
            preferences=[],
            visitedPlaces=["Vienna"],
            extra_places=["Rome"],
            direct_destinations=[
                {"city": "Vienna", "country": "Austria", "iata": "VIE"},
                {"city": "Berlin", "country": "Germany", "iata": "BER"},
            ],
            start_date="2026-07-01",
            end_date="2026-07-05",
            llm_provider="deepseek",
        )

        assert "Vienna, Austria (IATA: VIE)" in captured["prompt"]
        assert "Berlin, Germany (IATA: BER)" not in captured["prompt"]
        assert "ONLY choose destinations from this list" in captured["prompt"]
        assert "Vienna" in captured["prompt"] and "Rome" in captured["prompt"]
