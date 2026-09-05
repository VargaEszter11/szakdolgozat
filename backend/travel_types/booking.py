"""Flight availability and booking-link helpers for travel planning.

Outbound legs require a matching active ``direct_routes`` row for the travel
date. Return-home may fall back to an unverified Skyscanner link when no route
exists. Links use Skyscanner's /origin/dest/YYMMDD/ URL shape.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from database import models

# Skyscanner links embed the date as a /YYMMDD/ path segment.
_SKYSCANNER_DATE_RE = re.compile(r"(/[a-z]{3}/[a-z]{3}/)(\d{6})(/)")


def seasonality_status(is_seasonal: Optional[bool]) -> str:
    if is_seasonal is True:
        return "seasonal"
    if is_seasonal is False:
        return "year_round"
    return "unknown"


def _people_count(people: Optional[int] = 1) -> int:
    if people is None:
        return 1
    return max(1, people)


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
    """Build a Skyscanner search URL. ``airline_iata`` is reserved for future direct-airline links."""
    origin = (origin or "").strip().upper()
    destination = (destination or "").strip().upper()
    people = _people_count(people)
    skyscanner_date = _skyscanner_date(departure_date)
    if not origin or not destination or not skyscanner_date:
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


def update_booking_url_date(url: Optional[str], new_departure_date: str) -> Optional[str]:
    """Patch just the date segment of an existing booking_url in place.

    Used when a stop's arrival date is edited after the trip was generated:
    the origin/destination/people/airline parts stay whatever was already
    resolved, only the embedded departure date needs to move. Handles both
    URL shapes seen in stored data: a "dateOut" query param (airline direct
    booking links, e.g. Ryanair) and Skyscanner's /YYMMDD/ path segment.
    """
    if not url:
        return url
    try:
        new_date = date.fromisoformat(str(new_departure_date))
    except (TypeError, ValueError):
        return url

    parts = urlsplit(url)
    query_pairs = parse_qsl(parts.query, keep_blank_values=True)
    if any(key == "dateOut" for key, _ in query_pairs):
        new_query = urlencode(
            [(k, new_date.isoformat() if k == "dateOut" else v) for k, v in query_pairs]
        )
        return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))

    skyscanner_date = new_date.strftime("%y%m%d")
    patched, count = _SKYSCANNER_DATE_RE.subn(
        lambda m: m.group(1) + skyscanner_date + m.group(3), url, count=1
    )
    return patched if count else url


_PEOPLE_QUERY_KEYS = frozenset(
    {
        "adultsv2",
        "adults",
        "AdultCount",
        "adultCount",
        "ADT",
        "passengers",
        "travellers",
        "travelers",
    }
)


def update_booking_url_people(url: Optional[str], people: int) -> Optional[str]:
    """Patch adult/traveller query params on an existing booking_url."""
    if not url:
        return url
    people = _people_count(people)
    parts = urlsplit(url)
    query_pairs = parse_qsl(parts.query, keep_blank_values=True)
    if not query_pairs:
        return url

    changed = False
    new_pairs = []
    for key, value in query_pairs:
        if key in _PEOPLE_QUERY_KEYS:
            new_pairs.append((key, str(people)))
            changed = True
        else:
            new_pairs.append((key, value))

    if not changed:
        return url
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(new_pairs), parts.fragment)
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
    """False when the leg is outside the route's seasonal effective window."""
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

    return True


