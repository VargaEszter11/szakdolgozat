from datetime import datetime, timezone

from backend.database import crud
from backend.database.airport_regions import (
    EUROPE_COUNTRY_CODES,
    is_europe_country,
)

def test_hash_password_returns_string():
    hashed = crud.hash_password("secret123")

    assert isinstance(hashed, str)
    assert hashed != "secret123"


def test_hash_password_generates_different_hashes():
    password = "secret123"

    hash1 = crud.hash_password(password)
    hash2 = crud.hash_password(password)

    assert hash1 != hash2


def test_verify_password_accepts_correct_password():
    password = "correct horse battery staple"

    hashed = crud.hash_password(password)

    assert crud.verify_password(password, hashed) is True


def test_verify_password_rejects_wrong_password():
    hashed = crud.hash_password("secret123")

    assert crud.verify_password("wrong-password", hashed) is False


def test_verify_password_rejects_empty_password():
    hashed = crud.hash_password("secret123")

    assert crud.verify_password("", hashed) is False

def test_norm_iata_uppercases():
    assert crud._norm_iata("bud") == "BUD"


def test_norm_iata_strips_whitespace():
    assert crud._norm_iata("  lhr  ") == "LHR"


def test_norm_iata_handles_empty_string():
    assert crud._norm_iata("") == ""


def test_norm_iata_handles_none():
    assert crud._norm_iata(None) == ""

def test_norm_country_uppercases():
    assert crud._norm_country("hu") == "HU"


def test_norm_country_strips_whitespace():
    assert crud._norm_country("  gb  ") == "GB"


def test_norm_country_truncates_long_values():
    assert crud._norm_country("HUN") == "HU"


def test_norm_country_handles_empty_string():
    assert crud._norm_country("") is None


def test_norm_country_handles_none():
    assert crud._norm_country(None) is None

def test_utcnow_returns_datetime():
    now = crud._utcnow()

    assert isinstance(now, datetime)


def test_utcnow_returns_timezone_aware_datetime():
    now = crud._utcnow()

    assert now.tzinfo is not None
    assert now.tzinfo == timezone.utc


def test_utcnow_is_close_to_real_utc_time():
    before = datetime.now(timezone.utc)

    now = crud._utcnow()

    after = datetime.now(timezone.utc)

    assert before <= now <= after

def test_airport_name_as_city_falls_back_to_iata():
    """
    We cannot assume the exact transformation rules of
    airport_name_as_city(), but we can verify the wrapper
    returns a non-empty string.
    """
    result = crud._airport_name_as_city(None, "BUD")

    assert isinstance(result, str)
    assert result != ""


def test_airport_name_as_city_returns_string():
    result = crud._airport_name_as_city(
        "Budapest Ferenc Liszt International Airport",
        "BUD",
    )

    assert isinstance(result, str)
    assert result != ""

def test_europe_country_codes_contains_known_european_countries():
    assert "HU" in EUROPE_COUNTRY_CODES
    assert "GB" in EUROPE_COUNTRY_CODES
    assert "FR" in EUROPE_COUNTRY_CODES
    assert "DE" in EUROPE_COUNTRY_CODES


def test_europe_country_codes_excludes_non_european_countries():
    assert "US" not in EUROPE_COUNTRY_CODES
    assert "JP" not in EUROPE_COUNTRY_CODES
    assert "AU" not in EUROPE_COUNTRY_CODES


def test_is_europe_country_accepts_valid_code():
    assert is_europe_country("HU") is True


def test_is_europe_country_is_case_insensitive():
    assert is_europe_country("hu") is True


def test_is_europe_country_strips_whitespace():
    assert is_europe_country("  gb  ") is True


def test_is_europe_country_rejects_non_european_country():
    assert is_europe_country("US") is False


def test_is_europe_country_rejects_empty_string():
    assert is_europe_country("") is False


def test_is_europe_country_rejects_none():
    assert is_europe_country(None) is False