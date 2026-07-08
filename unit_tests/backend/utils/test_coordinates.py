import httpx
import pytest
from fastapi import HTTPException

from backend.utils.coordinates import geocode_place


class MockResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


class MockClient:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def get(self, *args, **kwargs):
        return self.response

@pytest.mark.asyncio
async def test_geocode_place_returns_coordinates(monkeypatch):
    response = MockResponse([
        {
            "lat": "47.4979",
            "lon": "19.0402",
        }
    ])

    monkeypatch.setattr(
        "backend.utils.coordinates.httpx.AsyncClient",
        lambda **kwargs: MockClient(response),
    )

    lat, lon = await geocode_place("Budapest")

    assert lat == 47.4979
    assert lon == 19.0402

@pytest.mark.asyncio
async def test_geocode_place_raises_when_place_not_found(monkeypatch):
    response = MockResponse([])

    monkeypatch.setattr(
        "backend.utils.coordinates.httpx.AsyncClient",
        lambda **kwargs: MockClient(response),
    )

    with pytest.raises(ValueError, match="not found"):
        await geocode_place("MadeUpPlace123")

@pytest.mark.asyncio
async def test_geocode_place_uses_env_user_agent(monkeypatch):
    captured = {}

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url, params=None, headers=None):
            captured["headers"] = headers
            return MockResponse(
                [{"lat": "47.4979", "lon": "19.0402"}]
            )

    monkeypatch.setenv(
        "NOMINATIM_USER_AGENT",
        "MyCustomAgent/1.0",
    )

    monkeypatch.setattr(
        "backend.utils.coordinates.httpx.AsyncClient",
        lambda **kwargs: Client(),
    )

    await geocode_place("Budapest")

    assert captured["headers"]["User-Agent"] == "MyCustomAgent/1.0"

@pytest.mark.asyncio
async def test_geocode_place_propagates_http_errors(monkeypatch):
    class ErrorResponse:
        def raise_for_status(self):
            raise Exception("HTTP error")

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, *args, **kwargs):
            return ErrorResponse()

    monkeypatch.setattr(
        "backend.utils.coordinates.httpx.AsyncClient",
        lambda **kwargs: Client(),
    )

    with pytest.raises(Exception, match="HTTP error"):
        await geocode_place("Budapest")

@pytest.mark.asyncio
async def test_geocode_place_raises_503_when_rate_limited(monkeypatch):
    class RateLimitedResponse:
        status_code = 429

        def raise_for_status(self):
            raise httpx.HTTPStatusError(
                "429 Too Many Requests",
                request=httpx.Request("GET", "https://nominatim.openstreetmap.org/search"),
                response=httpx.Response(429, request=httpx.Request("GET", "https://nominatim.openstreetmap.org/search")),
            )

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, *args, **kwargs):
            return RateLimitedResponse()

    monkeypatch.setattr(
        "backend.utils.coordinates.httpx.AsyncClient",
        lambda **kwargs: Client(),
    )

    with pytest.raises(HTTPException) as exc_info:
        await geocode_place("Budapest")

    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_geocode_place_passes_language(monkeypatch):
    captured = {}

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url, params=None, headers=None):
            captured["params"] = params
            return MockResponse(
                [{"lat": "47.4979", "lon": "19.0402"}]
            )

    monkeypatch.setattr(
        "backend.utils.coordinates.httpx.AsyncClient",
        lambda **kwargs: Client(),
    )

    await geocode_place("Budapest", language="hu")

    assert captured["params"]["accept-language"] == "hu"
