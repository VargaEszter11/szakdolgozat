from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.travel_types import plan_builder


def test_finalize_segment_days_and_dates():
    plan = [
        {"days": 2, "city": "A"},
        {"days": 2, "city": "B"},
        {"days": 0, "city": "Home"},
    ]
    plan_builder._finalize_segment_days_and_dates(plan, "2026-07-01", "2026-07-08", 7)
    assert plan[0]["arrivalDate"] == "2026-07-01"
    assert plan[0]["departureDate"] == "2026-07-03"
    assert plan[1]["days"] == 5
    assert plan[-1]["arrivalDate"] == "2026-07-08"
    assert plan[-1]["days"] == 0


def test_finalize_noop_for_short_plan():
    plan = [{"days": 3, "city": "Only"}]
    plan_builder._finalize_segment_days_and_dates(plan, "2026-07-01", "2026-07-04", 3)
    assert "arrivalDate" not in plan[0]


def test_transport_helpers():
    assert plan_builder._allowed_transport_modes("flight") == {"flight"}
    assert plan_builder._allowed_transport_modes("trainBus") == {"train", "bus"}
    assert plan_builder._allowed_transport_modes("trainBusFerry") == {"train", "bus", "ferry"}
    assert plan_builder._allowed_transport_modes("allModes") is None

    candidates = [
        {"transport": "flight", "city": "A"},
        {"transport": "train", "city": "B"},
        {"transport": "bus", "city": "C"},
    ]
    assert [c["city"] for c in plan_builder._filter_by_preferred_transport(candidates, "trainBus")] == ["B", "C"]
    assert plan_builder._filter_by_preferred_transport(candidates, "allModes") == candidates


def test_prefer_next_transport_orders_flights_first_when_mixed():
    candidates = [
        {"transport": "train", "city": "T"},
        {"transport": "flight", "city": "F"},
        {"transport": "bus", "city": "B"},
    ]
    ordered = plan_builder._prefer_next_transport(candidates, previous_transport="flight")
    assert ordered[0]["city"] == "F"


def test_pick_candidate_requested_vs_random(monkeypatch):
    candidates = [{"city": "A"}, {"city": "B"}, {"city": "C"}]
    assert plan_builder._pick_candidate(candidates, "visited", True)["city"] == "A"
    monkeypatch.setattr(plan_builder.random, "choice", lambda seq: seq[-1])
    assert plan_builder._pick_candidate(candidates, "random", False)["city"] == "C"


def test_merge_helpers_and_format_parse():
    assert plan_builder._merge_place_lists([" Paris "], ["paris"], ["Rome"]) == ["Paris", "Rome"]
    merged = plan_builder._merge_requested_with_ranked(
        [{"iata": "VIE", "city": "Vienna"}],
        [{"iata": "VIE", "city": "Vienna"}, {"iata": "FCO", "city": "Rome"}],
    )
    assert [c["iata"] for c in merged] == ["VIE", "FCO"]

    block = plan_builder._format_candidates(
        [{"city": "Vienna", "country": "AT", "iata": "VIE", "transport": "flight", "distance_km": 200}]
    )
    assert "VIE" in block and "200 km" in block

    assert plan_builder._parse_json_object('{"a":1}') == {"a": 1}
    assert plan_builder._parse_json_object('```json\n{"a":1}\n```') == {"a": 1}
    assert plan_builder._parse_json_object("[1]") is None
    assert plan_builder._parse_json_object("nope") is None


def test_clamp_and_minimum_days():
    assert plan_builder._minimum_stop_days(5) == 2
    assert plan_builder._minimum_stop_days(1) == 1
    assert plan_builder._clamp_days(10, 4) == 4
    assert plan_builder._clamp_days(None, 5) == 2
    # leftover would be 1 (< min 2) so consume all remaining
    assert plan_builder._clamp_days(4, 5) == 5


def test_used_iatas():
    assert plan_builder._used_iatas([{"iata": "bud"}, {"city": "x"}, {"iata": "VIE"}]) == {"BUD", "VIE"}


