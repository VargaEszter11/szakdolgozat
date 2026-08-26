"""
Trip sharing API: two flows used from the Planned Trips page.

1) Public link — owner creates a token; anyone with /share?token=… can read the trip
   (no login). Served by GET /api/shared-trips/{token} → shared_trip.html.
2) User-to-user invitation — owner invites another account; recipient sees it in the
   share inbox, then accept (copies the trip) or decline.

Identity for mutating routes comes from the access token; optional body user_id
fields are ignored when present (legacy clients).
"""
from typing import Any, List, Optional, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import crud, get_db, models, schemas
from utils.auth_deps import current_user_id, get_current_user, require_self

router = APIRouter()


def _invitation_response(
    db: Session, invitation: models.TripShareInvitation
) -> schemas.TripShareInvitationResponse:
    """Enrich invitation with from_username and a short source-trip summary for the inbox UI."""
    inv_row = cast(Any, invitation)
    from_user = crud.get_user(db, int(inv_row.from_user_id))
    source_trip = crud.get_planned_trip(db, int(inv_row.source_trip_id))
    source_summary = None
    if source_trip is not None:
        trip_row = cast(Any, source_trip)
        source_summary = schemas.TripShareSourceSummary(
            id=int(trip_row.id),
            title=str(trip_row.title),
            start_date=trip_row.start_date,
            end_date=trip_row.end_date,
            start_city=trip_row.start_city,
        )
    return schemas.TripShareInvitationResponse(
        id=int(inv_row.id),
        source_trip_id=int(inv_row.source_trip_id),
        from_user_id=int(inv_row.from_user_id),
        to_user_id=int(inv_row.to_user_id),
        status=str(inv_row.status),
        created_at=inv_row.created_at,
        responded_at=inv_row.responded_at,
        result_trip_id=inv_row.result_trip_id,
        from_username=cast(Any, from_user).username if from_user else None,
        source_trip=source_summary,
    )


def _trip_public_response(trip: models.PlannedTrip, db: Session) -> schemas.SharedTripPublicResponse:
    """Read-only itinerary payload for the public share page (includes map coordinates)."""
    trip_row = cast(Any, trip)
    stops = crud.get_trip_stops(db, int(trip_row.id))
    return schemas.SharedTripPublicResponse(
        title=str(trip_row.title),
        start_date=trip_row.start_date,
        end_date=trip_row.end_date,
        start_city=trip_row.start_city,
        start_latitude=trip_row.start_latitude,
        start_longitude=trip_row.start_longitude,
        people=int(trip_row.people or 1),
        stops=[schemas.TripStopResponse.model_validate(s) for s in stops],
    )


# Public share links

@router.post(
    "/planned-trips/{trip_id}/share-link",
    response_model=schemas.TripShareLinkResponse,
)
def create_trip_share_link(
    trip_id: int,
    body: Optional[schemas.TripShareLinkRequest] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create or reuse an active public link for an owned trip."""
    del body  # user identity comes from the access token
    try:
        link = crud.create_or_get_trip_share_link(db, trip_id, current_user_id(current_user))
    except ValueError as exc:
        code = str(exc)
        if code == "trip_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
        if code == "not_owner":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not trip owner")
        raise
    link_row = cast(Any, link)
    token = str(link_row.share_token)
    return schemas.TripShareLinkResponse(
        share_token=token,
        share_url=crud.share_url_for_token(token),
    )


@router.delete("/planned-trips/{trip_id}/share-link", status_code=status.HTTP_204_NO_CONTENT)
def revoke_trip_share_link(
    trip_id: int,
    body: Optional[schemas.TripShareLinkRequest] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Deactivate all active public links for an owned trip."""
    del body
    try:
        crud.revoke_trip_share_link(db, trip_id, current_user_id(current_user))
    except ValueError as exc:
        code = str(exc)
        if code == "trip_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
        if code == "not_owner":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not trip owner")
        raise
    return None


@router.get("/shared-trips/{token}", response_model=schemas.SharedTripPublicResponse)
def get_shared_trip(token: str, db: Session = Depends(get_db)):
    """Unauthenticated read of a trip via an active share token (shared_trip.html)."""
    link = crud.get_active_share_link_by_token(db, token)
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link not found")
    link_row = cast(Any, link)
    trip = crud.get_planned_trip(db, int(link_row.trip_id))
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    return _trip_public_response(trip, db)


# User-to-user invitations

@router.post(
    "/planned-trips/{trip_id}/share",
    response_model=schemas.TripShareInvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
def share_trip_with_user(
    trip_id: int,
    body: schemas.TripShareInvitationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Invite another user."""
    try:
        invitation = crud.create_trip_share_invitation(
            db, trip_id, current_user_id(current_user), body.to_user_id
        )
    except ValueError as exc:
        code = str(exc)
        if code == "trip_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
        if code == "not_owner":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not trip owner")
        if code == "cannot_share_with_self":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot share trip with yourself",
            )
        if code == "recipient_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient not found")
        if code == "invitation_already_pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Invitation already pending",
            )
        raise
    return _invitation_response(db, invitation)


@router.get(
    "/users/{user_id}/trip-share-invitations",
    response_model=List[schemas.TripShareInvitationResponse],
)
def list_trip_share_invitations(
    user_id: int,
    status_filter: str = Query("pending", alias="status"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Inbox for the current user (self only); Planned Trips page loads status=pending."""
    require_self(user_id, current_user)
    user = crud.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    invitations = crud.list_trip_share_invitations_for_user(db, user_id, status_filter)
    return [_invitation_response(db, inv) for inv in invitations]


@router.post(
    "/trip-share-invitations/{invitation_id}/accept",
    response_model=schemas.TripShareInvitationResponse,
)
def accept_trip_share_invitation(
    invitation_id: int,
    body: Optional[schemas.TripShareInvitationAction] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Recipient only: copy source trip into their account (shared_from_user_id set)."""
    del body
    try:
        invitation = crud.accept_trip_share_invitation(
            db, invitation_id, current_user_id(current_user)
        )
    except ValueError as exc:
        code = str(exc)
        if code == "invitation_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
        if code == "not_recipient":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not invitation recipient")
        if code == "invitation_not_pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation is not pending",
            )
        if code == "source_trip_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source trip not found")
        raise
    return _invitation_response(db, invitation)


@router.post(
    "/trip-share-invitations/{invitation_id}/decline",
    response_model=schemas.TripShareInvitationResponse,
)
def decline_trip_share_invitation(
    invitation_id: int,
    body: Optional[schemas.TripShareInvitationAction] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Recipient only: mark invitation declined (no trip copy)."""
    del body
    try:
        invitation = crud.decline_trip_share_invitation(
            db, invitation_id, current_user_id(current_user)
        )
    except ValueError as exc:
        code = str(exc)
        if code == "invitation_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
        if code == "not_recipient":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not invitation recipient")
        if code == "invitation_not_pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation is not pending",
            )
        raise
    return _invitation_response(db, invitation)
