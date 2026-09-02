from utils.countries import (
    COUNTRY_CODE_TO_NAME,
    country_display_name,
    geocode_country_label,
    normalize_country_code,
    resolve_country_code,
)


def test_normalize_country_code_accepts_iso2():
    assert normalize_country_code("HU") == "HU"
    assert normalize_country_code("it") == "IT"
    assert normalize_country_code("  de  ") == "DE"


def test_normalize_country_code_maps_uk_to_gb():
    assert normalize_country_code("UK") == "GB"
    assert normalize_country_code("uk") == "GB"


def test_normalize_country_code_rejects_names_and_unknown():
    assert normalize_country_code("US") is None
    assert normalize_country_code("Hungary") is None
    assert normalize_country_code("magyarország") is None
    assert normalize_country_code("Hungar") is None
    assert normalize_country_code("") is None
    assert normalize_country_code(None) is None


def test_resolve_country_code_from_name_and_alias():
    assert resolve_country_code("HU") == "HU"
    assert resolve_country_code("Hungary") == "HU"
    assert resolve_country_code("magyarország") == "HU"
    assert resolve_country_code("Italy") == "IT"
    assert resolve_country_code("unknown-land") is None
    assert resolve_country_code("") is None


def test_country_display_name_from_code():
    assert country_display_name("HU") == COUNTRY_CODE_TO_NAME["HU"]
    assert country_display_name("uk") == COUNTRY_CODE_TO_NAME["GB"]


def test_country_display_name_passthrough_unknown():
    assert country_display_name("Somewhere") == "Somewhere"
    assert country_display_name("Hungary") == "Hungary"


def test_geocode_country_label_prefers_english_name():
    assert geocode_country_label("HU") == "Hungary"
    assert geocode_country_label("IT") == "Italy"
