"""Flight availability and booking-link helpers for travel planning."""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from database import models


def seasonality_status(is_seasonal: Optional[bool]) -> str:
    if is_seasonal is True:
        return "seasonal"
    if is_seasonal is False:
        return "year_round"
    return "unknown"


def _people_count(people: int = 1) -> int:
    try:
        count = int(people)
    except (TypeError, ValueError):
        count = 1
    return max(1, count)


def _skyscanner_date(departure_date: str) -> Optional[str]:
    try:
        return date.fromisoformat(str(departure_date)).strftime("%y%m%d")
    except (TypeError, ValueError):
        return None


def booking_url(
    airline_iata: Optional[str],
    origin: str,
    destination: str,
    departure_date: str,
    people: int = 1,
) -> Optional[str]:
    airline = (airline_iata or "").strip().upper()
    origin = (origin or "").strip().upper()
    destination = (destination or "").strip().upper()
    people = _people_count(people)
    if not origin or not destination or not departure_date:
        return None

    if airline == "FR":
        return (
            "https://www.ryanair.com/gb/en/trip/flights/select"
            f"?adults={people}&teens=0&children=0&infants=0&dateOut={departure_date}"
            f"&originIata={origin}&destinationIata={destination}"
            "&isConnectedFlight=false&discount=0&promoCode="
        )
    if airline == "W6":
        return (
            "https://wizzair.com/en-gb/booking/select-flight/"
            f"{origin}/{destination}/{departure_date}/null/{people}/0/0/null"
        )

    skyscanner_date = _skyscanner_date(departure_date)
    if not skyscanner_date:
        return None
    params = urlencode(
        {
            "adultsv2": people,
            "adults": people,
            "cabinclass": "economy",
            "childrenv2": "",
            "children": 0,
            "inboundaltsenabled": "false",
            "outboundaltsenabled": "false",
            "preferdirects": "false",
            "ref": "home",
            "rtn": 0,
        }
    )
    return (
        "https://www.skyscanner.net/transport/flights/"
        f"{origin.lower()}/{destination.lower()}/{skyscanner_date}/?{params}"
    )


def direct_route_for_leg(db, origin: str, destination: str, airline_iata: Optional[str] = None):
    query = db.query(models.DirectRoute).filter(
        models.DirectRoute.origin_iata == (origin or "").strip().upper(),
        models.DirectRoute.destination_iata == (destination or "").strip().upper(),
        models.DirectRoute.is_active.is_(True),
    )
    airline = (airline_iata or "").strip().upper()
    if airline:
        query = query.filter(models.DirectRoute.airline_iata == airline)
    return query.order_by(
        models.DirectRoute.airline_iata.is_(None),
        models.DirectRoute.airline_iata,
    ).first()


def route_operates_on_date(route, departure_date: str) -> bool:
    if not route:
        return False
    try:
        parsed_date = date.fromisoformat(departure_date)
    except (TypeError, ValueError):
        return False

    if route.effective_from and parsed_date < route.effective_from:
        return False
    if route.effective_to and parsed_date > route.effective_to:
        return False

    operating_days = list(route.operating_days or [])
    if not operating_days:
        return True

    return any(day.weekday == parsed_date.isoweekday() for day in operating_days)


def route_availability_verified(route) -> bool:
    return bool(route and list(route.operating_days or []))


def available_flight_candidates(
    db,
    origin: str,
    candidates: List[dict],
    departure_date: str,
) -> List[dict]:
    return [
        candidate
        for candidate in candidates
        if (candidate.get("transport") or "flight") == "flight"
        and route_operates_on_date(
            direct_route_for_leg(
                db,
                origin,
                candidate.get("iata"),
                candidate.get("airline_iata"),
            ),
            departure_date,
        )
    ]


def flight_booking_details(
    db,
    origin: str,
    destination: str,
    departure_date: str,
    airline_iata: Optional[str] = None,
    people: int = 1,
) -> dict:
    route = direct_route_for_leg(db, origin, destination, airline_iata)
    if not route_operates_on_date(route, departure_date):
        return {}

    return {
        "origin_airport_iata": route.origin_iata,
        "destination_airport_iata": route.destination_iata,
        "airline_iata": route.airline_iata,
        "airline_name": route.airline_name,
        "is_seasonal_route": route.is_seasonal,
        "seasonality_status": seasonality_status(route.is_seasonal),
        "effective_from": route.effective_from.isoformat() if route.effective_from else None,
        "effective_to": route.effective_to.isoformat() if route.effective_to else None,
        "booking_url": booking_url(
            route.airline_iata,
            route.origin_iata,
            route.destination_iata,
            departure_date,
            people,
        ),
        "flight_availability_verified": route_availability_verified(route),
    }


def refresh_booking_details(
    db,
    plan: List[Dict[str, Any]],
    starting_airport_iata: str,
    people: int = 1,
) -> None:
    previous_iata = starting_airport_iata
    for stop in plan:
        selected_airline_iata = stop.get("airline_iata")
        clear_booking_details(stop)
        transport = (stop.get("transportFromPreviousCity") or "").strip().lower()
        destination_iata = (stop.get("iata") or "").strip().upper()
        travel_date = stop.get("arrivalDate")

        if transport == "flight" and previous_iata and destination_iata and travel_date:
            stop.update(
                flight_booking_details(
                    db,
                    previous_iata,
                    destination_iata,
                    travel_date,
                    selected_airline_iata,
                    people,
                )
            )

        if destination_iata:
            previous_iata = destination_iata


def clear_booking_details(stop: Dict[str, Any]) -> None:
    for key in (
        "origin_airport_iata",
        "destination_airport_iata",
        "airline_iata",
        "airline_name",
        "booking_url",
        "flight_availability_verified",
    ):
        stop.pop(key, None)
