"""Guard tests (TDD §12.3): unauthenticated / unverified / wrong-role rejected."""
from sqlmodel import select

from app.models import Hostel, Room
from tests.conftest import create_resident_profile, login, submit_kyc
from tests.factories import make_hostel, make_owner, make_room


def test_unauthenticated_rejected(make_client):
    client = make_client()
    assert client.get("/api/residents/me").status_code == 401
    assert client.get("/api/owners/hostels").status_code == 401
    assert client.post("/api/bookings", json={"roomId": "x"}).status_code == 401


def test_wrong_role_rejected(make_client):
    client = make_client()
    login(client, "8100000001", "RESIDENT")
    assert client.get("/api/owners/hostels").status_code == 403
    assert client.post("/api/owners/profile", data={"name": "x", "contact": "y"}).status_code == 403

    owner = make_client()
    login(owner, "8100000002", "OWNER")
    assert owner.get("/api/residents/me").status_code == 403
    assert owner.get("/api/residents/recommendations").status_code == 403


def test_booking_requires_kyc_verified(make_client, session):
    owner = make_owner(session)
    room = make_room(session, make_hostel(session, owner))
    session.commit()

    client = make_client()
    login(client, "8100000003", "RESIDENT")
    create_resident_profile(client)
    # no KYC submitted -> kyc_status == NONE
    r = client.post("/api/bookings", json={"roomId": str(room.id)})
    assert r.status_code == 403
    assert "KYC" in r.json()["detail"]


def test_listing_requires_kyc_verified(make_client):
    client = make_client()
    login(client, "8100000004", "OWNER")
    client.post("/api/owners/profile", data={"name": "O", "contact": "c"})
    r = client.post(
        "/api/owners/hostels",
        data={"name": "H", "address": "A", "location": "l", "gender_policy": "COED"},
    )
    assert r.status_code == 403


def test_one_role_per_account(make_client):
    client = make_client()
    login(client, "8100000005", "RESIDENT")
    r = client.post("/api/auth/request-otp", data={"phone": "8100000005", "role": "OWNER"})
    assert r.status_code == 400


def test_otp_rate_limit(make_client):
    client = make_client()
    client.post("/api/auth/request-otp", data={"phone": "8100000006", "role": "RESIDENT"})
    for _ in range(5):
        client.post("/api/auth/verify-otp", data={"phone": "8100000006", "code": "000000"})
    # 6th attempt exceeds MAX_OTP_ATTEMPTS even with the right code
    r = client.post("/api/auth/verify-otp", data={"phone": "8100000006", "code": "123456"})
    assert r.status_code == 400
