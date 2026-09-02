"""In-app notification feed (computed from existing trip/feedback/share state)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, List, Optional, cast

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import crud, schemas, get_db, models
from utils.auth_deps import current_user_id, get_current_user

router = APIRouter()


def _iso_dt(value) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    return None


def _preview(text: str, limit: int = 120) -> str:
    raw = " ".join(str(text or "").split())
    if len(raw) <= limit:
        return raw
    return raw[: limit - 1].rstrip() + "…"


@router.get("/notifications", response_model=schemas.NotificationsResponse)
def list_notifications(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Pending shares, recently solved feedback, and completed booked trips."""
    user_id = current_user_id(current_user)
    items: List[schemas.NotificationItem] = []

    invitations = crud.list_trip_share_invitations_for_user(db, user_id, status="pending")
    for inv in invitations:
        inv_any = cast(Any, inv)
        trip = crud.get_planned_trip(db, int(inv_any.source_trip_id))
        from_user = crud.get_user(db, int(inv_any.from_user_id))
        trip_title = (
            str(cast(Any, trip).title)
            if trip is not None and getattr(trip, "title", None)
            else "Trip"
        )
        from_name = (
            str(cast(Any, from_user).username)
            if from_user is not None
            else f"user#{inv_any.from_user_id}"
        )
        items.append(
            schemas.NotificationItem(
                id=f"share:{int(inv_any.id)}",
                type="share_pending",
                title="Shared trip invitation",
                body=f"{from_name} shared “{trip_title}” with you.",
                href="/trips",
                created_at=_iso_dt(inv_any.created_at),
                meta={
                    "invitation_id": int(inv_any.id),
                    "trip_title": trip_title,
                    "from_username": from_name,
                },
            )
        )

    feedback_rows = crud.list_feedbacks_for_user(db, user_id, limit=50)
    for row in feedback_rows:
        fb = cast(Any, row)
        if not bool(getattr(fb, "solved", False)):
            continue
        items.append(
            schemas.NotificationItem(
                id=f"feedback_solved:{int(fb.id)}",
                type="feedback_solved",
                title="Feedback marked as solved",
                body=_preview(str(fb.message or "")),
                href="/profile",
                created_at=_iso_dt(fb.created_at),
                meta={
                    "feedback_id": int(fb.id),
                    "message_preview": _preview(str(fb.message or "")),
                },
            )
        )

    today = date.today()
    # Keep completed-trip alerts relevant (last 90 days).
    oldest = today - timedelta(days=90)
    trips = crud.get_user_planned_trips(db, user_id)
    for trip in trips:
        t = cast(Any, trip)
        if not bool(t.is_booked) or not t.end_date:
            continue
        end = t.end_date if isinstance(t.end_date, date) else None
        if end is None or end >= today or end < oldest:
            continue
        title = str(t.title or "Trip")
        items.append(
            schemas.NotificationItem(
                id=f"trip_completed:{int(t.id)}",
                type="trip_completed",
                title="Trip completed",
                body=f"“{title}” ended on {end.isoformat()}.",
                href="/trips",
                created_at=_iso_dt(end),
                meta={
                    "trip_id": int(t.id),
                    "trip_title": title,
                    "end_date": end.isoformat(),
                },
            )
        )

    items.sort(
        key=lambda n: n.created_at or datetime.min,
        reverse=True,
    )
    return schemas.NotificationsResponse(items=items)
