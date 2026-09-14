"""
Integration tests for the completed-booked-trip -> visited-places sync,
specifically that a user deleting a synced visited place doesn't cause it to
silently reappear the next time the sync runs (e.g. on the next list load).
"""
from datetime import date, timedelta

from database import models


def _make_booked_trip_with_stop(db, user_id, *, place_name="Prague", country="CZ"):
    trip = models.PlannedTrip(
        user_id=user_id,
        title="Past Trip",
        start_date=date.today() - timedelta(days=10),
        end_date=date.today() - timedelta(days=3),
        start_city="Budapest",
        people=1,
        is_booked=True,
    )
    db.add(trip)
    db.flush()

    stop = models.PlannedTripStop(
        trip_id=trip.id,
        place_name=place_name,
        country=country,
        stop_order=1,
        arrival_date=date.today() - timedelta(days=8),
        departure_date=date.today() - timedelta(days=5),
    )
    db.add(stop)
    db.commit()
    db.refresh(trip)
    db.refresh(stop)
    return trip, stop


class TestBookedTripVisitedSync:
    def test_synced_place_appears_on_list(self, client, db, test_user, auth_headers):
        _make_booked_trip_with_stop(db, test_user["id"])

        response = client.get("/api/visited-places", headers=auth_headers)

        assert response.status_code == 200
        places = response.json()
        assert any(p["place_name"] == "Prague" for p in places)

    def test_deleted_synced_place_does_not_reappear(self, client, db, test_user, auth_headers):
        _make_booked_trip_with_stop(db, test_user["id"])

        # First load creates the visited place from the booked trip's stop.
        first = client.get("/api/visited-places", headers=auth_headers)
        assert first.status_code == 200
        prague = next(p for p in first.json() if p["place_name"] == "Prague")

        # User deletes it.
        delete_response = client.delete(
            f"/api/visited-places/{prague['id']}", headers=auth_headers
        )
        assert delete_response.status_code == 204

        # A later list load must not recreate it.
        second = client.get("/api/visited-places", headers=auth_headers)
        assert second.status_code == 200
        assert not any(p["place_name"] == "Prague" for p in second.json())

        # And a third, to make sure it's not just a one-request grace period.
        third = client.get("/api/visited-places", headers=auth_headers)
        assert third.status_code == 200
        assert not any(p["place_name"] == "Prague" for p in third.json())

    def test_stop_marked_synced_after_first_sync(self, client, db, test_user, auth_headers):
        trip, stop = _make_booked_trip_with_stop(db, test_user["id"])
        assert stop.synced_to_visited is False

        client.get("/api/visited-places", headers=auth_headers)

        db.refresh(stop)
        assert stop.synced_to_visited is True
