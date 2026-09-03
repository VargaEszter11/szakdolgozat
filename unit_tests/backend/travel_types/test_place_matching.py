from backend.travel_types.place_matching import (
    split_place_label,
    extract_city,
    place_matches_candidate,
    place_used_in_plan,
    prioritize_requested_places,
    filter_visited,
    filter_unvisited,
    filter_random,
    filter_strategy_candidates,
)


def test_split_place_label_with_city_and_country():
    city, country = split_place_label("Budapest, Hungary")

    assert city == "Budapest"
    assert country == "Hungary"


def test_split_place_label_without_country():
    city, country = split_place_label("Budapest")

    assert city == "Budapest"
    assert country == ""


def test_extract_city():
    assert extract_city("Budapest, Hungary") == "budapest"


def test_place_matches_candidate_exact_match():
    candidate = {
        "city": "Budapest",
        "country": "Hungary",
    }

    assert place_matches_candidate(
        "Budapest",
        candidate,
    )


def test_place_matches_candidate_country_code():
    candidate = {
        "city": "Rome",
        "country": "IT",
    }

    assert place_matches_candidate(
        "IT",
        candidate,
    )


def test_place_matches_candidate_country_code_case_insensitive():
    candidate = {
        "city": "Rome",
        "country": "IT",
    }

    assert place_matches_candidate(
        "it",
        candidate,
    )


def test_place_matches_candidate_no_match():
    candidate = {
        "city": "Rome",
        "country": "Italy",
    }

    assert not place_matches_candidate(
        "Budapest",
        candidate,
    )


def test_place_used_in_plan_returns_true():
    plan = [
        {
            "city": "Budapest",
            "country": "Hungary",
        }
    ]

    assert place_used_in_plan(
        "Budapest",
        plan,
    )


def test_place_used_in_plan_returns_true_for_country():
    plan = [
        {
            "city": "Rome",
            "country": "IT",
        }
    ]

    assert place_used_in_plan(
        "IT",
        plan,
    )


def test_place_used_in_plan_returns_false():
    plan = [
        {
            "city": "Rome",
            "country": "Italy",
        }
    ]

    assert not place_used_in_plan(
        "Budapest",
        plan,
    )


def test_prioritize_requested_places_moves_requested_city_first():
    candidates = [
        {"city": "Rome", "country": "Italy"},
        {"city": "Budapest", "country": "Hungary"},
    ]

    result = prioritize_requested_places(
        candidates,
        ["Budapest"],
        [],
    )

    assert result[0]["city"] == "Budapest"


def test_filter_visited_returns_matching_places():
    destinations = [
        {"city": "Budapest", "iata": "BUD"},
        {"city": "Rome", "iata": "FCO"},
    ]

    result = filter_visited(
        destinations,
        ["Budapest"],
    )

    assert len(result) == 1
    assert result[0]["iata"] == "BUD"


def test_filter_visited_returns_places_matching_requested_country():
    destinations = [
        {"city": "Budapest", "country": "HU", "iata": "BUD"},
        {"city": "Rome", "country": "IT", "iata": "FCO"},
        {"city": "Milan", "country": "IT", "iata": "MXP"},
    ]

    result = filter_visited(
        destinations,
        ["IT"],
    )

    assert [item["iata"] for item in result] == ["FCO", "MXP"]


def test_filter_unvisited_removes_forbidden_places():
    destinations = [
        {
            "city": "Budapest",
            "country": "Hungary",
            "iata": "BUD",
        },
        {
            "city": "Rome",
            "country": "Italy",
            "iata": "FCO",
        },
    ]

    result = filter_unvisited(
        destinations,
        ["Budapest"],
    )

    assert len(result) == 1
    assert result[0]["iata"] == "FCO"


def test_filter_unvisited_removes_forbidden_country():
    destinations = [
        {
            "city": "Budapest",
            "country": "HU",
            "iata": "BUD",
        },
        {
            "city": "Rome",
            "country": "IT",
            "iata": "FCO",
        },
    ]

    result = filter_unvisited(
        destinations,
        ["IT"],
    )

    assert len(result) == 1
    assert result[0]["iata"] == "BUD"


def test_filter_random_removes_duplicate_iatas():
    destinations = [
        {"city": "Budapest", "iata": "BUD"},
        {"city": "Budapest", "iata": "BUD"},
        {"city": "Rome", "iata": "FCO"},
    ]

    result = filter_random(destinations)

    assert len(result) == 2
    assert {d["iata"] for d in result} == {"BUD", "FCO"}


def test_filter_random_excludes_forbidden_places():
    destinations = [
        {"city": "Budapest", "country": "Hungary", "iata": "BUD"},
        {"city": "Rome", "country": "Italy", "iata": "FCO"},
    ]

    result = filter_random(destinations, ["Rome, Italy"])

    assert len(result) == 1
    assert result[0]["iata"] == "BUD"


def test_filter_strategy_candidates_visited():
    destinations = [
        {"city": "Budapest", "iata": "BUD"},
        {"city": "Rome", "iata": "FCO"},
    ]

    result = filter_strategy_candidates(
        strategy="visited",
        raw_dests=destinations,
        visited_places=["Budapest"],
        forbidden_places=[],
    )

    assert len(result) == 1
    assert result[0]["iata"] == "BUD"


def test_filter_strategy_candidates_unvisited():
    destinations = [
        {
            "city": "Budapest",
            "country": "Hungary",
            "iata": "BUD",
        },
        {
            "city": "Rome",
            "country": "Italy",
            "iata": "FCO",
        },
    ]

    result = filter_strategy_candidates(
        strategy="unvisited",
        raw_dests=destinations,
        visited_places=[],
        forbidden_places=["Budapest"],
    )

    assert len(result) == 1
    assert result[0]["iata"] == "FCO"


def test_filter_strategy_candidates_random():
    destinations = [
        {"city": "Budapest", "iata": "BUD"},
        {"city": "Budapest", "iata": "BUD"},
        {"city": "Rome", "iata": "FCO"},
    ]

    result = filter_strategy_candidates(
        strategy="random",
        raw_dests=destinations,
        visited_places=[],
        forbidden_places=[],
    )

    assert len(result) == 2