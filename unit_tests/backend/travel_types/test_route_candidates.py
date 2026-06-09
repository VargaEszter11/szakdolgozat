from datetime import date

import pytest

from backend.travel_types.route_candidates import (
    _iata,
    _has_coordinates,
    calculate_distance_km,
    transport_for_ground_distance,
    ground_area,
    can_use_ground_transport,
    can_use_ferry_transport,
    is_europe_country,
    is_plannable_place_label,
    airport_distance,
    ground_transport_between_airports,
    ferry_transport_between_airports,
    ground_candidates_from_airport,
    ferry_candidates_from_airport,
    with_transport,
    europe_candidates,
    dedupe_candidates,
    annotate_distances,
    rank_candidates,
    build_candidates,
)


class FakeAirport:
    def __init__(
        self,
        iata: str = "BUD",
        name: str = "Budapest Airport",
        city: str | None = "Budapest",
        country_code: str | None = "HU",
        latitude: float | None = 47.439,
        longitude: float | None = 19.261,
    ):
        self.iata = iata
        self.name = name
        self.city = city
        self.country_code = country_code
        self.latitude = latitude
        self.longitude = longitude


class FakeQuery:
    def __init__(self, airports):
        self.airports = airports
        self.filtered_iata = None

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        if self.filtered_iata:
            return next((a for a in self.airports if a.iata == self.filtered_iata), None)
        return self.airports[0] if self.airports else None

    def all(self):
        return self.airports


class FakeDB:
    def __init__(self, airports):
        self.airports = airports

    def query(self, model):
        return FakeQuery(self.airports)


def test_iata_normalizes_value():
    assert _iata(" bud ") == "BUD"
    assert _iata(None) == ""


def test_has_coordinates():
    assert _has_coordinates(FakeAirport(latitude=1, longitude=2)) is True
    assert _has_coordinates(FakeAirport(latitude=None, longitude=2)) is False
    assert _has_coordinates(None) is False


def test_is_europe_country():
    assert is_europe_country("HU") is True
    assert is_europe_country("hu") is True
    assert is_europe_country("US") is False
    assert is_europe_country(None) is False


def test_calculate_distance_km_same_point():
    assert calculate_distance_km(47.4979, 19.0402, 47.4979, 19.0402) == pytest.approx(0)


def test_calculate_distance_km_budapest_to_vienna():
    distance = calculate_distance_km(47.4979, 19.0402, 48.2082, 16.3738)

    assert distance == pytest.approx(214, abs=5)


def test_transport_for_ground_distance():
    assert transport_for_ground_distance(250) == "bus"
    assert transport_for_ground_distance(251) == "train"


def test_ground_area_mainland():
    airport = FakeAirport(country_code="HU", latitude=47.4, longitude=19.2)

    assert ground_area(airport) == "mainland"


def test_ground_area_ireland():
    airport = FakeAirport(country_code="IE", latitude=53.3, longitude=-6.2)

    assert ground_area(airport) == "ireland"


def test_ground_area_great_britain():
    airport = FakeAirport(country_code="GB", latitude=51.5, longitude=-0.1)

    assert ground_area(airport) == "great_britain"


def test_ground_area_island_country():
    airport = FakeAirport(country_code="MT", latitude=35.8, longitude=14.5)

    assert ground_area(airport) == "MT"


def test_can_use_ground_transport_same_area():
    origin = FakeAirport(country_code="HU", latitude=47.4, longitude=19.2)
    destination = FakeAirport(country_code="AT", latitude=48.2, longitude=16.3)

    assert can_use_ground_transport(origin, destination) is True


def test_can_use_ground_transport_different_area():
    origin = FakeAirport(country_code="GB", latitude=51.5, longitude=-0.1)
    destination = FakeAirport(country_code="FR", latitude=48.8, longitude=2.3)

    assert can_use_ground_transport(origin, destination) is False