def test_fallback_and_stop_from_choice(monkeypatch):
    monkeypatch.setattr(plan_builder.random, "choice", lambda seq: seq[0])
    choice = plan_builder._fallback_choice(
        [{"city": "Vienna", "country": "AT", "iata": "VIE", "transport": "flight", "airline_iata": "OS"}],
        strategy="random",
        remaining_days=6,
        has_requested_places=False,
    )
    assert choice["city"] == "Vienna"
    assert choice["days"] >= 1

    monkeypatch.setattr(
        plan_builder,
        "flight_booking_details",
        lambda *a, **k: {
            "booking_url": "https://book",
            "airline_iata": "OS",
            "origin_airport_iata": "BUD",
            "destination_airport_iata": "VIE",
        },
    )
    stop = plan_builder._stop_from_choice(
        MagicMock(),
        choice=choice,
        current_airport="BUD",
        cursor=datetime(2026, 7, 1),
        remaining_days=6,
    )
    assert stop is not None
    assert stop["iata"] == "VIE"
    assert stop["booking_url"] == "https://book"

    monkeypatch.setattr(plan_builder, "flight_booking_details", lambda *a, **k: {})
    assert (
        plan_builder._stop_from_choice(
            MagicMock(),
            choice=choice,
            current_airport="BUD",
            cursor=datetime(2026, 7, 1),
            remaining_days=6,
        )
        is None
    )


def test_append_return_home(monkeypatch):
    monkeypatch.setattr(
        plan_builder,
        "return_flight_booking_details",
        lambda *a, **k: {
            "booking_url": "https://book",
            "airline_iata": "FR",
            "origin_airport_iata": "FCO",
            "destination_airport_iata": "BUD",
        },
    )
    plan = [{"city": "Rome", "iata": "FCO"}]
    plan_builder._append_return_home(
        MagicMock(),
        plan=plan,
        starting_airport_iata="BUD",
        home_city="Budapest",
        home_country="Hungary",
        end_date="2026-07-10",
    )
    assert plan[-1]["city"] == "Budapest"
    assert plan[-1]["country"] == "HU"
    assert plan[-1]["transportFromPreviousCity"] == "flight"
    assert plan[-1]["is_return_home"] is True

    monkeypatch.setattr(plan_builder, "return_flight_booking_details", lambda *a, **k: {})
    monkeypatch.setattr(plan_builder, "ground_transport_between_airports", lambda *a, **k: None)
    monkeypatch.setattr(plan_builder, "ferry_transport_between_airports", lambda *a, **k: None)
    short = [{"city": "Rome", "iata": "FCO"}]
    plan_builder._append_return_home(
        MagicMock(),
        plan=short,
        starting_airport_iata="BUD",
        home_city="Budapest",
        home_country="Hungary",
        end_date="2026-07-10",
    )
    assert len(short) == 1

    def db_with_airport(country_code):
        db = MagicMock()
        ap = MagicMock()
        ap.country_code = country_code
        db.query.return_value.filter.return_value.first.return_value = ap
        return db

    monkeypatch.setattr(plan_builder, "return_flight_booking_details", lambda *a, **k: {})
    monkeypatch.setattr(plan_builder, "ground_transport_between_airports", lambda *a, **k: "bus")
    same_hub = [{"city": "Kosice", "iata": "KSC"}]
    plan_builder._append_return_home(
        MagicMock(),
        plan=same_hub,
        starting_airport_iata="KSC",
        home_city="miskolc",
        home_country="",
        end_date="2026-08-19",
        home_transfer={
            "access_city": "Kosice",
            "local_transport": "bus",
            "home_country": "HU",
        },
    )
    assert same_hub[-1]["city"] == "Miskolc"
    assert same_hub[-1]["country"] == "HU"
    assert same_hub[-1]["is_return_home"] is True
    assert same_hub[-1]["transportFromPreviousCity"] == "bus"
    assert same_hub[-1]["access_city"] == "Kosice"
    assert "local_transport" not in same_hub[-1]

    # City-only start next to its hub airport → fill country from airport.
    near_hub = [{"city": "Rome", "iata": "FCO"}]
    monkeypatch.setattr(
        plan_builder,
        "return_flight_booking_details",
        lambda *a, **k: {
            "booking_url": "https://book",
            "airline_iata": "FR",
            "origin_airport_iata": "FCO",
            "destination_airport_iata": "BUD",
        },
    )
    plan_builder._append_return_home(
        db_with_airport("HU"),
        plan=near_hub,
        starting_airport_iata="BUD",
        home_city="Budapest",
        home_country="",
        end_date="2026-07-10",
    )
    assert near_hub[-1]["country"] == "HU"

    # Off-airport home + missing dated reverse flight: keep flight into hub, then bus home.
    soft_home = [{"city": "Vienna", "iata": "VIE"}]
    monkeypatch.setattr(
        plan_builder,
        "return_flight_booking_details",
        lambda *a, **k: {
            "booking_url": "https://book-soft",
            "origin_airport_iata": "VIE",
            "destination_airport_iata": "KSC",
        },
    )
    monkeypatch.setattr(plan_builder, "ground_transport_between_airports", lambda *a, **k: "bus")
    plan_builder._append_return_home(
        MagicMock(),
        plan=soft_home,
        starting_airport_iata="KSC",
        home_city="Miskolc",
        home_country="",
        end_date="2026-08-19",
        home_transfer={"access_city": "Kosice", "local_transport": "bus"},
    )
    assert soft_home[-1]["transportFromPreviousCity"] == "flight"
    assert soft_home[-1]["access_city"] == "Kosice"
    assert soft_home[-1]["local_transport"] == "bus"
    assert soft_home[-1]["booking_url"] == "https://book-soft"

    flight_home = [{
        "city": "Rathvilly",
        "iata": "DUB",
        "access_city": "Dublin",
        "local_transport": "bus",
        "off_airport": True,
    }]
    monkeypatch.setattr(
        plan_builder,
        "return_flight_booking_details",
        lambda *a, **k: {
            "booking_url": "https://book",
            "airline_iata": "FR",
            "origin_airport_iata": "DUB",
            "destination_airport_iata": "KSC",
        },
    )
    plan_builder._append_return_home(
        MagicMock(),
        plan=flight_home,
        starting_airport_iata="KSC",
        home_city="Miskolc",
        home_country="",
        end_date="2026-08-19",
        home_transfer={"access_city": "Kosice", "local_transport": "bus"},
    )
    assert flight_home[-1]["transportFromPreviousCity"] == "flight"
    assert flight_home[-1]["local_transport"] == "bus"
    assert flight_home[-1]["access_city"] == "Kosice"
    assert flight_home[-1]["departure_access_city"] == "Dublin"
    assert flight_home[-1]["departure_local_transport"] == "bus"
    assert flight_home[-1]["departure_from_city"] == "Rathvilly"

    first = [{"city": "Rathvilly", "iata": "DUB", "transportFromPreviousCity": "flight"}]
    plan_builder._annotate_departure_home_transfer(
        first,
        home_city="miskolc",
        home_transfer={"access_city": "Kosice", "local_transport": "bus"},
    )
    assert first[0]["departure_access_city"] == "Kosice"
    assert first[0]["departure_local_transport"] == "bus"
    assert first[0]["departure_from_city"] == "Miskolc"

    assert first[0]["departure_from_city"] == "Miskolc"


