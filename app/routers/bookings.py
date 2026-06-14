"""Resident booking lifecycle endpoints (HLD §4.2).

POST /api/bookings accepts JSON {"roomId": ...} (public camelCase contract)
or an HTMX form field `roomId`.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session, select

from app.db import get_session
from app.dependencies import get_current_resident, require_kyc_verified
from app.models import (
    Booking,
    BookingStatus,
    Hostel,
    ResidentProfile,
    Room,
    RoomType,
    User,
)
from app.serializers import to_candidate_view
from app.services.booking_lifecycle import cancel_booking, create_booking
from app.services.matchmaking import build_candidate_pool, rank_pool

router = APIRouter(prefix="/api/bookings", tags=["Bookings"])


async def _extract_room_id(request: Request) -> uuid.UUID:
    raw = None
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        raw = body.get("roomId") or body.get("room_id")
    else:
        form = await request.form()
        raw = form.get("roomId") or form.get("room_id")
    if not raw:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="roomId is required")
    try:
        return uuid.UUID(str(raw))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="roomId must be a UUID")


@router.post("")
async def place_booking(
    request: Request,
    user: User = Depends(require_kyc_verified),
    profile: ResidentProfile = Depends(get_current_resident),
    session: Session = Depends(get_session),
):
    room_id = await _extract_room_id(request)
    booking, match = create_booking(session, profile, user, room_id)
    room = session.get(Room, booking.room_id)

    # `prebooked_match` tells the client a pre-decided roommate was auto-linked;
    # `is_shared` (without a match) is its cue to offer the roommate-finder flow.
    return {
        "id": str(booking.id),
        "status": booking.status,
        "room_id": str(booking.room_id),
        "roommate_match_id": str(booking.roommate_match_id) if booking.roommate_match_id else None,
        "is_shared": room.type == RoomType.SHARED.value,
        "prebooked_match": match is not None,
    }


@router.post("/{booking_id}/cancel")
def cancel(
    booking_id: uuid.UUID,
    profile: ResidentProfile = Depends(get_current_resident),
    session: Session = Depends(get_session),
):
    booking = session.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    outcome = cancel_booking(session, booking, profile)
    return {"id": str(booking_id), "status": booking.status, "detail": outcome}


@router.get("/{booking_id}/roommate-recommendations")
def roommate_recommendations(
    booking_id: uuid.UUID,
    profile: ResidentProfile = Depends(get_current_resident),
    session: Session = Depends(get_session),
):
    booking = session.get(Booking, booking_id)
    if not booking or booking.resident_id != profile.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    if booking.status != BookingStatus.REQUESTED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Roommate matching applies to active REQUESTED bookings only.",
        )
    room = session.get(Room, booking.room_id)
    if room.type != RoomType.SHARED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Roommate matching is for SHARED rooms only.",
        )

    pool = build_candidate_pool(session, profile, room)
    ranked = rank_pool(profile, pool)
    candidates = [to_candidate_view(p, r["overall_score"], r["breakdown"]) for p, r in ranked]

    return {"candidates": candidates}


@router.get("/mine")
def my_bookings(
    profile: ResidentProfile = Depends(get_current_resident),
    session: Session = Depends(get_session),
):
    rows = session.exec(
        select(Booking, Room, Hostel)
        .where(Booking.resident_id == profile.user_id)
        .where(Room.id == Booking.room_id)
        .where(Hostel.id == Room.hostel_id)
        .order_by(Booking.created_at.desc())
    ).all()
    bookings = [
        {
            "id": str(b.id),
            "status": b.status,
            "created_at": b.created_at.isoformat(),
            "room": {"id": str(r.id), "type": r.type, "price": r.price},
            "hostel": {"id": str(h.id), "name": h.name, "location": h.location},
            "roommate_match_id": str(b.roommate_match_id) if b.roommate_match_id else None,
        }
        for b, r, h in rows
    ]
    return {"bookings": bookings}
