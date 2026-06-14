"""Regression tests for the security-hardening pass.

Each test pins a specific fix from the security review so a future change can't
silently regress it.
"""
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.config import OperationalConfig
from app.models import Booking, BookingStatus, MatchStatus, RoomStatus
from app.services.booking_allocation import commit_booking_allocation
from app.services.booking_lifecycle import cancel_booking
from tests.conftest import (
    RESIDENT_FORM,
    _JPEG_BYTES,
    create_resident_profile,
    login,
    submit_kyc,
)
from tests.factories import (
    make_hostel,
    make_owner,
    make_pair_on_room,
    make_resident,
    make_room,
)


# --- PII / DPDP: /me must not echo a third party's phone (CRITICAL-1) ---

def test_me_hides_third_party_roommate_phone(make_client):
    c = make_client()
    login(c, "8200000001", "RESIDENT")
    create_resident_profile(c, prebooked_roommate_phone="9998887776")
    body = c.get("/api/residents/me").json()
    assert "prebooked_roommate_phone" not in body          # raw field never exposed
    assert body["has_prebooked_roommate"] is True
    assert body["prebooked_roommate_phone_masked"] == "999****76"
    assert "9998887776" not in str(body)                   # full number never leaks


# --- Upload validation: only real images/PDFs accepted (C1) ---

def test_kyc_rejects_non_document(make_client):
    c = make_client()
    login(c, "8200000002", "RESIDENT")
    r = c.post(
        "/api/kyc/submit",
        data={"doc_type": "AADHAAR"},
        files={"document": ("evil.jpg", b"<html>not an image</html>", "image/jpeg")},
    )
    assert r.status_code == 400


# --- Allocation: atomic capacity guard blocks overselling (CRITICAL) ---

def test_allocation_blocks_oversell(session):
    owner = make_owner(session)
    hostel = make_hostel(session, owner)
    room = make_room(
        session, hostel, type="SINGLE", capacity=1,
        occupied_count=1, status=RoomStatus.AVAILABLE.value,
    )
    _, profile = make_resident(session)
    booking = Booking(resident_id=profile.user_id, room_id=room.id, status=BookingStatus.REQUESTED.value)
    session.add(booking)
    session.commit()

    with pytest.raises(HTTPException) as exc:
        commit_booking_allocation(session, booking.id, owner_user_id=owner.user_id)
    assert exc.value.status_code == 409


# --- Authorization: an owner cannot approve a booking on another owner's room ---

def test_approve_foreign_room_forbidden(session):
    owner_a = make_owner(session)
    owner_b = make_owner(session)
    hostel = make_hostel(session, owner_a)
    room = make_room(session, hostel, type="SINGLE", capacity=1)
    _, profile = make_resident(session)
    booking = Booking(resident_id=profile.user_id, room_id=room.id, status=BookingStatus.REQUESTED.value)
    session.add(booking)
    session.commit()

    with pytest.raises(HTTPException) as exc:
        commit_booking_allocation(session, booking.id, owner_user_id=owner_b.user_id)
    # 404, not 403: a foreign booking is indistinguishable from a missing one, so
    # the response can't be used to confirm the booking/room exists (enumeration guard).
    assert exc.value.status_code == 404


# --- Config: production refuses to boot on insecure defaults (C3) ---

def test_production_config_rejects_insecure_defaults():
    # Env has MOCK_OTP/MOCK_KYC=true (conftest) and JWT_SECRET is the dev default,
    # so constructing a production config must fail fast.
    with pytest.raises(ValidationError):
        OperationalConfig(ENVIRONMENT="production")


def test_production_config_accepts_hardened_values():
    cfg = OperationalConfig(
        ENVIRONMENT="production",
        JWT_SECRET="x" * 48,
        MOCK_OTP=False,
        MOCK_KYC=False,
    )
    assert cfg.is_production is True
    assert cfg.cookie_secure is True


# --- Cancel cascade: occupancy is recomputed authoritatively, never drifts ---

