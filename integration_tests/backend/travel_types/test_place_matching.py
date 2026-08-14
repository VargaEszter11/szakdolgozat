"""
Integration tests for place matching with database-backed visited places.
"""
from database import crud, schemas
from travel_types.place_matching import (
    filter_strategy_candidates,
    filter_visited,
    filter_unvisited,
    place_matches_candidate,
    prioritize_requested_places,
)


class TestPlaceMatchingWithDatabase:
    """Place matching integrated with persisted visited places."""

    def test_filter_visited_uses_stored_places(self, db, test_user, european_airports):
        crud.create_visited_place(
            db,
            schemas.VisitedPlaceCreate(
                user_id=test_user["id"],
                place_name="Budapest",
                country="HU",
                rating=None,
            ),
        )
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

        places = crud.get_user_visited_places(db, user_id=test_user["id"])
        visited_labels = [
            str(place.place_name) for place in places if place.place_name is not None
        ]
        destinations = [
            {"city": "Budapest", "country": "HU", "iata": "BUD"},
            {"city": "Vienna", "country": "AT", "iata": "VIE"},
            {"city": "Rome", "country": "IT", "iata": "FCO"},
        ]

        result = filter_visited(destinations, visited_labels)

        assert {item["iata"] for item in result} == {"BUD", "FCO"}

    def test_filter_unvisited_excludes_stored_places(self, db, test_user, european_airports):
        crud.create_visited_place(
            db,
            schemas.VisitedPlaceCreate(
                user_id=test_user["id"],
                place_name="Budapest",
                country="HU",
                rating=None,
            ),
        )
        db.commit()

        forbidden = [
            str(place.place_name)
            for place in crud.get_user_visited_places(db, test_user["id"])
            if place.place_name is not None
        ]
        destinations = [
            {"city": "Budapest", "country": "HU", "iata": "BUD"},
            {"city": "Vienna", "country": "AT", "iata": "VIE"},
        ]

        result = filter_unvisited(destinations, forbidden)

        assert len(result) == 1
        assert result[0]["iata"] == "VIE"

    def test_prioritize_requested_places_with_user_visits(self, db, test_user, european_airports):
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

        candidates = [
            {"city": "Vienna", "country": "AT", "iata": "VIE"},
            {"city": "Rome", "country": "IT", "iata": "FCO"},
        ]
        requested = ["Rome"]

        result = prioritize_requested_places(candidates, requested, plan=[])

        assert result[0]["iata"] == "FCO"

    def test_place_matches_candidate_with_country_codes_from_db(self, european_airports):
        candidate = {"city": "Budapest", "country": "HU", "iata": "BUD"}

        assert place_matches_candidate("HU", candidate) is True
        assert place_matches_candidate("Budapest", candidate) is True
        assert place_matches_candidate("Vienna", candidate) is False

    def test_filter_strategy_candidates_visited_strategy(self, db, test_user, european_airports):
        crud.create_visited_place(
            db,
            schemas.VisitedPlaceCreate(
                user_id=test_user["id"],
                place_name="Vienna",
                country="AT",
                rating=None,
            ),
        )
        db.commit()

        visited_labels = [
            str(place.place_name)
            for place in crud.get_user_visited_places(db, user_id=test_user["id"])
            if place.place_name is not None
        ]
        destinations = [
            {"city": "Budapest", "country": "HU", "iata": "BUD"},
            {"city": "Vienna", "country": "AT", "iata": "VIE"},
        ]

        result = filter_strategy_candidates(
            strategy="visited",
            raw_dests=destinations,
            visited_places=visited_labels,
            forbidden_places=[],
        )

        assert len(result) == 1
        assert result[0]["iata"] == "VIE"
