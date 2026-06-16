"""Cancellation cascades (HLD §5.2.3) + pre-decided roommates (§5.3 / A6)."""
import pytest
from fastapi import HTTPException
from sqlmodel import select

from app.models import (
    Booking,
    BookingStatus,
    KycStatus,
    MatchStatus,
    Room,
    RoomStatus,
    RoommateMatch,
    User,
)
from app.services.booking_allocation import commit_booking_allocation
from app.services.booking_lifecycle import cancel_booking, create_booking
from tests.factories import (
    make_hostel,
    make_owner,
    make_pair_on_room,
    make_resident,
    make_room,
)


def test_preapproval_cancel_dissolves_pair_keeps_partner_requested(session):
    owner = make_owner(session)
    room = make_room(session, make_hostel(session, owner))
    _, a = make_resident(session)
    _, b = make_resident(session)
    match, booking_a, booking_b = make_pair_on_room(session, room, a, b)
    session.commit()

    out = cancel_booking(session, booking_b, b)
    session.expire_all()
    assert session.get(Booking, booking_b.id).status == BookingStatus.CANCELLED.value
    assert session.get(RoommateMatch, match.id).status == MatchStatus.REJECTED.value
    partner = session.get(Booking, booking_a.id)
    assert partner.status == BookingStatus.REQUESTED.value
    assert partner.roommate_match_id is None  # A reopens to the candidate pool


def test_postapproval_cancel_releases_inventory_and_resets_partner(session):
    owner = make_owner(session)
    room = make_room(session, make_hostel(session, owner), type="SHARED", capacity=2)
    _, a = make_resident(session)
    _, b = make_resident(session)
    match, booking_a, booking_b = make_pair_on_room(session, room, a, b)
    session.commit()
    commit_booking_allocation(session, booking_a.id)
    session.expire_all()
    assert session.get(Room, room.id).status == RoomStatus.FULL.value

    booking_a = session.get(Booking, booking_a.id)
    cancel_booking(session, booking_a, a)
    session.expire_all()

    assert session.get(Booking, booking_a.id).status == BookingStatus.CANCELLED.value
    partner = session.get(Booking, booking_b.id)
    assert partner.status == BookingStatus.REQUESTED.value
    assert partner.roommate_match_id is None
    assert session.get(RoommateMatch, match.id).status == MatchStatus.REJECTED.value
    refreshed = session.get(Room, room.id)
    assert refreshed.occupied_count == 0  # -2, atomic with status rollback
    assert refreshed.status == RoomStatus.AVAILABLE.value


def test_cannot_cancel_someone_elses_booking(session):
    owner = make_owner(session)
    room = make_room(session, make_hostel(session, owner))
    _, a = make_resident(session)
    _, b = make_resident(session)
    booking = Booking(resident_id=a.user_id, room_id=room.id,
                      status=BookingStatus.REQUESTED.value)
    session.add(booking)
    session.commit()

    with pytest.raises(HTTPException) as exc:
        cancel_booking(session, booking, b)
    # 404, not 403: never confirm another resident's booking exists (enumeration guard).
    assert exc.value.status_code == 404


def test_a6_prebooked_reciprocal_pair_creates_confirmed_match(session):
    owner = make_owner(session)
    room = make_room(session, make_hostel(session, owner), type="SHARED", capacity=2)
    user_a, a = make_resident(session, phone="9111111111")
    user_b, b = make_resident(session, phone="9222222222")
    a.prebooked_roommate_phone = "9222222222"
    b.prebooked_roommate_phone = "9111111111"
    session.add(a)
    session.add(b)
    session.commit()

    booking, match = create_booking(session, a, user_a, room.id)
    assert match is not None
    assert match.status == MatchStatus.CONFIRMED.value
    assert match.a_accepted and match.b_accepted
    linked = session.exec(
        select(Booking).where(Booking.roommate_match_id == match.id)
    ).all()
    assert len(linked) == 2
    assert all(bk.status == BookingStatus.REQUESTED.value for bk in linked)


def test_a6_falls_back_without_reciprocity(session):
    owner = make_owner(session)
    room = make_room(session, make_hostel(session, owner), type="SHARED", capacity=2)
    user_a, a = make_resident(session, phone="9333333333")
    user_b, b = make_resident(session, phone="9444444444")
    a.prebooked_roommate_phone = "9444444444"  # B does NOT reciprocate
    session.add(a)
    session.commit()

    booking, match = create_booking(session, a, user_a, room.id)
    assert match is None
    assert booking.roommate_match_id is None


def test_a6_falls_back_when_partner_unverified(session):
    owner = make_owner(session)
    room = make_room(session, make_hostel(session, owner), type="SHARED", capacity=2)
    user_a, a = make_resident(session, phone="9555555555")
    user_b, b = make_resident(session, phone="9666666666", kyc=KycStatus.NONE)
    a.prebooked_roommate_phone = "9666666666"
    b.prebooked_roommate_phone = "9555555555"
    session.add(a)
    session.add(b)
    session.commit()

    booking, match = create_booking(session, a, user_a, room.id)
    assert match is None


def test_double_active_booking_blocked(session):
    owner = make_owner(session)
    room = make_room(session, make_hostel(session, owner), type="SINGLE", capacity=1)
    room2 = make_room(session, make_hostel(session, owner), type="SINGLE", capacity=1)
    user_a, a = make_resident(session)
    session.commit()

    create_booking(session, a, user_a, room.id)
    with pytest.raises(HTTPException) as exc:
        create_booking(session, a, user_a, room2.id)
    assert exc.value.status_code == 409
