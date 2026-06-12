"""Mutual-consent roommate flow (HLD §4.2, §5.1, §5.2.1).

Candidate eligibility is re-validated server-side on proposal; never trust
client-sent scores (TDD §10).
"""
import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from app.db import get_session
from app.dependencies import get_current_resident
from app.models import (
    Booking,
    BookingStatus,
    KycStatus,
    MatchStatus,
    ResidentProfile,
    Room,
    RoomType,
    RoommateMatch,
    User,
)
from app.serializers import to_match_confirmed_view
from app.services.matchmaking import build_candidate_pool, has_active_booking, score_pair

router = APIRouter(prefix="/api/roommate-matches", tags=["Roommate Matches"])


@router.post("", response_class=HTMLResponse)
def create_roommate_match(
    candidate_id: uuid.UUID = Form(..., alias="candidateId"),
    profile: ResidentProfile = Depends(get_current_resident),
    session: Session = Depends(get_session),
):
    # Re-matching via extant rows (HLD §5.1.4): the initiator's active REQUESTED
    # placeholder on a shared room is reused, never duplicated.
    booking = session.exec(
        select(Booking).where(
            Booking.resident_id == profile.user_id,
            Booking.status == BookingStatus.REQUESTED.value,
        )
    ).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Place a shared-room booking before proposing a roommate.",
        )
    room = session.get(Room, booking.room_id)
    if room.type != RoomType.SHARED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Roommate proposals apply to SHARED rooms only.",
        )

    candidate = session.get(ResidentProfile, candidate_id)
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    # Server-side re-validation: candidate must still be in the eligible pool
    pool_ids = {c.user_id for c in build_candidate_pool(session, profile, room)}
    if candidate.user_id not in pool_ids:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Candidate is no longer eligible for this room.",
        )
    pair = score_pair(profile, candidate)
    if pair is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Candidate fails pairwise compatibility gates.",
        )

    # Dissolve a lingering PROPOSED block if the initiator re-proposes
    if booking.roommate_match_id:
        old = session.get(RoommateMatch, booking.roommate_match_id)
        if old and old.status == MatchStatus.PROPOSED.value:
            old.status = MatchStatus.REJECTED.value
            session.add(old)

    match = RoommateMatch(
        room_id=room.id,
        resident_a=profile.user_id,
        resident_b=candidate.user_id,
        a_accepted=True,
        b_accepted=False,
        score=int(round(pair["overall_score"])),
        breakdown=pair["breakdown"],
        status=MatchStatus.PROPOSED.value,
    )
    session.add(match)
    session.flush()
    booking.roommate_match_id = match.id  # same transaction (HLD §5.1.2)
    session.add(booking)
    session.commit()

    return HTMLResponse(
        "<div class='rounded bg-green-50 text-green-800 p-3'>Proposal sent — pending their consent. "
        f"Compatibility: <b>{match.score}%</b></div>"
    )


@router.post("/{match_id}/accept", response_class=HTMLResponse)
def accept_roommate_match(
    match_id: uuid.UUID,
    profile: ResidentProfile = Depends(get_current_resident),
    session: Session = Depends(get_session),
):
    match = session.get(RoommateMatch, match_id)
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    if match.resident_b != profile.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the invited resident can accept")
    if match.status != MatchStatus.PROPOSED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"Match is {match.status}, not PROPOSED."
        )

    user_b = session.get(User, profile.user_id)
    if user_b.kyc_status != KycStatus.VERIFIED.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Complete KYC verification before accepting."
        )
    if has_active_booking(session, profile.user_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already hold an active booking.",
        )

    match.b_accepted = True
    match.status = MatchStatus.CONFIRMED.value
    session.add(match)
    # Auto-create linked Booking B (HLD §5.1.3)
    session.add(
        Booking(
            resident_id=profile.user_id,
            room_id=match.room_id,
            roommate_match_id=match.id,
            status=BookingStatus.REQUESTED.value,
        )
    )
    session.commit()

    partner_profile = session.get(ResidentProfile, match.resident_a)
    partner_user = session.get(User, match.resident_a)
    partner = to_match_confirmed_view(partner_profile, partner_user)
    return HTMLResponse(
        "<div class='rounded bg-green-50 text-green-800 p-3'>Match confirmed! Your linked booking "
        f"was created. Roommate: <b>{partner['full_name']}</b> · {partner['phone']}</div>"
    )


@router.post("/{match_id}/reject", response_class=HTMLResponse)
def reject_roommate_match(
    match_id: uuid.UUID,
    profile: ResidentProfile = Depends(get_current_resident),
    session: Session = Depends(get_session),
):
    match = session.get(RoommateMatch, match_id)
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    if profile.user_id not in (match.resident_a, match.resident_b):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a participant of this match")
    if match.status == MatchStatus.CONFIRMED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Confirmed matches dissolve via booking cancellation.",
        )
    match.status = MatchStatus.REJECTED.value
    session.add(match)
    # Unlink the initiator's still-REQUESTED placeholder so they can re-match
    linked = session.exec(
        select(Booking).where(
            Booking.roommate_match_id == match.id,
            Booking.status == BookingStatus.REQUESTED.value,
        )
    ).all()
    for b in linked:
        b.roommate_match_id = None
        session.add(b)
    session.commit()
    return HTMLResponse("<div class='rounded bg-amber-50 text-amber-800 p-3'>Proposal declined.</div>")


@router.get("/pending", response_class=HTMLResponse)
def pending_matches(
    profile: ResidentProfile = Depends(get_current_resident),
    session: Session = Depends(get_session),
):
    """Incoming proposals awaiting this resident's consent (HTMX fragment)."""
    matches = session.exec(
        select(RoommateMatch).where(
            RoommateMatch.resident_b == profile.user_id,
            RoommateMatch.status == MatchStatus.PROPOSED.value,
        )
    ).all()
    if not matches:
        return HTMLResponse("<p class='text-sm text-gray-500'>No pending roommate proposals.</p>")
    parts = []
    for m in matches:
        proposer = session.get(ResidentProfile, m.resident_a)
        first = (proposer.name or "").split()[0] if proposer else "Someone"
        parts.append(
            f"<div class='border rounded p-3 space-y-2'><p><b>{first}</b> proposed to share a room "
            f"with you — compatibility <b>{m.score}%</b></p>"
            f"<div class='flex gap-2'>"
            f"<button hx-post='/api/roommate-matches/{m.id}/accept' hx-target='closest div' "
            "class='bg-green-600 text-white rounded px-3 py-1'>Accept</button>"
            f"<button hx-post='/api/roommate-matches/{m.id}/reject' hx-target='closest div' "
            "class='bg-gray-200 rounded px-3 py-1'>Decline</button>"
            "</div></div>"
        )
    return HTMLResponse("".join(parts))