def test_missing_requested_places_lists_all_unused():
    """Visited strategy must report every unused requested place, not stop at the first hit."""
    plan = [{"city": "Paris", "country": "France"}]

    assert plan_builder._missing_requested_places(
        strategy="random",
        requested_places=["Paris", "Rome"],
        plan=plan,
    ) == []
    assert plan_builder._missing_requested_places(
        strategy="visited",
        requested_places=[],
        plan=plan,
    ) == []
    assert plan_builder._missing_requested_places(
        strategy="visited",
        requested_places=["Paris", "Rome", "Vienna"],
        plan=[],
    ) == ["Paris", "Rome", "Vienna"]
    assert plan_builder._missing_requested_places(
        strategy="visited",
        requested_places=["Paris", "Rome", "Vienna"],
        plan=plan,
    ) == ["Rome", "Vienna"]
    assert plan_builder._missing_requested_places(
        strategy="visited",
        requested_places=["Paris"],
        plan=plan,
    ) == []


def test_candidate_choices_for_date(monkeypatch):
    monkeypatch.setattr(plan_builder, "available_flight_candidates", lambda db, origin, cands, day: [])
    cands = [{"transport": "train", "iata": "VIE"}, {"transport": "flight", "iata": "FCO"}]
    out = plan_builder._candidate_choices_for_date(
        MagicMock(),
        current_airport="BUD",
        candidates=cands,
        requested_matches=[],
        departure_date="2026-07-01",
    )
    assert out == [{"transport": "train", "iata": "VIE"}]