def available_flight_candidates(
    db,
    origin: str,
    candidates: List[dict],
    departure_date: str,
) -> List[dict]:
    """Keep only flight candidates with a DB route that operates on ``departure_date``."""
    return [
        candidate
        for candidate in candidates
        if (candidate.get("transport") or "flight") == "flight"
        and route_operates_on_date(
            direct_route_for_leg(
                db,
                origin,
                candidate.get("iata") or "",
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
    """Attach booking metadata for a verified direct route, or {} if none operates that day.

    Empty dict causes plan_builder to skip the flight leg entirely.
    """
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
        "flight_availability_verified": False,
    }


def _soft_flight_booking_details(
    db,
    origin: str,
    destination: str,
    departure_date: str,
    people: int = 1,
) -> dict:
    """Skyscanner link without insisting on a cached route (used for return-home fallback)."""
    origin_code = (origin or "").strip().upper()
    destination_code = (destination or "").strip().upper()
    if not origin_code or not destination_code or origin_code == destination_code:
        return {}

    route = direct_route_for_leg(db, origin_code, destination_code)
    if route:
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
            "flight_availability_verified": False,
        }

    # No DB route — still offer a generic Skyscanner search for the airport pair.
    url = booking_url(None, origin_code, destination_code, departure_date, people)
    if not url:
        return {}
    return {
        "origin_airport_iata": origin_code,
        "destination_airport_iata": destination_code,
        "booking_url": url,
        "flight_availability_verified": False,
    }


def return_flight_booking_details(
    db,
    origin: str,
    destination: str,
    departure_date: str,
    airline_iata: Optional[str] = None,
    people: int = 1,
    *,
    allow_unverified: bool = False,
) -> dict:
    """Resolve return-home flight details, optionally allowing soft/unverified links."""
    details = flight_booking_details(
        db, origin, destination, departure_date, airline_iata, people
    )
    if details or not allow_unverified:
        return details
    return _soft_flight_booking_details(db, origin, destination, departure_date, people)


def refresh_booking_details(
    db,
    plan: List[Dict[str, Any]],
    starting_airport_iata: str,
    people: int = 1,
) -> None:
    """Recompute flight URLs after dates are finalized at the end of ``build_plan``."""
    previous_iata = starting_airport_iata
    for stop in plan:
        selected_airline_iata = stop.get("airline_iata")
        clear_booking_details(stop)
        transport = (stop.get("transportFromPreviousCity") or "").strip().lower()
        destination_iata = (stop.get("iata") or "").strip().upper()
        travel_date = stop.get("arrivalDate")
        is_return_home = bool(stop.get("is_return_home"))

        if transport == "flight" and previous_iata and destination_iata and travel_date:
            stop.update(
                return_flight_booking_details(
                    db,
                    previous_iata,
                    destination_iata,
                    travel_date,
                    selected_airline_iata,
                    people,
                    # Return leg may lack a cached route; still show a check-availability link.
                    allow_unverified=is_return_home,
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


def _transport_is_flight(transport: Optional[str]) -> bool:
    return "flight" in (transport or "").strip().lower()


def _iata_for_coords(db, lat: Any, lon: Any) -> Optional[str]:
    from utils.nearest_airport import nearest_airport

    if lat is None or lon is None:
        return None
    airport = nearest_airport(lat, lon, db=db)
    if not airport:
        return None
    return ((airport.get("iata") or "").strip().upper() or None)


def _iata_for_place_name(db, place_name: Optional[str]) -> Optional[str]:
    label = (place_name or "").strip()
    if not label:
        return None

    if len(label) == 3 and label.isalpha():
        row = (
            db.query(models.Airport)
            .filter(models.Airport.iata == label.upper())
            .first()
        )
        if row is not None:
            return str(row.iata).upper()

    row = (
        db.query(models.Airport)
        .filter(models.Airport.city.isnot(None))
        .filter(models.Airport.city.ilike(label))
        .first()
    )
    if row is not None:
        return str(row.iata).upper()
    return None


def _iata_for_stop(db, stop: Any) -> Optional[str]:
    iata = _iata_for_coords(db, getattr(stop, "latitude", None), getattr(stop, "longitude", None))
    if iata:
        return iata
    return _iata_for_place_name(db, getattr(stop, "place_name", None))


def refresh_planned_trip_booking_links(db, trip: Any) -> None:
    """Rebuild flight booking_url on every stop from current trip state.

    Used after trip/stop edits so new stops, reordered legs, date changes, and
    traveller count changes all get fresh Skyscanner links. Soft/unverified
    links are allowed so manually added stops still get a useful search URL.
    """
    if trip is None:
        return

    people = _people_count(getattr(trip, "people", 1))
    stops = list(getattr(trip, "stops", None) or [])
    if not stops and getattr(trip, "id", None) is not None:
        stops = (
            db.query(models.PlannedTripStop)
            .filter(models.PlannedTripStop.trip_id == int(trip.id))
            .all()
        )
    stops = sorted(
        stops,
        key=lambda s: (
            getattr(s, "stop_order", None) is None,
            getattr(s, "stop_order", None) or 0,
            getattr(s, "id", None) or 0,
        ),
    )

    previous_iata = _iata_for_coords(
        db, getattr(trip, "start_latitude", None), getattr(trip, "start_longitude", None)
    )
    if not previous_iata:
        previous_iata = _iata_for_place_name(db, getattr(trip, "start_city", None))

    for stop in stops:
        dest_iata = _iata_for_stop(db, stop)
        travel_date = getattr(stop, "arrival_date", None)
        is_flight = _transport_is_flight(getattr(stop, "transport_from_last", None))

        stop.booking_url = None
        stop.flight_availability_verified = None

        if is_flight and previous_iata and dest_iata and travel_date:
            details = return_flight_booking_details(
                db,
                previous_iata,
                dest_iata,
                str(travel_date),
                None,
                people,
                # Edits may invent legs without a cached route; still offer a search link.
                allow_unverified=True,
            )
            if details.get("booking_url"):
                stop.booking_url = details["booking_url"]
                stop.flight_availability_verified = details.get(
                    "flight_availability_verified"
                )

        if dest_iata:
            previous_iata = dest_iata
