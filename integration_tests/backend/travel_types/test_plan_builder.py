"""
Integration tests for itinerary building (formerly planner.py).
"""
import json
from unittest.mock import AsyncMock

import pytest

from travel_types import plan_builder


@pytest.fixture
def round_trip_bud_fco(db, european_airports, bud_fco_route):
    """BUD→FCO and FCO→BUD active routes for outbound + return legs."""
    from database import models

    ret = models.DirectRoute(
        id=2,
        airline_iata="FR",
        airline_name="Ryanair",
        flight_number="FR4321",
        origin_iata="FCO",
        destination_iata="BUD",
        is_seasonal=False,
        is_active=True,
    )
    db.add(ret)
    db.commit()
    return ret


class TestPlanBuilderWithDatabase:
    """build_plan against persisted airports/routes with LLM mocked."""

    @pytest.mark.asyncio
    async def test_build_plan_random_creates_stops_and_return_home(
        self,
        db,
        european_airports,
        round_trip_bud_fco,
        monkeypatch,
        patch_plan_builder_db,
    ):
        patch_plan_builder_db(plan_builder)

        async def fake_destinations(database, current_airport):
            if current_airport == "BUD":
                return [
                    {
                        "iata": "FCO",
                        "city": "Rome",
                        "country": "IT",
                        "airline_iata": "FR",
                        "airline_name": "Ryanair",
                    }
                ]
            return [
                {
                    "iata": "BUD",
                    "city": "Budapest",
                    "country": "HU",
                    "airline_iata": "FR",
                    "airline_name": "Ryanair",
                }
            ]

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
                        "activities": ["Forum"],
                    }
                )
            ),
        )

        result = await plan_builder.build_plan(
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

        assert result["strategy"] == "random"
        assert len(result["plan"]) >= 2
        assert result["plan"][0]["iata"] == "FCO"
        assert result["plan"][0]["days"] == 5
        assert result["plan"][-1]["iata"] == "BUD"
        assert result["plan"][-1]["days"] == 0
        assert result["plan"][-1]["transportFromPreviousCity"] == "flight"
        assert "booking_url" in result["plan"][0]

    @pytest.mark.asyncio
    async def test_build_plan_visited_prefers_requested_city(
        self,
        db,
        european_airports,
        round_trip_bud_fco,
        monkeypatch,
        patch_plan_builder_db,
    ):
        from database import models

        db.add(
            models.DirectRoute(
                id=3,
                airline_iata="FR",
                airline_name="Ryanair",
                flight_number="FR100",
                origin_iata="BUD",
                destination_iata="VIE",
                is_seasonal=False,
                is_active=True,
            )
        )
        db.add(
            models.DirectRoute(
                id=4,
                airline_iata="FR",
                airline_name="Ryanair",
                flight_number="FR101",
                origin_iata="VIE",
                destination_iata="BUD",
                is_seasonal=False,
                is_active=True,
            )
        )
        db.commit()

        patch_plan_builder_db(plan_builder)

        async def fake_destinations(database, current_airport):
            if current_airport == "BUD":
                return [
                    {"iata": "FCO", "city": "Rome", "country": "IT", "airline_iata": "FR"},
                    {"iata": "VIE", "city": "Vienna", "country": "AT", "airline_iata": "FR"},
                ]
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
                        "city": "Vienna",
                        "country": "AT",
                        "iata": "VIE",
                        "days": 4,
                        "transportFromPreviousCity": "flight",
                        "activities": ["Old town"],
                    }
                )
            ),
        )

        result = await plan_builder.build_plan(
            strategy="visited",
            starting_point="Budapest, Hungary",
            starting_airport_iata="BUD",
            travel_length=4,
            preferences=[],
            start_date="2026-08-01",
            end_date="2026-08-05",
            language="en",
            llm_provider="deepseek",
            visited_places=["Vienna"],
        )

        assert result["plan"][0]["iata"] == "VIE"
        assert result["requestedPlacesMissing"] == []
