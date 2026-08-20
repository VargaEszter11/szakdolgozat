"""
Integration tests for random travel-plan generation.
"""
import json
from unittest.mock import AsyncMock

import pytest

from travel_types import plan_builder, random as random_plan


class TestRandomPlanWithDatabase:
    """random generator against the DB planner path."""

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
                        "days": 3,
                        "transportFromPreviousCity": "flight",
                        "activities": ["walk"],
                    }
                )
            ),
        )

        raw = await random_plan.generate_travel_plan_random(
            startingPoint="Budapest, Hungary",
            travelLength=3,
            preferences=[],
            start_date="2026-08-01",
            end_date="2026-08-04",
            starting_airport_iata="BUD",
            llm_provider="deepseek",
        )

        data = json.loads(raw)
        assert "trips" in data
        assert data["trips"][0]["plan"][0]["iata"] == "FCO"
