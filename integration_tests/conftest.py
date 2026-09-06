"""
Shared fixtures and configuration for integration tests.
"""
import pytest
import sys
import os
from pathlib import Path
from sqlalchemy import create_engine, pool
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import main
from database.database import Base, get_db as original_get_db
from database import crud, schemas


# Use SQLite in-memory database for tests with shared cache
# StaticPool ensures the same connection is reused, allowing in-memory DB to persist
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=pool.StaticPool
)

# Create tables at module load time
Base.metadata.create_all(bind=engine)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def patch_plan_builder_db(monkeypatch, db):
    """Bind plan_builder.SessionLocal to the same SQLite engine as the test ``db``."""

    def _patch(plan_builder_module):
        factory = sessionmaker(autocommit=False, autoflush=False, bind=db.get_bind())
        monkeypatch.setattr(plan_builder_module, "SessionLocal", factory)
        return factory

    return _patch


def override_get_db():
    """Override the database dependency with test database."""
    db = None
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        if db is not None:
            db.close()


@pytest.fixture(scope="function", autouse=True)
def clear_db():
    """Clear all tables before each test."""
    # Delete all data from tables
    from sqlalchemy import text
    with engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()
    yield


@pytest.fixture(scope="function")
def db():
    """Provide a database session for test fixtures."""
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="function")
def client():
    """Provide a test client with overridden database dependency."""
    main.app.dependency_overrides[original_get_db] = override_get_db
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(db):
    """Create a test user and return user data."""
    user_data = schemas.UserCreate(
        username="testuser",
        email="testuser@example.com",
        password="TestPassword123!"
    )
    user = crud.create_user(db=db, user=user_data)
    crud.mark_user_email_verified(db, int(user.id))
    db.commit()
    return {
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "TestPassword123!",
        "id": user.id
    }


@pytest.fixture(scope="function")
def test_user_2(db):
    """Create a second test user."""
    user_data = schemas.UserCreate(
        username="testuser2",
        email="testuser2@example.com",
        password="TestPassword456!"
    )
    user = crud.create_user(db=db, user=user_data)
    crud.mark_user_email_verified(db, int(user.id))
    db.commit()
    return {
        "username": "testuser2",
        "email": "testuser2@example.com",
        "password": "TestPassword456!",
        "id": user.id
    }


@pytest.fixture(scope="function")
def auth_headers(test_user):
    """Bearer token for the primary test user."""
    from utils.auth_deps import create_access_token

    token = create_access_token(user_id=int(test_user["id"]), username=test_user["username"])
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def auth_headers_2(test_user_2):
    """Bearer token for the second test user."""
    from utils.auth_deps import create_access_token

    token = create_access_token(user_id=int(test_user_2["id"]), username=test_user_2["username"])
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def planned_trip(client, test_user, auth_headers):
    """Create a planned trip for the primary test user."""
    response = client.post(
        "/api/planned-trips",
        headers=auth_headers,
        json={
            "user_id": test_user["id"],
            "title": "Europe Adventure",
            "start_date": "2026-07-01",
            "end_date": "2026-07-14",
            "start_city": "Budapest",
            "people": 2,
            "is_booked": False,
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture(scope="function")
def visited_place(client, test_user, auth_headers):
    """Create a visited place for the primary test user."""
    response = client.post(
        "/api/visited-places",
        headers=auth_headers,
        json={
            "user_id": test_user["id"],
            "place_name": "Prague",
            "country": "CZ",
            "date": "2024-05-10",
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture(scope="function")
def european_airports(db):
    """Seed European airports used by route planning integration tests."""
    from database import models

    airports = [
        models.Airport(
            iata="BUD",
            name="Budapest Airport",
            city="Budapest",
            country_code="HU",
            latitude=47.439,
            longitude=19.261,
        ),
        models.Airport(
            iata="VIE",
            name="Vienna Airport",
            city="Vienna",
            country_code="AT",
            latitude=48.1103,
            longitude=16.5697,
        ),
        models.Airport(
            iata="FCO",
            name="Rome Fiumicino",
            city="Rome",
            country_code="IT",
            latitude=41.8003,
            longitude=12.2389,
        ),
        models.Airport(
            iata="DUB",
            name="Dublin Airport",
            city="Dublin",
            country_code="IE",
            latitude=53.4264,
            longitude=-6.2499,
        ),
        models.Airport(
            iata="LPL",
            name="Liverpool Airport",
            city="Liverpool",
            country_code="GB",
            latitude=53.3336,
            longitude=-2.8497,
        ),
    ]
    for airport in airports:
        db.add(airport)
    db.commit()
    return {airport.iata: airport for airport in airports}


@pytest.fixture(scope="function")
def bud_fco_route(db, european_airports):
    """Seed an active BUD→FCO direct route with a weekday schedule."""
    from database import models

    airline = models.Airline(iata="FR", name="Ryanair")
    db.add(airline)
    db.flush()

    route = models.DirectRoute(
        id=1,
        airline_iata="FR",
        airline_name="Ryanair",
        flight_number="FR1234",
        origin_iata="BUD",
        destination_iata="FCO",
        is_seasonal=False,
        is_active=True,
    )
    db.add(route)
    db.flush()
    db.commit()
    db.refresh(route)
    return route
