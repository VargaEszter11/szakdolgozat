"""Manual loader for European AirLabs airport/airline/route data.

Usage from the project root:
    python backend/scripts/load_airlabs_europe.py --dry-run
    python backend/scripts/load_airlabs_europe.py

Set AIRLABS_API_KEY in .env before running. This script is not imported by
FastAPI startup and should only be run intentionally from CLI.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import date, time as dt_time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set

import httpx
from dotenv import load_dotenv
from sqlalchemy.orm import Session

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv()

from database import crud, models  # noqa: E402
from database.database import SessionLocal  # noqa: E402


AIRLABS_BASE_URL = os.getenv("AIRLABS_BASE_URL", "https://airlabs.co/api/v9").rstrip("/")
AIRLABS_API_KEY = os.getenv("AIRLABS_API_KEY", "")
DEFAULT_PROGRESS_FILE = BACKEND_DIR / "scripts" / ".airlabs_routes_completed.txt"

EUROPE_COUNTRY_CODES = {
    "AL", "AD", "AT", "BY", "BE", "BA", "BG", "HR", "CY", "CZ", "DK", "EE",
    "FI", "FR", "DE", "GR", "HU", "IS", "IE", "IT", "XK", "LV", "LI", "LT",
    "LU", "MT", "MD", "MC", "ME", "NL", "MK", "NO", "PL", "PT", "RO", "RU",
    "SM", "RS", "SK", "SI", "ES", "SE", "CH", "TR", "UA", "GB", "VA",
}

DAY_TO_WEEKDAY = {
    "mon": 1,
    "tue": 2,
    "wed": 3,
    "thu": 4,
    "fri": 5,
    "sat": 6,
    "sun": 7,
}


def norm_code(value: Any, length: int) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip().upper()
    if not s:
        return None
    return s[:length]


def parse_time(value: Any) -> Optional[dt_time]:
    if not value:
        return None
    try:
        parts = str(value).strip().split(":")
        if len(parts) < 2:
            return None
        return dt_time(hour=int(parts[0]), minute=int(parts[1]))
    except (TypeError, ValueError):
        return None


def parse_date(value: Any) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except ValueError:
        return None


def load_completed_origins(progress_file: Path) -> Set[str]:
    if not progress_file.exists():
        return set()
    return {
        code
        for line in progress_file.read_text(encoding="utf-8").splitlines()
        if (code := norm_code(line, 3))
    }


def mark_origin_completed(progress_file: Path, origin_iata: str) -> None:
    code = norm_code(origin_iata, 3)
    if not code:
        return
    progress_file.parent.mkdir(parents=True, exist_ok=True)
    completed = load_completed_origins(progress_file)
    if code in completed:
        return
    with progress_file.open("a", encoding="utf-8") as fh:
        fh.write(code + "\n")


class AirLabsClient:
    def __init__(self, api_key: str, *, timeout: float = 30.0, pause_seconds: float = 0.2):
        if not api_key:
            raise RuntimeError("AIRLABS_API_KEY is not set. Add it to .env before running.")
        self.api_key = api_key
        self.pause_seconds = pause_seconds
        self.client = httpx.Client(timeout=timeout)

    def close(self) -> None:
        self.client.close()

    def get(self, endpoint: str, **params: Any) -> Dict[str, Any]:
        req_params = {k: v for k, v in params.items() if v is not None}
        req_params["api_key"] = self.api_key
        response = self.client.get(f"{AIRLABS_BASE_URL}/{endpoint.lstrip('/')}", params=req_params)
        response.raise_for_status()
        time.sleep(self.pause_seconds)
        payload = response.json()
        if isinstance(payload, dict) and payload.get("error"):
            raise RuntimeError(f"AirLabs {endpoint} error: {payload['error']}")
        return payload if isinstance(payload, dict) else {"response": payload}


def response_rows(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = payload.get("response", [])
    return rows if isinstance(rows, list) else []


def has_more(payload: Dict[str, Any], row_count: int, limit: int) -> bool:
    request = payload.get("request") if isinstance(payload, dict) else None
    if isinstance(request, dict) and "has_more" in request:
        return bool(request.get("has_more"))
    return row_count >= limit


def upsert_airline(db: Session, item: Dict[str, Any]) -> Optional[models.Airline]:
    iata = norm_code(item.get("iata_code") or item.get("iata"), 2)
    name = (item.get("name") or "").strip()
    if not iata or not name:
        return None
    row = db.query(models.Airline).filter(models.Airline.iata == iata).first()
    if row is None:
        row = models.Airline(iata=iata, name=name)
        db.add(row)
    row.icao = norm_code(item.get("icao_code") or item.get("icao"), 3)
    row.name = name
    row.website = item.get("website") or row.website
    return row


def upsert_airline_batch(db: Session, items: Sequence[Dict[str, Any]]) -> Dict[str, str]:
    """Upsert unique airlines from one API response.

    AirLabs can return duplicate IATA rows. This project uses autoflush=False, so
    deduping in memory avoids adding the same primary key twice before commit.
    """
    unique: Dict[str, Dict[str, Any]] = {}
    names: Dict[str, str] = {}
    for item in items:
        iata = norm_code(item.get("iata_code") or item.get("iata"), 2)
        name = item.get("name")
        if not iata or not name:
            continue
        if iata not in unique:
            unique[iata] = item
            names[iata] = str(name)

    existing = {
        row.iata: row
        for row in db.query(models.Airline)
        .filter(models.Airline.iata.in_(list(unique.keys())))
        .all()
    }
    for iata, item in unique.items():
        row = existing.get(iata)
        if row is None:
            row = models.Airline(iata=iata, name=str(item.get("name") or iata))
            db.add(row)
        row.icao = norm_code(item.get("icao_code") or item.get("icao"), 3)
        row.name = str(item.get("name") or row.name or iata)
        row.website = item.get("website") or row.website
    return names


def upsert_airport(db: Session, item: Dict[str, Any]) -> Optional[models.Airport]:
    iata = norm_code(item.get("iata_code") or item.get("iata"), 3)
    if not iata:
        return None
    row = db.query(models.Airport).filter(models.Airport.iata == iata).first()
    if row is None:
        row = models.Airport(iata=iata, name=item.get("name") or iata)
        db.add(row)
    row.icao = norm_code(item.get("icao_code") or item.get("icao"), 4)
    row.name = item.get("name") or row.name or iata
    row.city = item.get("city") or row.city
    row.country_code = norm_code(item.get("country_code") or item.get("country"), 2)
    row.latitude = item.get("lat") if item.get("lat") is not None else row.latitude
    row.longitude = item.get("lng") if item.get("lng") is not None else row.longitude
    row.timezone = item.get("timezone") or row.timezone
    return row


def upsert_airport_batch(db: Session, items: Sequence[Dict[str, Any]]) -> Set[str]:
    unique: Dict[str, Dict[str, Any]] = {}
    for item in items:
        iata = norm_code(item.get("iata_code") or item.get("iata"), 3)
        if iata and iata not in unique:
            unique[iata] = item

    existing = {
        row.iata: row
        for row in db.query(models.Airport)
        .filter(models.Airport.iata.in_(list(unique.keys())))
        .all()
    }
    for iata, item in unique.items():
        row = existing.get(iata)
        if row is None:
            row = models.Airport(iata=iata, name=item.get("name") or iata)
            db.add(row)
        row.icao = norm_code(item.get("icao_code") or item.get("icao"), 4)
        row.name = item.get("name") or row.name or iata
        row.city = item.get("city") or row.city
        row.country_code = norm_code(item.get("country_code") or item.get("country"), 2)
        row.latitude = item.get("lat") if item.get("lat") is not None else row.latitude
        row.longitude = item.get("lng") if item.get("lng") is not None else row.longitude
        row.timezone = item.get("timezone") or row.timezone
    return set(unique.keys())


def ensure_route_airports(db: Session, item: Dict[str, Any]) -> None:
    for iata_key, icao_key in (("dep_iata", "dep_icao"), ("arr_iata", "arr_icao")):
        iata = norm_code(item.get(iata_key), 3)
        if not iata:
            continue
        row = db.query(models.Airport).filter(models.Airport.iata == iata).first()
        if row is None:
            row = models.Airport(iata=iata, name=iata)
            db.add(row)
            db.flush()
        icao = norm_code(item.get(icao_key), 4)
        if icao and not row.icao:
            row.icao = icao


def ensure_route_airline(
    db: Session,
    item: Dict[str, Any],
    airline_names: Dict[str, str],
) -> None:
    iata = norm_code(item.get("airline_iata"), 2)
    if not iata:
        return
    row = db.query(models.Airline).filter(models.Airline.iata == iata).first()
    if row is None:
        row = models.Airline(iata=iata, name=airline_names.get(iata) or iata)
        db.add(row)
        db.flush()
    icao = norm_code(item.get("airline_icao"), 3)
    if icao and not row.icao:
        row.icao = icao


def upsert_route(
    db: Session,
    item: Dict[str, Any],
    airline_names: Dict[str, str],
) -> Optional[models.DirectRoute]:
    dep_iata = norm_code(item.get("dep_iata"), 3)
    arr_iata = norm_code(item.get("arr_iata"), 3)
    if not dep_iata or not arr_iata or dep_iata == arr_iata:
        return None

    ensure_route_airports(db, item)
    ensure_route_airline(db, item, airline_names)

    airline_iata = norm_code(item.get("airline_iata"), 2)
    flight_number = str(item.get("flight_number") or item.get("flight_iata") or "DIRECT").strip()
    dep_time = parse_time(item.get("dep_time"))

    row = (
        db.query(models.DirectRoute)
        .filter(
            models.DirectRoute.origin_iata == dep_iata,
            models.DirectRoute.destination_iata == arr_iata,
        )
        .first()
    )
    if row is None:
        row = models.DirectRoute(
            airline_iata=airline_iata,
            flight_number=flight_number,
            origin_iata=dep_iata,
            destination_iata=arr_iata,
            dep_time=dep_time,
        )
        db.add(row)

    row.airline_iata = airline_iata
    row.airline_name = airline_names.get(airline_iata or "") if airline_iata else None
    row.flight_number = flight_number
    row.origin_iata = dep_iata
    row.destination_iata = arr_iata
    row.dep_time = dep_time
    row.arr_time = parse_time(item.get("arr_time"))
    row.aircraft = item.get("aircraft_icao") or item.get("aircraft") or row.aircraft
    row.effective_from = parse_date(item.get("effective_from"))
    row.effective_to = parse_date(item.get("effective_to"))
    row.is_active = True

    db.flush()

    db.query(models.RouteDay).filter(models.RouteDay.route_id == row.id).delete(
        synchronize_session=False
    )
    for day in item.get("days") or []:
        weekday = DAY_TO_WEEKDAY.get(str(day).strip().lower())
        if weekday:
            db.add(models.RouteDay(route_id=row.id, weekday=weekday))
    return row


def load_airlines(client: AirLabsClient, db: Session, *, dry_run: bool) -> Dict[str, str]:
    payload = client.get("airlines", _fields="name,iata_code,icao_code,website")
    rows = response_rows(payload)
    names = {
        iata: str(item.get("name"))
        for item in rows
        if (iata := norm_code(item.get("iata_code"), 2)) and item.get("name")
    }
    if not dry_run:
        names = upsert_airline_batch(db, rows)
        db.commit()
    return names


def load_europe_airports(
    client: AirLabsClient,
    db: Session,
    countries: Sequence[str],
    *,
    dry_run: bool,
) -> List[str]:
    seen: Set[str] = set()
    for country in countries:
        payload = client.get(
            "airports",
            country_code=country,
            _fields="name,iata_code,icao_code,lat,lng,city,timezone,country_code",
        )
        country_seen: Set[str] = set()
        for item in response_rows(payload):
            iata = norm_code(item.get("iata_code"), 3)
            if not iata or iata in country_seen:
                continue
            country_seen.add(iata)
            seen.add(iata)
        if not dry_run:
            upsert_airport_batch(db, response_rows(payload))
        if not dry_run:
            db.commit()
    return sorted(seen)


def load_routes_for_airports(
    client: AirLabsClient,
    db: Session,
    airport_iatas: Sequence[str],
    airline_names: Dict[str, str],
    *,
    dry_run: bool,
    limit: int,
    max_airports: Optional[int],
    start_at: Optional[str],
    start_after: Optional[str],
    skip_existing_origins: bool,
    resume_progress: bool,
    progress_file: Path,
) -> int:
    total = 0
    airports = list(airport_iatas[:max_airports] if max_airports else airport_iatas)
    if start_at and start_after:
        raise ValueError("Use only one of --start-at or --start-after.")

    if start_at or start_after:
        marker = norm_code(start_at or start_after, 3)
        if marker in airports:
            marker_index = airports.index(marker)
            start_index = marker_index if start_at else marker_index + 1
            airports = airports[start_index:]
            print(
                f"Resume marker applied: starting {'at' if start_at else 'after'} {marker}; "
                f"{len(airports)} origins remain."
            )
        else:
            print(f"Resume marker {marker} was not found in selected airport list; starting from beginning.")

    if skip_existing_origins and not dry_run:
        existing_origins = set(crud.distinct_route_origins(db))
        airports = [iata for iata in airports if iata not in existing_origins]
        print(f"Skipped DB origins with routes; {len(airports)} origins remain.")

    if resume_progress and not dry_run:
        completed_origins = load_completed_origins(progress_file)
        airports = [iata for iata in airports if iata not in completed_origins]
        print(
            f"Skipped {len(completed_origins)} progress-file completed origins; "
            f"{len(airports)} origins remain."
        )

    for index, dep_iata in enumerate(airports, start=1):
        print(f"[{index}/{len(airports)}] routes from {dep_iata}")
        offset = 0
        while True:
            payload = client.get(
                "routes",
                dep_iata=dep_iata,
                limit=limit,
                offset=offset,
                _fields="dep_iata,dep_icao,arr_iata,arr_icao",
            )
            rows = response_rows(payload)
            for item in rows:
                if not dry_run:
                    upsert_route(db, item, airline_names)
                total += 1
            if not dry_run:
                db.commit()
            if not has_more(payload, len(rows), limit):
                break
            offset += limit
        if not dry_run:
            mark_origin_completed(progress_file, dep_iata)
    return total


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load European routes from AirLabs.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and count data without writing.")
    parser.add_argument("--countries", nargs="*", default=sorted(EUROPE_COUNTRY_CODES))
    parser.add_argument("--limit", type=int, default=500, help="AirLabs page size (free keys may cap at 50).")
    parser.add_argument(
        "--route-load-mode",
        choices=("per-airport",),
        default="per-airport",
        help="AirLabs /routes requires a departure, arrival, or airline filter, so routes are loaded per departure airport.",
    )
    parser.add_argument("--max-airports", type=int, default=None, help="Limit route import for testing.")
    parser.add_argument("--start-at", default=None, help="Resume route import at this departure airport IATA.")
    parser.add_argument("--start-after", default=None, help="Resume route import after this departure airport IATA.")
    parser.add_argument(
        "--resume-from-db",
        action="store_true",
        help="Start at the highest origin currently present in direct_routes (useful after an interrupted run).",
    )
    parser.add_argument(
        "--resume-progress",
        action="store_true",
        help="Skip origins recorded as completed in the progress file, including zero-route origins.",
    )
    parser.add_argument(
        "--progress-file",
        type=Path,
        default=DEFAULT_PROGRESS_FILE,
        help=f"Path to route import progress file (default: {DEFAULT_PROGRESS_FILE}).",
    )
    parser.add_argument(
        "--skip-existing-origins",
        action="store_true",
        help="Skip origins already present in direct_routes. Use only when you are sure they completed.",
    )
    parser.add_argument("--pause", type=float, default=0.2, help="Seconds to sleep after each API call.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = AirLabsClient(AIRLABS_API_KEY, pause_seconds=args.pause)
    db = SessionLocal()
    try:
        if args.resume_from_db:
            if args.start_at or args.start_after:
                raise ValueError("Use --resume-from-db without --start-at/--start-after.")
            origins = crud.distinct_route_origins(db)
            if origins:
                args.start_at = origins[-1]
                print(f"Resuming from DB origin marker: {args.start_at}")

        print("Loading airlines...")
        airline_names = load_airlines(client, db, dry_run=args.dry_run)
        print(f"Airlines seen: {len(airline_names)}")

        countries = sorted({norm_code(c, 2) for c in args.countries if norm_code(c, 2)})
        print(f"Loading European airports for {len(countries)} countries...")
        airport_iatas = load_europe_airports(client, db, countries, dry_run=args.dry_run)
        print(f"European airports seen: {len(airport_iatas)}")

        print("Loading route schedules for European departure airports...")
        routes_seen = load_routes_for_airports(
            client,
            db,
            airport_iatas,
            airline_names,
            dry_run=args.dry_run,
            limit=args.limit,
            max_airports=args.max_airports,
            start_at=args.start_at,
            start_after=args.start_after,
            skip_existing_origins=args.skip_existing_origins,
            resume_progress=args.resume_progress,
            progress_file=args.progress_file,
        )
        print(f"Routes seen: {routes_seen}")
        if args.dry_run:
            print("Dry run only; no database rows were written.")
    finally:
        db.close()
        client.close()


if __name__ == "__main__":
    main()
