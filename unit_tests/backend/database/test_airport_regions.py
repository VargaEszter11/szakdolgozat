import pytest

from database.airport_regions import is_europe_country


@pytest.mark.parametrize(
    "input_code,expected",
    [
        ("FR", True),      # valid Europe country
        ("gb", True),      # lowercase input
        (" Gb ", True),    # whitespace + mixed case
        ("US", False),      # non-European country
        ("CA", False),      # non-European country
        ("", False),        # empty string
        (None, False),      # None input
    ],
)
def test_is_europe_country(input_code, expected):
    assert is_europe_country(input_code) is expected