def test_confirmed_cancel_recomputes_occupancy_from_truth(session):
    """The ledger the capacity gate trusts must equal the real CONFIRMED count,
    even if occupied_count was already inconsistent before the cancel."""
    owner = make_owner(session)
    hostel = make_hostel(session, owner)
    room = make_room(session, hostel, type="SHARED", capacity=2)
    _, profile_a = make_resident(session)
    _, profile_b = make_resident(session)
    _, booking_a, booking_b = make_pair_on_room(
        session, room, profile_a, profile_b, match_status=MatchStatus.CONFIRMED
    )
    booking_a.status = BookingStatus.CONFIRMED.value
    booking_b.status = BookingStatus.CONFIRMED.value
    room.occupied_count = 2
    room.status = RoomStatus.FULL.value
    session.add_all([booking_a, booking_b, room])
    session.commit()

    cancel_booking(session, booking_a, profile_a)

    session.refresh(room)
    # Per HLD §5.2.3 the pair dissolves (partner -> REQUESTED), so 0 CONFIRMED remain.
    # occupied_count is recomputed from the real CONFIRMED count, never via fragile deltas.
    assert room.occupied_count == 0
    assert room.status == RoomStatus.AVAILABLE.value
    # The CHECK constraint (occupied_count <= capacity) is the final anti-drift backstop.


# --- Rate limiting: rotating phones bypasses the per-phone cap, not the per-IP one (#1) ---

def test_request_otp_rate_limited_per_ip(make_client):
    from app.ratelimit import limiter

    limiter.enabled = True  # the suite runs with it off; pin it on for this test
    try:
        c = make_client()
        headers = {"X-Forwarded-For": "203.0.113.77"}
        statuses = [
            c.post(
                "/api/auth/request-otp",
                data={"phone": f"73000000{i:02d}", "role": "RESIDENT"},
                headers=headers,
            ).status_code
            for i in range(7)
        ]
        # Each phone is unique, so the per-phone send cap never trips — only the
        # 5/min per-IP limit does, which is the SMS-bomb / DB-bloat vector.
        assert 429 in statuses
    finally:
        limiter.enabled = False


# --- Input validation: resident domain fields are allowlisted/bounded (#3) ---

def test_resident_profile_rejects_invalid_enum(make_client):
    c = make_client()
    login(c, "8200000010", "RESIDENT")
    r = c.post("/api/residents/profile", data={**RESIDENT_FORM, "gender": "ALIEN"})
    assert r.status_code == 400


def test_resident_profile_rejects_inverted_budget(make_client):
    c = make_client()
    login(c, "8200000011", "RESIDENT")
    r = c.post("/api/residents/profile", data={**RESIDENT_FORM, "budget_min": "9000", "budget_max": "5000"})
    assert r.status_code == 400


def test_resident_profile_rejects_negative_budget(make_client):
    c = make_client()
    login(c, "8200000012", "RESIDENT")
    r = c.post("/api/residents/profile", data={**RESIDENT_FORM, "budget_min": "-1"})
    assert r.status_code == 422  # Form(..., ge=0) -> request validation error


def test_resident_profile_rejects_bad_prebooked_phone(make_client):
    c = make_client()
    login(c, "8200000013", "RESIDENT")
    r = c.post("/api/residents/profile", data={**RESIDENT_FORM, "prebooked_roommate_phone": "not-a-phone"})
    assert r.status_code == 400


def test_kyc_rejects_unknown_doc_type(make_client):
    c = make_client()
    login(c, "8200000014", "RESIDENT")
    r = c.post(
        "/api/kyc/submit",
        data={"doc_type": "TOTALLY_FAKE"},
        files={"document": ("id.jpg", _JPEG_BYTES, "image/jpeg")},
    )
    assert r.status_code == 400


# --- Per-owner abuse cap: rooms are bounded per owner (#1 secondary) ---

def test_per_owner_room_cap(make_client, monkeypatch):
    from app.config import config as app_config

    monkeypatch.setattr(app_config, "MAX_ROOMS_PER_OWNER", 1)

    owner = make_client()
    login(owner, "8200000020", "OWNER")
    owner.post("/api/owners/profile", data={"name": "O", "contact": "c@x.in"})
    submit_kyc(owner)
    created = owner.post(
        "/api/owners/hostels",
        data={"name": "H", "address": "A", "location": "l", "gender_policy": "COED"},
    )
    assert created.status_code == 200, created.text
    hostel_id = created.json()["id"]

    room_form = {"type": "SINGLE", "capacity": "1", "price": "5000"}
    first = owner.post(f"/api/hostels/{hostel_id}/rooms", data=room_form)
    assert first.status_code == 200, first.text
    second = owner.post(f"/api/hostels/{hostel_id}/rooms", data=room_form)
    assert second.status_code == 400
