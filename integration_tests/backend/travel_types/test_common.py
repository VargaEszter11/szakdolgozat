"""
Integration tests for shared travel-type helpers.
"""
import json
from unittest.mock import AsyncMock

import pytest

from travel_types import common
from travel_types import plan_builder


class TestCommonWithPlanner:
    """common.run_db_planner wired to the real itinerary builder + test DB."""

    @pytest.mark.asyncio
    async def test_run_db_planner_returns_json_plan(
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

        async def fake_destinations(database, current_airport):
            if current_airport == "BUD":
                return [{"iata": "FCO", "city": "Rome", "country": "IT", "airline_iata": "FR"}]
            return [{"iata": "BUD", "city": "Budapest", "country": "HU", "airline_iata": "FR"}]

        monkeypatch.setattr(
            "travel_types.route_candidates.get_direct_destinations_cached",
            fake_destinations,
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
                        "days": 5,
                        "transportFromPreviousCity": "flight",
                        "activities": ["Colosseum"],
                    }
                )
            ),
        )

        raw = await common.run_db_planner(
            strategy="random",
            starting_point="Budapest, Hungary",
            starting_airport_iata="BUD",
            travel_length=5,
            preferences=["history"],
            start_date="2026-08-01",
            end_date="2026-08-06",
            language="en",
            llm_provider="deepseek",
        )

        data = json.loads(raw)
        assert data["strategy"] == "random"
        assert data["startingPoint"] == "Budapest, Hungary"
        assert data["plan"]
        assert data["plan"][0]["iata"] == "FCO"
        assert data["plan"][-1]["iata"] == "BUD"


class TestCommonPromptHelpers:
    """Lightweight checks that shared prompt helpers stay coherent."""

    def test_language_and_place_helpers(self):
        assert common.language_name("hu") == "Hungarian"
        assert common.merge_place_lists(["Paris"], ["paris", "Rome"]) == ["Paris", "Rome"]
        assert "SYSTEM:" in common.system_travel_planner("English")
        assert "Trip length: 5 days" in common.user_trip_header(
            "Budapest", "2026-07-01", "2026-07-06", 5, ["food"]
        )
