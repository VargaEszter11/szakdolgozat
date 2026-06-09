import pytest

from database.airport_city import airport_name_as_city


@pytest.mark.parametrize(
    ("iata", "expected"),
    [
        ("BUD", "Budapest"),
        ("bud", "Budapest"),
        ("PRG", "Prague"),
        ("TXL", "Berlin"),
        ("WMI", "Warsaw"),
    ],
)
def test_iata_overrides_take_precedence(iata, expected):
    assert airport_name_as_city("Completely Different Name", iata) == expected


def test_empty_name_returns_code():
    assert airport_name_as_city(None, "BUD") == "Budapest"
    assert airport_name_as_city(None, "ABC") == "ABC"


def test_empty_name_and_code_returns_empty_string():
    assert airport_name_as_city(None, None) == ""
    assert airport_name_as_city("", "") == ""


def test_label_equal_to_code_returns_code():
    assert airport_name_as_city("ABC", "ABC") == "ABC"
    assert airport_name_as_city("abc", "ABC") == "ABC"


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("London Heathrow Airport", "London Heathrow"),
        ("Paris Charles de Gaulle Airport", "Paris Charles de Gaulle"),
        ("Madrid-Barajas Airport", "Madrid-Barajas"),
        ("Oslo Lufthavn", "Oslo"),
        ("Berlin Flughafen Brandenburg", "Berlin"),
        ("Springfield Airfield", "Springfield"),
    ],
)
def test_facility_words_are_removed(name, expected):
    assert airport_name_as_city(name, None) == expected


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Paris Central Station", "Paris"),
        ("Berlin Hauptbahnhof", "Berlin"),
        ("Lyon SNCF Station", "Lyon"),
        ("Avignon TGV Station", "Avignon"),
        ("Rome Railway Station", "Rome"),
    ],
)
def test_transport_words_and_following_text_are_removed(name, expected):
    assert airport_name_as_city(name, None) == expected


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Nice International Airport", "Nice"),
        ("Austin Municipal Airport", "Austin"),
        ("Belfast City Regional Airport", "Belfast City"),
        ("Capital National Airport", "Capital"),
        ("Springfield Public Airport", "Springfield"),
    ],
)
def test_descriptive_words_are_removed(name, expected):
    assert airport_name_as_city(name, None) == expected


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Rome/Fiumicino Airport", "Rome"),
        ("Bergamo - Orio al Serio Airport", "Bergamo"),
        ("Bristol / Bath", "Bristol"),
        ("Belfast - City", "Belfast"),
    ],
)
def test_first_place_part_is_used(name, expected):
    assert airport_name_as_city(name, None) == expected


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Budapest Airport (Terminal 2)", "Budapest"),
        ("John F. Kennedy Airport (JFK)", "John F. Kennedy"),
        ('Paris Airport "Charles de Gaulle"', "Paris"),
        ("Rome Airport 'Leonardo da Vinci'", "Rome"),
    ],
)
def test_parentheses_and_quoted_suffixes_are_removed(name, expected):
    assert airport_name_as_city(name, None) == expected


def test_facility_word_uses_text_after_if_before_is_empty():
    assert airport_name_as_city("Airport Split", None) == "Split"


def test_whitespace_is_normalized():
    assert airport_name_as_city(
        "  New   York   International   Airport  ",
        None,
    ) == "New York"


def test_result_falls_back_to_code_if_label_becomes_empty():
    assert airport_name_as_city("International Airport", "XYZ") == "XYZ"


def test_result_can_be_empty_without_code():
    assert airport_name_as_city("International Airport", None) == ""