def test_can_use_ferry_transport_different_area():
    origin = FakeAirport(country_code="GB", latitude=51.5, longitude=-0.1)
    destination = FakeAirport(country_code="FR", latitude=48.8, longitude=2.3)

    assert can_use_ferry_transport(origin, destination) is True


def test_can_use_ferry_transport_same_area():
    origin = FakeAirport(country_code="HU", latitude=47.4, longitude=19.2)
    destination = FakeAirport(country_code="AT", latitude=48.2, longitude=16.3)

    assert can_use_ferry_transport(origin, destination) is False


def test_is_plannable_place_label_accepts_city():
    assert is_plannable_place_label("Budapest") is True


def test_is_plannable_place_label_rejects_empty():
    assert is_plannable_place_label("") is False
    assert is_plannable_place_label(None) is False


@pytest.mark.parametrize(
    "label",
    [
        "Budapest Airport",
        "Main Station",
        "Ferry Terminal",
        "Old Port",
        "City Marina",
        "Small Heliport",
    ],
)
def test_is_plannable_place_label_rejects_transport_places(label):
    assert is_plannable_place_label(label) is False


def test_with_transport_adds_transport_when_missing():
    candidates = [{"iata": "BUD", "city": "Budapest"}]

    result = with_transport(candidates, "flight")

    assert result == [{"iata": "BUD", "city": "Budapest", "transport": "flight"}]


def test_with_transport_does_not_overwrite_existing_transport():
    candidates = [{"iata": "BUD", "city": "Budapest", "transport": "train"}]

    result = with_transport(candidates, "flight")

    assert result[0]["transport"] == "train"


def test_with_transport_does_not_mutate_original():
    candidates = [{"iata": "BUD", "city": "Budapest"}]

    with_transport(candidates, "flight")

    assert "transport" not in candidates[0]


def test_europe_candidates_filters_non_europe():
    candidates = [
        {"iata": "BUD", "country": "HU"},
        {"iata": "JFK", "country": "US"},
    ]

    result = europe_candidates(candidates)

    assert result == [{"iata": "BUD", "country": "HU"}]


def test_dedupe_candidates_removes_duplicate_iata():
    candidates = [
        {"iata": "BUD", "city": "Budapest", "country": "HU"},
        {"iata": "BUD", "city": "Budapest", "country": "HU"},
        {"iata": "FCO", "city": "Rome", "country": "IT"},
    ]

    result = dedupe_candidates(candidates)

    assert len(result) == 2
    assert [c["iata"] for c in result] == ["BUD", "FCO"]


def test_dedupe_candidates_keeps_same_iata_for_different_airlines():
    candidates = [
        {"iata": "BUD", "city": "Budapest", "country": "HU", "airline_iata": "FR"},
        {"iata": "BUD", "city": "Budapest", "country": "HU", "airline_iata": "W6"},
    ]

    result = dedupe_candidates(candidates)

    assert len(result) == 2


def test_dedupe_candidates_removes_duplicate_city_country():
    candidates = [
        {"iata": "BUD", "city": "Budapest", "country": "HU"},
        {"iata": "XXX", "city": "Budapest", "country": "HU"},
    ]

    result = dedupe_candidates(candidates)

    assert len(result) == 1
    assert result[0]["iata"] == "BUD"


def test_rank_candidates_prefers_shorter_distance():
    candidates = [
        {"iata": "FCO", "distance_km": 1200},
        {"iata": "VIE", "distance_km": 200},
    ]

    result = rank_candidates(candidates)

    assert result[0]["iata"] == "VIE"


def test_rank_candidates_puts_missing_distance_last():
    candidates = [
        {"iata": "XXX"},
        {"iata": "VIE", "distance_km": 200},
    ]

    result = rank_candidates(candidates)

    assert result[0]["iata"] == "VIE"


