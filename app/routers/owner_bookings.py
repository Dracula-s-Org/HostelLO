"""Owner review queue + the approval/denial transaction endpoints (HLD §4.3).

Applicant data flows through the shared DPDP serializers: pre-approval views
expose first name + fit vectors only (HLD §6.1).
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
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
from app.serializers import to_owner_applicant_view
from app.services.booking_allocation import commit_booking_allocation, reject_booking
from app.templating import templates

router = APIRouter(tags=["Owner Bookings"])


def _owned_booking(session: Session, owner: OwnerProfile, booking_id: uuid.UUID) -> tuple[Booking, Room, Hostel]:
    booking = session.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    room = session.get(Room, booking.room_id)
    hostel = session.get(Hostel, room.hostel_id) if room else None
    if not hostel or hostel.owner_id != owner.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your property")
    return booking, room, hostel


@router.get("/api/owners/bookings", response_class=HTMLResponse)
def review_queue(
    request: Request,
    owner: OwnerProfile = Depends(get_current_owner),
    session: Session = Depends(get_session),
):
    rows = session.exec(
        select(Booking, Room, Hostel)
        .where(Booking.status == BookingStatus.REQUESTED.value)
        .where(Room.id == Booking.room_id)
        .where(Hostel.id == Room.hostel_id)
        .where(Hostel.owner_id == owner.user_id)
        .order_by(Booking.created_at)
    ).all()

    items = []
    for booking, room, hostel in rows:
        profile = session.get(ResidentProfile, booking.resident_id)
        applicant = to_owner_applicant_view(profile) if profile else None
        match = (
            session.get(RoommateMatch, booking.roommate_match_id)
            if booking.roommate_match_id
            else None
        )
        items.append(
            {
                "booking": booking,
                "room": room,
                "hostel": hostel,
                "applicant": applicant,
                "match": match,  # breakdown dict rendered with Dev A's frozen keys
            }
        )
    return templates.TemplateResponse(request, "owner/bookings.html", {"items": items})


@router.post("/api/bookings/{booking_id}/approve", response_class=HTMLResponse)
def approve(
    booking_id: uuid.UUID,
    owner: OwnerProfile = Depends(get_current_owner),
    session: Session = Depends(get_session),
):
    _owned_booking(session, owner, booking_id)
    result = commit_booking_allocation(session, booking_id)
    if result["result"] == "already_confirmed":
        return HTMLResponse(
            "<div class='rounded bg-blue-50 text-blue-800 p-3'>Already approved.</div>"
        )
    if result["result"] == "noop":
        return HTMLResponse(
            "<div class='rounded bg-amber-50 text-amber-800 p-3'>Nothing to approve on this block.</div>"
        )
    sweep = " Room is now FULL — competing requests were swept to REJECTED." if result.get("room_full") else ""
    return HTMLResponse(
        f"<div class='rounded bg-green-50 text-green-800 p-3'>Approved — {result['confirmed']} booking(s) "
        f"CONFIRMED in one transaction.{sweep}</div>"
    )


@router.post("/api/bookings/{booking_id}/reject", response_class=HTMLResponse)
def reject(
    booking_id: uuid.UUID,
    owner: OwnerProfile = Depends(get_current_owner),
    session: Session = Depends(get_session),
):
    _owned_booking(session, owner, booking_id)
    result = reject_booking(session, booking_id)
    return HTMLResponse(
        f"<div class='rounded bg-amber-50 text-amber-800 p-3'>Application rejected "
        f"({result['rejected']} booking(s)).</div>"
    )
