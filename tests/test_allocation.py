"""commit_booking_allocation — HLD §7.1 invariants."""
import pytest
from fastapi import HTTPException
from sqlmodel import select

from app.models import Booking, BookingStatus, MatchStatus, RoomStatus, RoommateMatch
from app.services.booking_allocation import commit_booking_allocation, reject_booking
from tests.factories import (
    make_hostel,
    make_owner,
    make_pair_on_room,
    make_resident,
    make_room,
)


def _shared_pair_scenario(session):
    owner = make_owner(session)
    hostel = make_hostel(session, owner)
    room = make_room(session, hostel, type="SHARED", capacity=2)
    _, a = make_resident(session)
    _, b = make_resident(session)
    match, booking_a, booking_b = make_pair_on_room(session, room, a, b)
    session.commit()
    return owner, hostel, room, a, b, match, booking_a, booking_b


def test_shared_pair_confirms_atomically_and_sweeps(session):
    owner, hostel, room, a, b, match, booking_a, booking_b = _shared_pair_scenario(session)
    # Competitors: a REQUESTED single application + a PROPOSED match on the same room
    _, c = make_resident(session)
    _, d = make_resident(session)
    _, e = make_resident(session)
    competing_booking = Booking(resident_id=c.user_id, room_id=room.id,
                                status=BookingStatus.REQUESTED.value)
    session.add(competing_booking)
    competing_match, _, _ = make_pair_on_room(
        session, room, d, e, match_status=MatchStatus.PROPOSED
    )
    session.commit()

    result = commit_booking_allocation(session, booking_a.id)
    assert result["result"] == "confirmed"
    assert result["confirmed"] == 2  # allocation_delta = both locked active rows

    session.expire_all()
    assert session.get(Booking, booking_a.id).status == BookingStatus.CONFIRMED.value
    assert session.get(Booking, booking_b.id).status == BookingStatus.CONFIRMED.value
    room = session.get(type(room), room.id)
    assert room.occupied_count == 2
    assert room.status == RoomStatus.FULL.value
    # FULL sweep: competing REQUESTED bookings and lingering matches rejected
    assert session.get(Booking, competing_booking.id).status == BookingStatus.REJECTED.value
    assert session.get(RoommateMatch, competing_match.id).status == MatchStatus.REJECTED.value
    # The approved pair's own match is untouched
    assert session.get(RoommateMatch, match.id).status == MatchStatus.CONFIRMED.value


def test_approval_is_idempotent(session):
    *_, booking_a, _ = _shared_pair_scenario(session)
    assert commit_booking_allocation(session, booking_a.id)["result"] == "confirmed"
    assert commit_booking_allocation(session, booking_a.id)["result"] == "already_confirmed"
    session.expire_all()
    # occupied_count must not double-increment
    from app.models import Room
    rooms = session.exec(select(Room)).all()
    assert rooms[0].occupied_count == 2


def test_capacity_exhaustion_409(session):
    owner = make_owner(session)
    hostel = make_hostel(session, owner)
    room = make_room(session, hostel, type="SHARED", capacity=2, occupied_count=1)
    _, a = make_resident(session)
    _, b = make_resident(session)
    match, booking_a, booking_b = make_pair_on_room(session, room, a, b)
    session.commit()

    with pytest.raises(HTTPException) as exc:
        commit_booking_allocation(session, booking_a.id)
    assert exc.value.status_code == 409


def test_shared_room_without_pair_rejected_400(session):
    owner = make_owner(session)
    hostel = make_hostel(session, owner)
    room = make_room(session, hostel, type="SHARED", capacity=2)
    _, a = make_resident(session)
    solo = Booking(resident_id=a.user_id, room_id=room.id, status=BookingStatus.REQUESTED.value)
    session.add(solo)
    session.commit()

    with pytest.raises(HTTPException) as exc:
        commit_booking_allocation(session, solo.id)
    assert exc.value.status_code == 400


def test_single_room_confirms_with_delta_one(session):
    owner = make_owner(session)
    hostel = make_hostel(session, owner)
    room = make_room(session, hostel, type="SINGLE", capacity=1)
    _, a = make_resident(session)
    booking = Booking(resident_id=a.user_id, room_id=room.id, status=BookingStatus.REQUESTED.value)
    session.add(booking)
    session.commit()

    result = commit_booking_allocation(session, booking.id)
    assert result["confirmed"] == 1
    session.expire_all()
    from app.models import Room
    refreshed = session.get(Room, room.id)
    assert refreshed.occupied_count == 1
    assert refreshed.status == RoomStatus.FULL.value


def test_reject_rejects_pair_and_match(session):
    *_, match, booking_a, booking_b = _shared_pair_scenario(session)
    result = reject_booking(session, booking_a.id)
    assert result["rejected"] == 2
    session.expire_all()
    assert session.get(Booking, booking_a.id).status == BookingStatus.REJECTED.value
    assert session.get(Booking, booking_b.id).status == BookingStatus.REJECTED.value
    assert session.get(RoommateMatch, match.id).status == MatchStatus.REJECTED.value


def test_cancelled_booking_cannot_be_approved(session):
    owner = make_owner(session)
    hostel = make_hostel(session, owner)
    room = make_room(session, hostel, type="SINGLE", capacity=1)
    _, a = make_resident(session)
    booking = Booking(resident_id=a.user_id, room_id=room.id, status=BookingStatus.CANCELLED.value)
    session.add(booking)
    session.commit()

    with pytest.raises(HTTPException) as exc:
        commit_booking_allocation(session, booking.id)
    assert exc.value.status_code == 409