def test_rank_candidates_avoids_previous_airport():
    candidates = [
        {"iata": "BUD", "distance_km": 100},
        {"iata": "VIE", "distance_km": 200},
    ]

    result = rank_candidates(candidates, previous_iata="BUD")

    assert result[0]["iata"] == "VIE"


def test_rank_candidates_respects_limit():
    candidates = [
        {"iata": "A", "distance_km": 1},
        {"iata": "B", "distance_km": 2},
        {"iata": "C", "distance_km": 3},
    ]

    result = rank_candidates(candidates, limit=2)

    assert len(result) == 2
    assert [c["iata"] for c in result] == ["A", "B"]


def test_airport_distance_returns_none_when_missing_coordinates(monkeypatch):
    airports = {
        "BUD": FakeAirport(iata="BUD", latitude=47.439, longitude=19.261),
        "XXX": FakeAirport(iata="XXX", latitude=None, longitude=10),
    }

    monkeypatch.setattr(
        "backend.travel_types.route_candidates._airport_by_iata",
        lambda db, iata: airports.get(iata),
    )

    result = airport_distance(None, "BUD", "XXX")

    assert result is None


def test_airport_distance_returns_distance(monkeypatch):
    airports = {
        "BUD": FakeAirport(iata="BUD", latitude=47.439, longitude=19.261),
        "VIE": FakeAirport(iata="VIE", latitude=48.1103, longitude=16.5697),
    }

    monkeypatch.setattr(
        "backend.travel_types.route_candidates._airport_by_iata",
        lambda db, iata: airports.get(iata),
    )

    result = airport_distance(None, "BUD", "VIE")

    assert result == pytest.approx(216, abs=10)


def test_ground_transport_between_airports_returns_none_without_coordinates(monkeypatch):
    airports = {
        "BUD": FakeAirport(iata="BUD", latitude=47.439, longitude=19.261),
        "XXX": FakeAirport(iata="XXX", latitude=None, longitude=10),
    }

    monkeypatch.setattr(
        "backend.travel_types.route_candidates._airport_by_iata",
        lambda db, iata: airports.get(iata),
    )

    result = ground_transport_between_airports(None, "BUD", "XXX")

    assert result is None


def test_ground_transport_between_airports_returns_none_for_different_ground_area(monkeypatch):
    airports = {
        "LHR": FakeAirport(iata="LHR", country_code="GB", latitude=51.47, longitude=-0.45),
        "CDG": FakeAirport(iata="CDG", country_code="FR", latitude=49.0, longitude=2.55),
    }

    monkeypatch.setattr(
        "backend.travel_types.route_candidates._airport_by_iata",
        lambda db, iata: airports.get(iata),
    )

    result = ground_transport_between_airports(None, "LHR", "CDG")

    assert result is None


def test_ground_transport_between_airports_returns_bus(monkeypatch):
    airports = {
        "BUD": FakeAirport(iata="BUD", country_code="HU", latitude=47.439, longitude=19.261),
        "VIE": FakeAirport(iata="VIE", country_code="AT", latitude=48.1103, longitude=16.5697),
    }

    monkeypatch.setattr(
        "backend.travel_types.route_candidates._airport_by_iata",
        lambda db, iata: airports.get(iata),
    )

    result = ground_transport_between_airports(None, "BUD", "VIE")

    assert result == "bus"


def test_ground_transport_between_airports_returns_train(monkeypatch):
    airports = {
        "BUD": FakeAirport(iata="BUD", country_code="HU", latitude=47.439, longitude=19.261),
        "FCO": FakeAirport(iata="FCO", country_code="IT", latitude=41.8, longitude=12.25),
    }

    monkeypatch.setattr(
        "backend.travel_types.route_candidates._airport_by_iata",
        lambda db, iata: airports.get(iata),
    )
    monkeypatch.setattr(
        "backend.travel_types.route_candidates.calculate_distance_km",
        lambda *args: 500,
    )

    result = ground_transport_between_airports(None, "BUD", "FCO")

    assert result == "train"


