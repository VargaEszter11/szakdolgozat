import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from routers import route_planner

app = FastAPI()
app.include_router(route_planner.router)


@pytest.fixture
def client():
    return TestClient(app)

def test_geocode_success(monkeypatch, client):
    async def fake_geocode(request):
        return {"results": ["ok"]}

    monkeypatch.setattr(route_planner, "geocode_places", fake_geocode)

    res = client.post("/api/geocode", json={
        "places": ["Miskolc", "Budapest"]
    })

    assert res.status_code == 200
    assert "results" in res.json()

def test_generate_visited_plan(monkeypatch, client):
    async def fake_plan(request, db):
        return {"type": "visited", "ok": True}

    monkeypatch.setattr(route_planner, "generate_visited_plan", fake_plan)

    res = client.post("/generate_travel_plans/visited", json={
        "visitedPlaces": [],
        "startingPoint": "Budapest",
        "startDate": "2026-07-01",
        "endDate": "2026-07-05",
        "userId": 1,
    })

    assert res.status_code == 200
    assert res.json()["type"] == "visited"

def test_generate_unvisited_plan(monkeypatch, client):
    async def fake_plan(request, db):
        return {"type": "unvisited"}

    monkeypatch.setattr(route_planner, "generate_unvisited_plan", fake_plan)

    res = client.post("/generate_travel_plans/unvisited", json={
        "startingPoint": "Budapest",
        "startDate": "2026-07-01",
        "endDate": "2026-07-05",
        "userId": 1,
    })

    assert res.status_code == 200
    assert res.json()["type"] == "unvisited"

def test_generate_random_plan(monkeypatch, client):
    async def fake_plan(request, db):
        return {"type": "random"}

    monkeypatch.setattr(route_planner, "generate_random_plan", fake_plan)

    res = client.post("/generate_travel_plans/random", json={
        "startingPoint": "Budapest",
        "startDate": "2026-07-01",
        "endDate": "2026-07-05",
    })

    assert res.status_code == 200
    assert res.json()["type"] == "random"