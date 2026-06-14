"""Owner review queue + the approval/denial transaction endpoints (HLD §4.3).

Applicant data flows through the shared DPDP serializers: pre-approval views
expose first name + fit vectors only (HLD §6.1).
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.db import get_session
from app.dependencies import get_current_owner
from app.models import (
    Booking,
    BookingStatus,
    Hostel,
    OwnerProfile,
    ResidentProfile,
    Room,
    RoommateMatch,
)
from app.serializers import to_owner_applicant_view, to_room_view
from app.services.booking_allocation import commit_booking_allocation, reject_booking

router = APIRouter(tags=["Owner Bookings"])


def _owned_booking(session: Session, owner: OwnerProfile, booking_id: uuid.UUID) -> tuple[Booking, Room, Hostel]:
    booking = session.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    room = session.get(Room, booking.room_id)
    hostel = session.get(Hostel, room.hostel_id) if room else None
    if not hostel or hostel.owner_id != owner.user_id:
        # 404 (not 403): a foreign booking id is indistinguishable from a missing one.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return booking, room, hostel


@router.get("/api/owners/bookings")
def review_queue(
    owner: OwnerProfile = Depends(get_current_owner),
    session: Session = Depends(get_session),
):
    """Owner review queue as JSON. Applicant data is pre-approval-gated
    (first name + habits) via to_owner_applicant_view; the linked roommate
    match (score + breakdown) is included when present.
    """
    rows = session.exec(
        select(Booking, Room, Hostel)
        .where(Booking.status == BookingStatus.REQUESTED.value)
        .where(Room.id == Booking.room_id)
        .where(Hostel.id == Room.hostel_id)
        .where(Hostel.owner_id == owner.user_id)
        .order_by(Booking.created_at)
    ).all()

    queue = []
    for booking, room, hostel in rows:
        profile = session.get(ResidentProfile, booking.resident_id)
        applicant = to_owner_applicant_view(profile) if profile else None
        match = (
            session.get(RoommateMatch, booking.roommate_match_id)
            if booking.roommate_match_id
            else None
        )
        queue.append(
            {
                "booking": {
                    "id": str(booking.id),
                    "status": booking.status,
                    "created_at": booking.created_at.isoformat(),
                },
                "room": to_room_view(room),
                "hostel": {"id": str(hostel.id), "name": hostel.name},
                "applicant": applicant,
                "match": (
                    {"score": match.score, "breakdown": match.breakdown}
                    if match
                    else None
                ),
            }
        )
    return {"queue": queue}


@router.post("/api/bookings/{booking_id}/approve")
def approve(
    booking_id: uuid.UUID,
    owner: OwnerProfile = Depends(get_current_owner),
    session: Session = Depends(get_session),
):
    """Approve a booking block. Returns the allocation outcome:
    result ∈ {confirmed, already_confirmed, noop}; `confirmed` is the number of
    bookings moved to CONFIRMED and `room_full` flags a competing-request sweep.
    """
    _owned_booking(session, owner, booking_id)
    result = commit_booking_allocation(session, booking_id, owner_user_id=owner.user_id)
    result.setdefault("room_full", False)
    return result


@router.post("/api/bookings/{booking_id}/reject")
def reject(
    booking_id: uuid.UUID,
    owner: OwnerProfile = Depends(get_current_owner),
    session: Session = Depends(get_session),
):
    """Reject a booking block. Returns {result: "rejected", rejected: <count>}."""
    _owned_booking(session, owner, booking_id)
    return reject_booking(session, booking_id, owner_user_id=owner.user_id)
