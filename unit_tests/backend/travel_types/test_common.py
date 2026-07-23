from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from backend.travel_types import common


def test_language_name_known_and_fallback():
    assert common.language_name("en") == "English"
    assert common.language_name("HU") == "Hungarian"
    assert common.language_name("de") == "German"
    assert common.language_name("xx") == "English"
    assert common.language_name("") == "English"
    assert common.language_name(None) == "English"


def test_preferences_line():
    assert common.preferences_line(None) == "none"
    assert common.preferences_line([]) == "none"
    assert common.preferences_line([" museums ", "", "hiking"]) == "museums, hiking"


def test_list_line_and_block():
    assert common._list_line(None) == "none"
    assert common._list_line(["a", " ", "b"]) == "a, b"
    assert common._block("one", None, "two") == "one\ntwo\n"


def test_places_context_block():
    text = common.places_context_block(
        requested_places=["Paris"],
        forbidden_places=["Rome"],
        extra_places=["Berlin"],
    )
    assert "Paris" in text
    assert "Rome" in text
    assert "Berlin" in text


def test_system_and_header_prompts():
    system = common.system_travel_planner("English")
    assert "SYSTEM:" in system
    assert "English" in system
    assert "train | bus | flight" in system

    next_stop = common.system_next_stop("Hungarian")
    assert "ONE next stop" in next_stop
    assert "Hungarian" in next_stop

    header = common.user_trip_header("Budapest", "2026-07-01", "2026-07-08", 7, ["food"])
    assert "Starting point: Budapest" in header
    assert "Preferences: food" in header


def test_itinerary_rules_and_output_schemas():
    rules = common.itinerary_rules_standard(
        travel_length=5,
        start_date="2026-01-01",
        end_date="2026-01-06",
        starting_point="Budapest",
        extra_rule_lines=("- Extra rule.",),
    )
    assert "Sum of days MUST equal 5" in rules
    assert "Extra rule." in rules
    assert "return home" in rules.lower() or "starting point" in rules

    single = common.output_json_single_trip_schema("2026-01-01", "2026-01-05", "visited")
    assert '"strategy": "visited"' in single
    assert "2026-01-01" in single

    random_schema = common.output_json_random_five_trips("a", "b")
    assert '"trips"' in random_schema
    assert '"strategy": "random"' in random_schema


def test_next_stop_prompt_includes_constraints():
    prompt = common.next_stop_prompt(
        strategy="visited",
        lang_name="English",
        current_airport="BUD",
        current_city_label="Budapest, Hungary",
        prefs="museums",
        remaining_days=4,
        min_stop_days=2,
        cand_block="- Vienna (IATA: VIE)",
        avoid="Budapest",
        requested_places=["Vienna"],
        forbidden_places=["Rome"],
        extra_places=["Prague"],
        preferred_transport="trainBus",
    )
    assert "Current departure airport (IATA): BUD" in prompt
    assert "Vienna" in prompt
    assert "Rome" in prompt
    assert "trainBus" in prompt


def test_json_helpers():
    assert common.from_json(common.as_json({"a": 1})) == {"a": 1}


def test_merge_place_lists_dedupes_case_insensitively():
    assert common.merge_place_lists([" Paris "], ["paris"], ["Rome", ""]) == ["Paris", "Rome"]
    assert common.merge_place_lists(None, []) == []


def test_place_and_destination_labels():
    assert common.place_label(SimpleNamespace(place_name="Paris", country="France")) == "Paris, France"
    assert common.place_label(SimpleNamespace(place_name="Rome", country=None)) == "Rome"
    assert common.destination_label({"city": "Vienna", "country": "Austria", "iata": "VIE"}) == (
        "Vienna, Austria (IATA: VIE)"
    )


def test_destinations_text():
    assert common.destinations_text(["A", "B"]) == "A\nB"
    assert common.destinations_text([]) == common.NO_DIRECT_FLIGHTS_MESSAGE


@pytest.mark.asyncio
async def test_run_db_planner_wraps_build_plan():
    fake_plan = {"strategy": "random", "plan": []}
    with patch("backend.travel_types.plan_builder.build_plan", new=AsyncMock(return_value=fake_plan)) as build:
        raw = await common.run_db_planner(
            strategy="random",
            starting_point="Budapest",
            starting_airport_iata="BUD",
            travel_length=5,
            preferences=[],
            start_date="2026-07-01",
            end_date="2026-07-06",
            language="en",
            llm_provider="deepseek",
        )

    assert common.from_json(raw) == fake_plan
    build.assert_awaited_once()
