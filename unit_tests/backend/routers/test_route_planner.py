import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers import route_planner
from utils.auth_deps import get_current_user

app = FastAPI()
app.include_router(route_planner.router)


@pytest.fixture
def client(auth_user):
    app.dependency_overrides[get_current_user] = lambda: auth_user
    yield TestClient(app)
    app.dependency_overrides.pop(get_current_user, None)


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
    captured = {}

    async def fake_plan(request, db):
        captured["userId"] = getattr(request, "userId", None)
        captured["plannerUserId"] = getattr(request, "plannerUserId", None)
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
    assert captured["userId"] == 1
    assert captured["plannerUserId"] == 1


def test_generate_visited_plan_without_travel_log(monkeypatch, client):
    """DB toggle off: omit userId so visited places come only from the request body."""
    captured = {}

    async def fake_plan(request, db):
        captured["userId"] = getattr(request, "userId", None)
        captured["plannerUserId"] = getattr(request, "plannerUserId", None)
        return {"type": "visited"}

    monkeypatch.setattr(route_planner, "generate_visited_plan", fake_plan)

    res = client.post("/generate_travel_plans/visited", json={
        "visitedPlaces": ["Vienna"],
        "extraPlaces": ["Prague"],
        "startingPoint": "Budapest",
        "startDate": "2026-07-01",
        "endDate": "2026-07-05",
    })

    assert res.status_code == 200
    assert captured["userId"] is None
    assert captured["plannerUserId"] == 1


def test_generate_unvisited_plan(monkeypatch, client):
    captured = {}

    async def fake_plan(request, db):
        captured["userId"] = getattr(request, "userId", None)
        captured["plannerUserId"] = getattr(request, "plannerUserId", None)
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
    assert captured["userId"] == 1
    assert captured["plannerUserId"] == 1


def test_generate_unvisited_plan_without_travel_log(monkeypatch, client):
    """DB toggle off: omit userId so exclusions come only from additionalExclusions."""
    captured = {}

    async def fake_plan(request, db):
        captured["userId"] = getattr(request, "userId", None)
        captured["plannerUserId"] = getattr(request, "plannerUserId", None)
        return {"type": "unvisited"}

    monkeypatch.setattr(route_planner, "generate_unvisited_plan", fake_plan)

    res = client.post("/generate_travel_plans/unvisited", json={
        "startingPoint": "Budapest",
        "startDate": "2026-07-01",
        "endDate": "2026-07-05",
        "additionalExclusions": ["Paris"],
    })

    assert res.status_code == 200
    assert captured["userId"] is None
    assert captured["plannerUserId"] == 1


def test_generate_random_plan(monkeypatch, client):
    captured = {}

    async def fake_plan(request, db):
        captured["userId"] = getattr(request, "userId", None)
        captured["plannerUserId"] = getattr(request, "plannerUserId", None)
        return {"type": "random"}

    monkeypatch.setattr(route_planner, "generate_random_plan", fake_plan)

    res = client.post("/generate_travel_plans/random", json={
        "startingPoint": "Budapest",
        "startDate": "2026-07-01",
        "endDate": "2026-07-05",
    })

    assert res.status_code == 200
    assert res.json()["type"] == "random"
    assert captured["userId"] is None
    assert captured["plannerUserId"] == 1
