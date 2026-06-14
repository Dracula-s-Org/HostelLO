"""Ordered, idempotent booking allocation — HLD §7.1 Listing 7, verbatim flow.

Lock order is the contract: sorted booking rows first, then the room row.
Do not reorder. `with_for_update()` degrades to a no-op on SQLite (single
local writer) and takes real row locks on Neon Postgres.
"""
from fastapi import HTTPException, status
from sqlmodel import Session

from app.models import Booking, BookingStatus, Hostel, MatchStatus, Room, RoomStatus, RoomType, RoommateMatch


def commit_booking_allocation(db_session: Session, booking_id) -> dict:
    # Fetch initial non-locked target to establish structural metadata boundaries
    base_booking = db_session.query(Booking).filter(Booking.id == booking_id).first()
    if not base_booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking Not Found")

    if base_booking.status in (BookingStatus.REJECTED.value, BookingStatus.CANCELLED.value):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Booking is {base_booking.status} and cannot be approved.",
        )

    # Establish deterministic booking IDs array to prevent circular cross-row deadlocks
    booking_ids_to_lock = [base_booking.id]

    # Check for active companions still in the REQUESTED state
    is_shared = base_booking.roommate_match_id is not None
    if is_shared:
        companion = (
            db_session.query(Booking)
            .filter(
                Booking.roommate_match_id == base_booking.roommate_match_id,
                Booking.id != base_booking.id,
                Booking.status == BookingStatus.REQUESTED.value,  # gate against stale/cancelled companions
            )
            .first()
        )
        if companion:
            booking_ids_to_lock.append(companion.id)

    # Sort IDs strictly to maintain uniform row-locking order across parallel threads
    booking_ids_to_lock.sort()

    # Acquire explicit row write locks across target booking rows sequentially
    locked_bookings = (
        db_session.query(Booking)
        .filter(Booking.id.in_(booking_ids_to_lock))
        .with_for_update()
        .all()
    )

    # Core idempotency guard: safely exit if a parallel worker already approved this block
    for b in locked_bookings:
        if b.status == BookingStatus.CONFIRMED.value:
            return {"result": "already_confirmed", "confirmed": 0}

    # Acquire write lock on the corresponding room row layout
    room = (
        db_session.query(Room)
        .filter(Room.id == base_booking.room_id)
        .with_for_update()
        .first()
    )
    hostel = db_session.query(Hostel).filter(Hostel.id == room.hostel_id).first()  # noqa: F841

    # Structural invariant: a shared room requires a confirmed, active mate-pair block
    if room.type == RoomType.SHARED.value and not is_shared:
        db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shared accommodations cannot be approved without a confirmed roommate block.",
        )

    # Compute true allocation delta based strictly on the number of active rows locked
    active_rows = [b for b in locked_bookings if b.status == BookingStatus.REQUESTED.value]
    allocation_delta = len(active_rows)
    if allocation_delta == 0:
        return {"result": "noop", "confirmed": 0}

    if room.occupied_count + allocation_delta > room.capacity:
        db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Requested Room Inventory Exhausted",
        )

    # Execute atomic updates
    room.occupied_count += allocation_delta

    # 1. Update locked active rows to the CONFIRMED state
    for b in active_rows:
        b.status = BookingStatus.CONFIRMED.value

    # 2. Check capacity boundaries and perform cleanup sweeps
    if room.occupied_count == room.capacity:
        room.status = RoomStatus.FULL.value

        # Synchronously reject all competing REQUESTED booking applications
        db_session.query(Booking).filter(
            Booking.room_id == room.id,
            Booking.status == BookingStatus.REQUESTED.value,
        ).update({"status": BookingStatus.REJECTED.value}, synchronize_session="fetch")

        # Synchronously reject lingering PROPOSED/CONFIRMED roommate matches for this room
        if is_shared:
            db_session.query(RoommateMatch).filter(
                RoommateMatch.room_id == room.id,
                RoommateMatch.id != base_booking.roommate_match_id,
                RoommateMatch.status.in_(
                    [MatchStatus.PROPOSED.value, MatchStatus.CONFIRMED.value]
                ),
            ).update({"status": MatchStatus.REJECTED.value}, synchronize_session="fetch")

    db_session.commit()
    return {"result": "confirmed", "confirmed": allocation_delta, "room_full": room.status == RoomStatus.FULL.value}


def reject_booking(db_session: Session, booking_id) -> dict:
    """Owner denial: rejects the application; a linked REQUESTED companion and
    its match block are rejected with it (owner reviews the pair as a unit)."""
    base_booking = db_session.query(Booking).filter(Booking.id == booking_id).first()
    if not base_booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking Not Found")
    if base_booking.status != BookingStatus.REQUESTED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Only REQUESTED bookings can be rejected (current: {base_booking.status}).",
        )

    base_booking.status = BookingStatus.REJECTED.value
    rejected = 1

    if base_booking.roommate_match_id:
        companion = (
            db_session.query(Booking)
            .filter(
                Booking.roommate_match_id == base_booking.roommate_match_id,
                Booking.id != base_booking.id,
                Booking.status == BookingStatus.REQUESTED.value,
            )
            .first()
        )
        if companion:
            companion.status = BookingStatus.REJECTED.value
            rejected += 1
        match = db_session.query(RoommateMatch).filter(
            RoommateMatch.id == base_booking.roommate_match_id
        ).first()
        if match and match.status != MatchStatus.REJECTED.value:
            match.status = MatchStatus.REJECTED.value

    db_session.commit()
    return {"result": "rejected", "rejected": rejected}
