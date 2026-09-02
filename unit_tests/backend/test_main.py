import main
from fastapi.testclient import TestClient
from middleware.request_logging import RequestLoggingMiddleware


client = TestClient(main.app)

def test_app_is_created():
    assert main.app is not None

def test_routers_are_attached():
    openapi_paths = main.app.openapi()["paths"]

    assert any(path.startswith("/api/") for path in openapi_paths)


def test_expected_route_groups_exist():
    route_strings = [str(route) for route in main.app.routes]
    openapi_paths = main.app.openapi()["paths"]

    assert any("auth" in r for r in route_strings)
    assert any("users" in r for r in route_strings)
    assert any("planned_trips" in r for r in route_strings)
    assert any("stops" in r or "trip_stops" in r for r in route_strings)
    assert any("places" in r or "visited" in r for r in route_strings)
    assert "/api/feedback" in openapi_paths
    assert "/api/admin/feedback" in openapi_paths
    assert "/api/admin/feedback/{feedback_id}" in openapi_paths

def test_request_logging_middleware_is_registered():
    middleware_classes = [m.cls for m in main.app.user_middleware]

    assert RequestLoggingMiddleware in middleware_classes

def test_static_mounts_exist():
    mount_paths = []

    for route in main.app.routes:
        path = getattr(route, "path", None)
        if isinstance(path, str):
            mount_paths.append(path)

    assert "/uploads" in mount_paths

def test_startup_event_exists():
    assert hasattr(main, "startup_event")
    assert callable(main.startup_event)

def test_uploads_endpoint_accessible():
    response = client.get("/uploads")

    assert response.status_code in (200, 404, 405)

def test_app_metadata():
    assert main.app.title == "Planventure API"
    assert main.app.version == "1.0.0"
    assert "travel planning" in main.app.description.lower()