def test_ground_transport_between_airports_returns_none_when_too_far(monkeypatch):
    airports = {
        "BUD": FakeAirport(iata="BUD", country_code="HU", latitude=47.439, longitude=19.261),
        "MAD": FakeAirport(iata="MAD", country_code="ES", latitude=40.4, longitude=-3.5),
    }

    monkeypatch.setattr(
        "backend.travel_types.route_candidates._airport_by_iata",
        lambda db, iata: airports.get(iata),
    )
    monkeypatch.setattr(
        "backend.travel_types.route_candidates.calculate_distance_km",
        lambda *args: 900,
    )

    result = ground_transport_between_airports(None, "BUD", "MAD")

    assert result is None


def test_ferry_transport_between_airports_returns_ferry(monkeypatch):
    airports = {
        "DUB": FakeAirport(iata="DUB", country_code="IE", latitude=53.4, longitude=-6.2),
        "LPL": FakeAirport(iata="LPL", country_code="GB", latitude=53.3, longitude=-2.8),
    }

    monkeypatch.setattr(
        "backend.travel_types.route_candidates._airport_by_iata",
        lambda db, iata: airports.get(iata),
    )
    monkeypatch.setattr(
        "backend.travel_types.route_candidates.calculate_distance_km",
        lambda *args: 260,
    )

    result = ferry_transport_between_airports(None, "DUB", "LPL")

    assert result == "ferry"


def test_ferry_transport_between_airports_returns_none_when_too_far(monkeypatch):
    airports = {
        "DUB": FakeAirport(iata="DUB", country_code="IE", latitude=53.4, longitude=-6.2),
        "LPL": FakeAirport(iata="LPL", country_code="GB", latitude=53.3, longitude=-2.8),
    }

    monkeypatch.setattr(
        "backend.travel_types.route_candidates._airport_by_iata",
        lambda db, iata: airports.get(iata),
    )
    monkeypatch.setattr(
        "backend.travel_types.route_candidates.calculate_distance_km",
        lambda *args: 900,
    )

    result = ferry_transport_between_airports(None, "DUB", "LPL")

    assert result is None


def test_ground_candidates_from_airport(monkeypatch):
    origin = FakeAirport(iata="BUD", city="Budapest", country_code="HU", latitude=47.439, longitude=19.261)
    vienna = FakeAirport(iata="VIE", city="Vienna", country_code="AT", latitude=48.1103, longitude=16.5697)
    rome = FakeAirport(iata="FCO", city="Rome", country_code="IT", latitude=41.8, longitude=12.25)
    us_city = FakeAirport(iata="JFK", city="New York", country_code="US", latitude=40.6, longitude=-73.7)
    airport_city = FakeAirport(iata="BAD", city="Some Airport", country_code="HU", latitude=47.5, longitude=19.3)

    class Query:
        def filter(self, *args, **kwargs):
            return self

        def all(self):
            return [origin, vienna, rome, us_city, airport_city]

    class DB:
        def query(self, model):
            return Query()

    monkeypatch.setattr(
        "backend.travel_types.route_candidates._airport_by_iata",
        lambda db, iata: origin if iata == "BUD" else None,
    )

    def fake_distance(lat1, lng1, lat2, lng2):
        if lat2 == vienna.latitude:
            return 220
        if lat2 == rome.latitude:
            return 700
        if lat2 == airport_city.latitude:
            return 20
        return 1000

    monkeypatch.setattr(
        "backend.travel_types.route_candidates.calculate_distance_km",
        fake_distance,
    )

    result = ground_candidates_from_airport(
        DB(),
        "BUD",
        excluded_iatas=set(),
    )

    assert result == [
        {
            "iata": "VIE",
            "city": "Vienna",
            "country": "AT",
            "transport": "bus",
            "distance_km": 220,
        }
    ]


