"""Resident-side booking lifecycle: creation (incl. pre-decided roommates, A6)
and the cancellation cascades of HLD §5.2.3.
"""
import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models import (
    Booking,
    BookingStatus,
    Hostel,
    KycStatus,
    MatchStatus,
    ResidentProfile,
    Room,
    RoomStatus,
    RoomType,
    RoommateMatch,
    User,
)
from app.services.matchmaking import (
    clears_hostel_gate,
    has_active_booking,
    passes_gender_policy,
    score_pair,
)


def _attempt_prebooked_pair(
    session: Session, profile: ResidentProfile, user: User, room: Room, booking: Booking
) -> Optional[RoommateMatch]:
    """Pre-decided roommates (HLD §5.3 / TDD A6).

    Requires registration, reciprocity (B lists A's exact phone), both VERIFIED,
    and B satisfying the room/hostel policy; otherwise falls back to pool matching.
    """
    phone = (profile.prebooked_roommate_phone or "").strip()
    if not phone:
        return None

    partner_user = session.exec(select(User).where(User.phone == phone)).first()
    if not partner_user or partner_user.kyc_status != KycStatus.VERIFIED.value:
        return None
    if user.kyc_status != KycStatus.VERIFIED.value:
        return None
    partner = session.get(ResidentProfile, partner_user.id)
    if not partner:
        return None
    if (partner.prebooked_roommate_phone or "").strip() != user.phone:
        return None
    if has_active_booking(session, partner.user_id):
        return None

    hostel = session.get(Hostel, room.hostel_id)
    rooms = list(session.exec(select(Room).where(Room.hostel_id == hostel.id)).all())
    if not passes_gender_policy(partner, profile, hostel):
        return None
    if not clears_hostel_gate(partner, hostel, rooms):
        return None

    pair = score_pair(profile, partner)
    score = int(round(pair["overall_score"])) if pair else 0
    breakdown = pair["breakdown"] if pair else {}

    match = RoommateMatch(
        room_id=room.id,
        resident_a=profile.user_id,
        resident_b=partner.user_id,
        a_accepted=True,
        b_accepted=True,
        score=score,
        breakdown=breakdown,
        status=MatchStatus.CONFIRMED.value,
    )
    session.add(match)
    session.flush()

    booking.roommate_match_id = match.id
    session.add(booking)
    session.add(
        Booking(
            resident_id=partner.user_id,
            room_id=room.id,
            roommate_match_id=match.id,
            status=BookingStatus.REQUESTED.value,
        )
    )
    return match


def create_booking(
    session: Session, profile: ResidentProfile, user: User, room_id: uuid.UUID
) -> tuple[Booking, Optional[RoommateMatch]]:
    room = session.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    if room.status != RoomStatus.AVAILABLE.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room is full")
    if has_active_booking(session, profile.user_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an active booking. Cancel it first.",
        )

    booking = Booking(
        resident_id=profile.user_id, room_id=room.id, status=BookingStatus.REQUESTED.value
    )
    session.add(booking)
    session.flush()

    match = None
    if room.type == RoomType.SHARED.value:
        match = _attempt_prebooked_pair(session, profile, user, room, booking)

    session.commit()
    session.refresh(booking)
    return booking, match


def cancel_booking(session: Session, booking: Booking, profile: ResidentProfile) -> str:
    """Cancellation cascades (HLD §5.2.3). Returns a human-readable outcome."""
    if booking.resident_id != profile.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your booking")

    if booking.status == BookingStatus.REQUESTED.value:
        booking.status = BookingStatus.CANCELLED.value
        session.add(booking)
        outcome = "Booking cancelled."
        if booking.roommate_match_id:
            match = session.get(RoommateMatch, booking.roommate_match_id)
            if match and match.status != MatchStatus.REJECTED.value:
                match.status = MatchStatus.REJECTED.value
                session.add(match)
            partner = session.exec(
                select(Booking).where(
                    Booking.roommate_match_id == booking.roommate_match_id,
                    Booking.id != booking.id,
                    Booking.status == BookingStatus.REQUESTED.value,
                )
            ).first()
            if partner:
                partner.roommate_match_id = None
                session.add(partner)
            outcome = "Booking cancelled. Roommate pair dissolved; partner remains REQUESTED."
        session.commit()
        return outcome

    if booking.status == BookingStatus.CONFIRMED.value:
        booking.status = BookingStatus.CANCELLED.value
        session.add(booking)
        released = 1
        if booking.roommate_match_id:
            match = session.get(RoommateMatch, booking.roommate_match_id)
            if match and match.status != MatchStatus.REJECTED.value:
                match.status = MatchStatus.REJECTED.value
                session.add(match)
            partner = session.exec(
                select(Booking).where(
                    Booking.roommate_match_id == booking.roommate_match_id,
                    Booking.id != booking.id,
                    Booking.status == BookingStatus.CONFIRMED.value,
                )
            ).first()
            if partner:
                partner.status = BookingStatus.REQUESTED.value
                partner.roommate_match_id = None
                session.add(partner)
                released = 2
        room = session.get(Room, booking.room_id)
        room.occupied_count = max(0, room.occupied_count - released)
        room.status = RoomStatus.AVAILABLE.value
        session.add(room)
        session.commit()
        return "Confirmed booking cancelled; room inventory released."

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Booking in state {booking.status} cannot be cancelled.",
    )
