from backend.utils.plan_enrichment import normalize_planner_response


def test_normalize_planner_response_returns_none_for_none():
    result = normalize_planner_response(None)

    assert result is None


def test_normalize_planner_response_returns_non_dict_unchanged():
    result = normalize_planner_response("not a dict")

    assert result == "not a dict"


def test_normalize_planner_response_returns_existing_plan_object():
    plan = {
        "plan": [
            {"day": 1, "city": "Budapest"},
        ]
    }

    result = normalize_planner_response(plan)

    assert result == plan


def test_normalize_planner_response_returns_first_trip():
    plan = {
        "trips": [
            {
                "destination": "Rome",
                "plan": [{"day": 1}],
            }
        ]
    }

    result = normalize_planner_response(plan)

    assert result == {
        "destination": "Rome",
        "plan": [{"day": 1}],
    }


def test_normalize_planner_response_copies_top_level_dates_into_trip():
    plan = {
        "startDate": "2026-07-01",
        "endDate": "2026-07-05",
        "tripLengthDays": 5,
        "trips": [
            {
                "destination": "Paris",
                "plan": [{"day": 1}],
            }
        ],
    }

    result = normalize_planner_response(plan)

    assert result == {
        "destination": "Paris",
        "plan": [{"day": 1}],
        "startDate": "2026-07-01",
        "endDate": "2026-07-05",
        "tripLengthDays": 5,
    }