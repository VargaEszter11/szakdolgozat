"""
Integration tests for main application pages.
"""
from pathlib import Path


class TestMainPages:
    """Integration tests for root and share page endpoints."""

    def test_root_redirects_to_main_page(self, client):
        response = client.get("/", follow_redirects=False)

        assert response.status_code in (302, 307)
        assert "main_page.html" in response.headers["location"]

    def test_share_page_served(self, client):
        response = client.get("/share")

        assert response.status_code == 200
        frontend = Path(__file__).parent.parent.parent / "frontend" / "pages" / "routePlanner" / "shared_trip.html"
        assert frontend.is_file()
        assert response.headers.get("content-type", "").startswith("text/html")
