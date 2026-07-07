"""
Integration tests for booking helpers with persisted route data.
"""
from travel_types.booking import (
    available_flight_candidates,
    direct_route_for_leg,
    flight_booking_details,
    refresh_booking_details,
    route_operates_on_date,
)


class TestBookingWithDatabase:
    """Booking helpers integrated with persisted airlines and routes."""

    def test_direct_route_for_leg_from_database(self, db, bud_fco_route):
        route = direct_route_for_leg(db, "BUD", "FCO")

        assert route is not None
        assert route.origin_iata == "BUD"
        assert route.destination_iata == "FCO"
        assert route.airline_iata == "FR"

    def test_direct_route_for_leg_filters_by_airline(self, db, bud_fco_route):
        route = direct_route_for_leg(db, "BUD", "FCO", airline_iata="FR")

        assert route is not None
        assert route.airline_iata == "FR"

        missing = direct_route_for_leg(db, "BUD", "FCO", airline_iata="W6")

        assert missing is None

    def test_route_operates_on_date_with_database_schedule(self, db, bud_fco_route):
        assert route_operates_on_date(bud_fco_route, "2026-08-12") is True
        assert route_operates_on_date(bud_fco_route, "2026-08-13") is False

    def test_flight_booking_details_from_database(self, db, bud_fco_route):
        details = flight_booking_details(
            db,
            origin="BUD",
            destination="FCO",
            departure_date="2026-08-12",
            people=2,
        )

        assert details["origin_airport_iata"] == "BUD"
        assert details["destination_airport_iata"] == "FCO"
        assert details["airline_iata"] == "FR"
        assert details["seasonality_status"] == "year_round"
        assert details["flight_availability_verified"] is True
        assert "bud/fco/260812" in details["booking_url"]
        assert "adultsv2=2" in details["booking_url"]

    def test_flight_booking_details_empty_when_route_not_operating(self, db, bud_fco_route):
        details = flight_booking_details(
            db,
            origin="BUD",
            destination="FCO",
            departure_date="2026-08-13",
        )

        assert details == {}

    def test_available_flight_candidates_filters_by_operating_days(self, db, bud_fco_route):
        candidates = [
            {"iata": "FCO", "transport": "flight", "airline_iata": "FR"},
            {"iata": "VIE", "transport": "flight", "airline_iata": "FR"},
        ]

        available = available_flight_candidates(db, "BUD", candidates, "2026-08-12")

        assert len(available) == 1
        assert available[0]["iata"] == "FCO"

    def test_refresh_booking_details_updates_plan_stops(self, db, bud_fco_route):
        plan = [
            {
                "city": "Rome",
                "iata": "FCO",
                "transportFromPreviousCity": "flight",
                "arrivalDate": "2026-08-12",
            }
        ]

        refresh_booking_details(db, plan, starting_airport_iata="BUD", people=2)

        stop = plan[0]
        assert stop["origin_airport_iata"] == "BUD"
        assert stop["destination_airport_iata"] == "FCO"
        assert stop["airline_iata"] == "FR"
        assert stop["flight_availability_verified"] is True
        assert "booking_url" in stop