def test_ferry_candidates_from_airport(monkeypatch):
    origin = FakeAirport(iata="DUB", city="Dublin", country_code="IE", latitude=53.4, longitude=-6.2)
    liverpool = FakeAirport(iata="LPL", city="Liverpool", country_code="GB", latitude=53.3, longitude=-2.8)
    cork = FakeAirport(iata="ORK", city="Cork", country_code="IE", latitude=51.8, longitude=-8.5)

    class Query:
        def filter(self, *args, **kwargs):
            return self

        def all(self):
            return [origin, liverpool, cork]

    class DB:
        def query(self, model):
            return Query()

    monkeypatch.setattr(
        "backend.travel_types.route_candidates._airport_by_iata",
        lambda db, iata: origin if iata == "DUB" else None,
    )
    monkeypatch.setattr(
        "backend.travel_types.route_candidates.calculate_distance_km",
        lambda *args: 250,
    )

    result = ferry_candidates_from_airport(
        DB(),
        "DUB",
        excluded_iatas=set(),
    )

    assert result == [
        {
            "iata": "LPL",
            "city": "Liverpool",
            "country": "GB",
            "transport": "ferry",
            "distance_km": 250,
        }
    ]


def test_ground_candidates_from_airport_returns_empty_without_origin_coordinates(monkeypatch):
    monkeypatch.setattr(
        "backend.travel_types.route_candidates._airport_by_iata",
        lambda db, iata: FakeAirport(latitude=None, longitude=19.261),
    )

    result = ground_candidates_from_airport(
        db=None,
        origin_iata="BUD",
        excluded_iatas=set(),
    )

    assert result == []


def test_annotate_distances_adds_missing_distance(monkeypatch):
    monkeypatch.setattr(
        "backend.travel_types.route_candidates.airport_distance",
        lambda db, origin, destination: 123.45,
    )

    result = annotate_distances(
        db=None,
        origin_iata="BUD",
        candidates=[{"iata": "VIE"}],
    )

    assert result == [{"iata": "VIE", "distance_km": 123.5}]


