"""
Integration tests for route candidate building with a real database.
"""
import pytest

from travel_types.route_candidates import (
    airport_distance,
    build_candidates,
    ground_candidates_from_airport,
    ground_transport_between_airports,
    rank_candidates,
)


class TestRouteCandidatesWithDatabase:
    """Route candidate helpers integrated with persisted airport data."""

    def test_airport_distance_from_database(self, db, european_airports):
        distance = airport_distance(db, "BUD", "VIE")

        assert distance is not None
        assert distance == pytest.approx(216, abs=15)

    def test_ground_transport_between_database_airports(self, db, european_airports):
        transport = ground_transport_between_airports(db, "BUD", "VIE")

        assert transport == "bus"

    def test_ground_candidates_from_database_airport(self, db, european_airports):
        candidates = ground_candidates_from_airport(
            db,
            "BUD",
            excluded_iatas=set(),
        )

        iatas = {candidate["iata"] for candidate in candidates}
        assert "VIE" in iatas
        assert "FCO" not in iatas
        assert all(candidate["transport"] in {"bus", "train"} for candidate in candidates)

    def test_rank_candidates_prefers_closer_database_destinations(self, db, european_airports):
        candidates = ground_candidates_from_airport(
            db,
            "BUD",
            excluded_iatas=set(),
        )

        ranked = rank_candidates(candidates, limit=3)

        assert ranked[0]["iata"] == "VIE"

    @pytest.mark.asyncio
    async def test_build_candidates_combines_ground_and_flight_routes(self, db, european_airports, monkeypatch):
        async def fake_get_direct_destinations_cached(database, current_airport):
            assert current_airport == "BUD"
            return [
                {"iata": "FCO", "city": "Rome", "country": "IT"},
                {"iata": "JFK", "city": "New York", "country": "US"},
            ]

        monkeypatch.setattr(
            "travel_types.route_candidates.get_direct_destinations_cached",
            fake_get_direct_destinations_cached,
        )

        result = await build_candidates(
            db,
            strategy="random",
            current_airport="BUD",
            hub_iata="BUD",
            used_iatas=set(),
            visited_places=[],
            forbidden_places=[],
        )

        transports = {candidate["iata"]: candidate["transport"] for candidate in result}
        assert transports["VIE"] == "bus"
        assert transports["FCO"] == "flight"
        assert "JFK" not in transports

    @pytest.mark.asyncio
    async def test_build_candidates_unvisited_strategy_excludes_db_places(
        self, db, test_user, european_airports, monkeypatch
    ):
        from database import crud, schemas

        crud.create_visited_place(
            db,
            schemas.VisitedPlaceCreate(
                user_id=test_user["id"],
                place_name="Rome",
                country="IT",
                rating=None,
            ),
        )
        db.commit()
        forbidden_labels = [
            str(place.place_name)
            for place in crud.get_user_visited_places(db, user_id=test_user["id"])
            if place.place_name is not None
        ]

        async def fake_get_direct_destinations_cached(database, current_airport):
            return [
                {"iata": "FCO", "city": "Rome", "country": "IT"},
                {"iata": "VIE", "city": "Vienna", "country": "AT"},
            ]

        monkeypatch.setattr(
            "travel_types.route_candidates.get_direct_destinations_cached",
            fake_get_direct_destinations_cached,
        )

        result = await build_candidates(
            db,
            strategy="unvisited",
            current_airport="BUD",
            hub_iata="BUD",
            used_iatas=set(),
            visited_places=[],
            forbidden_places=forbidden_labels,
        )

        assert "FCO" not in {candidate["iata"] for candidate in result}
        assert "VIE" in {candidate["iata"] for candidate in result}