@pytest.mark.asyncio
async def test_ask_ai_to_pick_candidate(monkeypatch):
    monkeypatch.setattr(plan_builder, "call_llm_api", AsyncMock(return_value='{"iata":"VIE","days":3,"activities":["walk"]}'))
    candidates = [{"city": "Vienna", "country": "AT", "iata": "VIE", "transport": "flight", "airline_iata": "OS"}]
    choice = await plan_builder._ask_ai_to_pick_candidate(
        candidates=candidates,
        strategy="random",
        current_airport="BUD",
        current_city_label="Budapest",
        remaining_days=5,
        preferences=[],
        plan=[],
        requested_places=[],
        forbidden_places=[],
        extra_places=[],
        preferred_transport="allModes",
        language="en",
        llm_provider="deepseek",
    )
    assert choice is not None
    assert choice["city"] == "Vienna"
    assert choice["days"] == 3

    monkeypatch.setattr(plan_builder, "call_llm_api", AsyncMock(return_value="not-json"))
    assert (
        await plan_builder._ask_ai_to_pick_candidate(
            candidates=candidates,
            strategy="random",
            current_airport="BUD",
            current_city_label="Budapest",
            remaining_days=5,
            preferences=[],
            plan=[],
            requested_places=[],
            forbidden_places=[],
            extra_places=[],
            preferred_transport="allModes",
            language="en",
            llm_provider="deepseek",
        )
        is None
    )


@pytest.mark.asyncio
async def test_build_plan_happy_path(monkeypatch):
    class FakeSession:
        def close(self):
            return None

    sessions = []

    def session_factory():
        s = FakeSession()
        sessions.append(s)
        return s

    monkeypatch.setattr(plan_builder, "SessionLocal", session_factory)
    monkeypatch.setattr(plan_builder, "split_place_label", lambda p: ("Budapest", "Hungary"))
    monkeypatch.setattr(
        plan_builder,
        "_ranked_step_candidates",
        AsyncMock(
            return_value=(
                [{"city": "Vienna", "country": "AT", "iata": "VIE", "transport": "flight"}],
                [],
            )
        ),
    )
    monkeypatch.setattr(
        plan_builder,
        "_candidate_choices_for_date",
        lambda *a, **k: [{"city": "Vienna", "country": "AT", "iata": "VIE", "transport": "flight"}],
    )
    monkeypatch.setattr(
        plan_builder,
        "_ask_ai_to_pick_candidate",
        AsyncMock(
            return_value={
                "city": "Vienna",
                "country": "AT",
                "iata": "VIE",
                "days": 5,
                "transportFromPreviousCity": "flight",
                "activities": ["walk"],
            }
        ),
    )
    monkeypatch.setattr(
        plan_builder,
        "_stop_from_choice",
        lambda db, choice, current_airport, cursor, remaining_days: {
            "city": choice["city"],
            "country": choice["country"],
            "iata": choice["iata"],
            "days": choice["days"],
            "arrivalDate": "2026-07-01",
            "departureDate": "2026-07-06",
            "transportFromPreviousCity": "flight",
            "activities": choice["activities"],
        },
    )
    monkeypatch.setattr(plan_builder, "_append_return_home", lambda *a, **k: None)
    monkeypatch.setattr(plan_builder, "resolve_home_hub_transfer", AsyncMock(return_value=None))
    monkeypatch.setattr(plan_builder, "refresh_booking_details", lambda *a, **k: None)

    result = await plan_builder.build_plan(
        strategy="random",
        starting_point="Budapest, Hungary",
        starting_airport_iata="BUD",
        travel_length=5,
        preferences=[],
        start_date="2026-07-01",
        end_date="2026-07-06",
        language="en",
        llm_provider="deepseek",
    )

    assert result["strategy"] == "random"
    assert result["startingPoint"] == "Budapest, Hungary"
    assert result["plan"][0]["city"] == "Vienna"
    assert len(sessions) >= 2