def test_annotate_distances_keeps_existing_distance(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("airport_distance should not be called")

    monkeypatch.setattr(
        "backend.travel_types.route_candidates.airport_distance",
        fail_if_called,
    )

    result = annotate_distances(
        db=None,
        origin_iata="BUD",
        candidates=[{"iata": "VIE", "distance_km": 220}],
    )

    assert result == [{"iata": "VIE", "distance_km": 220}]


@pytest.mark.asyncio
async def test_build_candidates_combines_ground_and_flight_candidates(monkeypatch):
    async def fake_get_direct_destinations_cached(db, current_airport):
        return [
            {"iata": "FCO", "city": "Rome", "country": "IT"},
            {"iata": "JFK", "city": "New York", "country": "US"},
            {"iata": "HUB", "city": "Hub City", "country": "HU"},
            {"iata": "USED", "city": "Used City", "country": "HU"},
        ]

    monkeypatch.setattr(
        "backend.travel_types.route_candidates.get_direct_destinations_cached",
        fake_get_direct_destinations_cached,
    )

    monkeypatch.setattr(
        "backend.travel_types.route_candidates.ground_candidates_from_airport",
        lambda *args, **kwargs: [
            {
                "iata": "VIE",
                "city": "Vienna",
                "country": "AT",
                "transport": "bus",
                "distance_km": 220,
            },
            {
                "iata": "BAD",
                "city": "Some Airport",
                "country": "AT",
                "transport": "bus",
                "distance_km": 100,
            },
        ],
    )
    monkeypatch.setattr(
        "backend.travel_types.route_candidates.ferry_candidates_from_airport",
        lambda *args, **kwargs: [],
    )

    result = await build_candidates(
        db=None,
        strategy="random",
        current_airport="BUD",
        hub_iata="HUB",
        used_iatas={"USED"},
        visited_places=[],
        forbidden_places=[],
    )

    assert result == [
        {
            "iata": "VIE",
            "city": "Vienna",
            "country": "AT",
            "transport": "bus",
            "distance_km": 220,
        },
        {
            "iata": "FCO",
            "city": "Rome",
            "country": "IT",
            "transport": "flight",
        },
    ]


@pytest.mark.asyncio
async def test_build_candidates_skips_direct_routes_for_train_bus(monkeypatch):
    async def fail_if_called(db, current_airport):
        raise AssertionError("direct routes should not be loaded for trainBus")

    monkeypatch.setattr(
        "backend.travel_types.route_candidates.get_direct_destinations_cached",
        fail_if_called,
    )
    monkeypatch.setattr(
        "backend.travel_types.route_candidates.ground_candidates_from_airport",
        lambda *args, **kwargs: [
            {
                "iata": "VIE",
                "city": "Vienna",
                "country": "AT",
                "transport": "bus",
                "distance_km": 220,
            }
        ],
    )
    monkeypatch.setattr(
        "backend.travel_types.route_candidates.ferry_candidates_from_airport",
        lambda *args, **kwargs: [],
    )

    result = await build_candidates(
        db=None,
        strategy="random",
        current_airport="BUD",
        hub_iata="HUB",
        used_iatas=set(),
        visited_places=[],
        forbidden_places=[],
        preferred_transport="trainBus",
    )

    assert result == [
        {
            "iata": "VIE",
            "city": "Vienna",
            "country": "AT",
            "transport": "bus",
            "distance_km": 220,
        }
    ]


@pytest.mark.asyncio
async def test_build_candidates_skips_direct_routes_for_train_bus_ferry(monkeypatch):
    async def fail_if_called(db, current_airport):
        raise AssertionError("direct routes should not be loaded for trainBusFerry")

    monkeypatch.setattr(
        "backend.travel_types.route_candidates.get_direct_destinations_cached",
        fail_if_called,
    )
    monkeypatch.setattr(
        "backend.travel_types.route_candidates.ground_candidates_from_airport",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        "backend.travel_types.route_candidates.ferry_candidates_from_airport",
        lambda *args, **kwargs: [
            {
                "iata": "LPL",
                "city": "Liverpool",
                "country": "GB",
                "transport": "ferry",
                "distance_km": 250,
            }
        ],
    )

    result = await build_candidates(
        db=None,
        strategy="random",
        current_airport="DUB",
        hub_iata="HUB",
        used_iatas=set(),
        visited_places=[],
        forbidden_places=[],
        preferred_transport="trainBusFerry",
    )

    assert result == [
        {
            "iata": "LPL",
            "city": "Liverpool",
            "country": "GB",
            "transport": "ferry",
            "distance_km": 250,
        }
    ]


@pytest.mark.asyncio
async def test_build_candidates_uses_random_filter_when_strategy_is_visited(monkeypatch):
    captured = {}

    async def fake_get_direct_destinations_cached(db, current_airport):
        return [{"iata": "FCO", "city": "Rome", "country": "IT"}]

    def fake_filter_strategy_candidates(strategy, raw_dests, visited_places, forbidden_places):
        captured.setdefault("strategies", []).append(strategy)
        return raw_dests

    monkeypatch.setattr(
        "backend.travel_types.route_candidates.get_direct_destinations_cached",
        fake_get_direct_destinations_cached,
    )
    monkeypatch.setattr(
        "backend.travel_types.route_candidates.ground_candidates_from_airport",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        "backend.travel_types.route_candidates.ferry_candidates_from_airport",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        "backend.travel_types.route_candidates.filter_strategy_candidates",
        fake_filter_strategy_candidates,
    )

    await build_candidates(
        db=None,
        strategy="visited",
        current_airport="BUD",
        hub_iata="BUD",
        used_iatas=set(),
        visited_places=["Rome"],
        forbidden_places=[],
    )

    assert captured["strategies"] == ["random", "random", "random"]