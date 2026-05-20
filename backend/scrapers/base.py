from database import models
from database.database import SessionLocal


def _airline_name(airline_iata: str, airline_names: dict | None = None) -> str:
    airline_names = airline_names or {}
    return airline_names.get(airline_iata) or airline_iata


def _ensure_airline(db, airline_iata: str, airline_names: dict | None = None):
    airline = db.query(models.Airline).filter(models.Airline.iata == airline_iata).first()
    if airline:
        return airline

    airline = models.Airline(
        iata=airline_iata,
        name=_airline_name(airline_iata, airline_names),
    )
    db.add(airline)
    return airline


def save_routes(routes, *, db=None, default_airline_iata=None, airline_names=None):
    owns_session = db is None
    db = db or SessionLocal()
    stats = {
        "fetched": len(routes),
        "inserted": 0,
        "updated": 0,
        "skipped": 0,
    }

    try:
        normalized_routes = []
        seen = set()
        for route in routes:
            airline_iata = (route.get("airline_iata") or default_airline_iata or "").strip().upper()
            origin_iata = (route.get("origin_iata") or "").strip().upper()
            destination_iata = (route.get("destination_iata") or "").strip().upper()

            key = (origin_iata, destination_iata)
            if (
                not airline_iata
                or not origin_iata
                or not destination_iata
                or origin_iata == destination_iata
                or key in seen
            ):
                stats["skipped"] += 1
                continue

            seen.add(key)
            normalized_routes.append(
                {
                    "airline_iata": airline_iata,
                    "origin_iata": origin_iata,
                    "destination_iata": destination_iata,
                }
            )

        airline_iatas = {route["airline_iata"] for route in normalized_routes}
        airport_iatas = {
            iata
            for route in normalized_routes
            for iata in (route["origin_iata"], route["destination_iata"])
        }

        for airline_iata in airline_iatas:
            _ensure_airline(db, airline_iata, airline_names)

        existing_airports = {
            row.iata
            for row in db.query(models.Airport.iata)
            .filter(models.Airport.iata.in_(list(airport_iatas)))
            .all()
        }
        for airport_iata in sorted(airport_iatas - existing_airports):
            db.add(models.Airport(iata=airport_iata, name=airport_iata))

        db.flush()

        for route in normalized_routes:
            airline_iata = route["airline_iata"]
            origin_iata = route["origin_iata"]
            destination_iata = route["destination_iata"]
            db_route = (
                db.query(models.DirectRoute)
                .filter(
                    models.DirectRoute.origin_iata == origin_iata,
                    models.DirectRoute.destination_iata == destination_iata,
                )
                .first()
            )
            if db_route:
                db_route.airline_iata = airline_iata
                db_route.airline_name = _airline_name(airline_iata, airline_names)
                db_route.flight_number = db_route.flight_number or "DIRECT"
                db_route.is_active = True
                stats["updated"] += 1
            else:
                db.add(
                    models.DirectRoute(
                        airline_iata=airline_iata,
                        airline_name=_airline_name(airline_iata, airline_names),
                        flight_number="DIRECT",
                        origin_iata=origin_iata,
                        destination_iata=destination_iata,
                        is_active=True,
                    )
                )
                stats["inserted"] += 1

        db.commit()
        return stats
    except Exception:
        db.rollback()
        raise
    finally:
        if owns_session:
            db.close()
