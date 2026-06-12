"""TDD §1 demo success criteria, end-to-end over the HTTP API:
owner lists → resident discovers → shared booking → roommate consent →
owner approves → pair CONFIRMED.
"""
import re

from sqlmodel import select

from app.models import Booking, BookingStatus, MatchStatus, Room, RoomStatus, RoommateMatch
from tests.conftest import create_resident_profile, login, submit_kyc


def test_golden_path(make_client, session):
    # 1. Owner signs up, completes KYC, lists a hostel with a shared room
    owner = make_client()
    login(owner, "8000000001", "OWNER")
    r = owner.post("/api/owners/profile", data={"name": "Rajesh Kumar", "contact": "r@pg.in"})
    assert r.status_code == 200
    submit_kyc(owner)
    r = owner.post(
        "/api/owners/hostels",
        data={
            "name": "Sunrise Residency",
            "address": "12 Main Rd",
            "location": "koramangala",
            "gender_policy": "COED",
            "listing_tier": "FREE",
            "amenities": "wifi, mess",
            "allow_smoking": "false",
            "allow_drinking": "false",
            "veg_only": "false",
        },
    )
    assert r.status_code == 200, r.text
    hostel_id = session.exec(select(Room.hostel_id)).first()  # none yet — get via hostels table
    from app.models import Hostel

    hostel = session.exec(select(Hostel)).first()
    r = owner.post(
        f"/api/hostels/{hostel.id}/rooms",
        data={"type": "SHARED", "capacity": "2", "price": "6000"},
        files={"images": ("room.jpg", b"fake-room-image", "image/jpeg")},
    )
    assert r.status_code == 200, r.text
    room = session.exec(select(Room)).first()
    assert room.image_paths, "image upload should persist a reference"

    # 2. Resident A signs up, completes profile + KYC
    res_a = make_client()
    login(res_a, "8000000002", "RESIDENT")
    create_resident_profile(res_a, name="Aarav Sharma")
    submit_kyc(res_a)

    # 3. Resident A sees a filtered, ranked list
    r = res_a.get("/api/residents/recommendations")
    assert r.status_code == 200
    assert "Sunrise Residency" in r.text

    # 4. Resident A books the SHARED room
    r = res_a.post("/api/bookings", json={"roomId": str(room.id)})
    assert r.status_code == 200, r.text
    booking_a = session.exec(select(Booking)).first()
    assert booking_a.status == BookingStatus.REQUESTED.value

    # 5. Resident B signs up — compatible profile
    res_b = make_client()
    login(res_b, "8000000003", "RESIDENT")
    create_resident_profile(res_b, name="Vihaan Patel", cleanliness=3, gaming_freq=3)
    submit_kyc(res_b)

    # 6. A sees B as a DPDP-redacted candidate (first name only, no phone)
    r = res_a.get(f"/api/bookings/{booking_a.id}/roommate-recommendations")
    assert r.status_code == 200, r.text
    assert "Vihaan" in r.text
    assert "8000000003" not in r.text  # phone never leaks pre-confirmation
    assert "Patel" not in r.text  # last name hidden in discovery
    candidate_id = re.search(r'name="candidateId" value="([0-9a-f-]+)"', r.text).group(1)

    # 7. A proposes, B accepts -> match CONFIRMED + linked Booking B auto-created
    r = res_a.post("/api/roommate-matches", data={"candidateId": candidate_id})
    assert r.status_code == 200, r.text
    match = session.exec(select(RoommateMatch)).first()
    assert match.status == MatchStatus.PROPOSED.value and match.a_accepted

    r = res_b.post(f"/api/roommate-matches/{match.id}/accept")
    assert r.status_code == 200, r.text
    session.expire_all()
    match = session.get(RoommateMatch, match.id)
    assert match.status == MatchStatus.CONFIRMED.value and match.b_accepted
    bookings = session.exec(select(Booking)).all()
    assert len(bookings) == 2
    assert all(b.roommate_match_id == match.id for b in bookings)

    # 8. Owner sees the application with redacted applicant data
    r = owner.get("/api/owners/bookings")
    assert r.status_code == 200
    assert "Aarav" in r.text and "Sharma" not in r.text

    # 9. Owner approves once -> both bookings CONFIRMED, room FULL
    r = owner.post(f"/api/bookings/{booking_a.id}/approve")
    assert r.status_code == 200, r.text
    session.expire_all()
    statuses = {b.status for b in session.exec(select(Booking)).all()}
    assert statuses == {BookingStatus.CONFIRMED.value}
    refreshed = session.get(Room, room.id)
    assert refreshed.occupied_count == 2
    assert refreshed.status == RoomStatus.FULL.value
