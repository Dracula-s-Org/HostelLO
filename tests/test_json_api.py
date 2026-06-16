"""JSON contract for the React-frontend endpoints (BACKEND-HANDOFF Parts A & B).

Drives the real HTTP API end-to-end and asserts the JSON shapes the client
wires against.
"""
from sqlmodel import select

from app.models import Booking, Hostel, Room
from tests.conftest import _JPEG_BYTES, create_resident_profile, login, submit_kyc


def _list_a_hostel(owner):
    """Owner with KYC lists a hostel + one SHARED room. Returns nothing; the
    caller reads the rows back through the session fixture."""
    owner.post("/api/owners/profile", data={"name": "Rajesh Kumar", "contact": "r@pg.in"})
    submit_kyc(owner)
    r = owner.post(
        "/api/owners/hostels",
        data={
            "name": "Sunrise Residency",
            "address": "12 Main Rd",
            "location": "koramangala",
            "gender_policy": "COED",
            "listing_tier": "PREMIUM",
            "amenities": "wifi, mess",
        },
    )
    assert r.status_code == 200, r.text


def test_recommendations_json_shape(make_client, session):
    owner = make_client()
    login(owner, "8000000001", "OWNER")
    _list_a_hostel(owner)
    hostel = session.exec(select(Hostel)).first()
    owner.post(
        f"/api/hostels/{hostel.id}/rooms",
        data={"type": "SHARED", "capacity": "3", "price": "8000"},
    )

    res = make_client()
    login(res, "8000000002", "RESIDENT")
    create_resident_profile(res, preferred_location="koramangala")

    r = res.get("/api/residents/recommendations")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "results" in body
    card = next(c for c in body["results"] if c["hostel"]["name"] == "Sunrise Residency")
    assert card["hostel"]["listing_tier"] == "PREMIUM"
    assert set(["score", "price_fit", "location_fit", "amenity_fit"]) <= card.keys()
    room = card["rooms"][0]
    assert room["image_count"] == 0
    assert "image_paths" not in room  # raw paths never leak


def test_bookings_mine_json(make_client, session):
    owner = make_client()
    login(owner, "8000000001", "OWNER")
    _list_a_hostel(owner)
    hostel = session.exec(select(Hostel)).first()
    owner.post(f"/api/hostels/{hostel.id}/rooms", data={"type": "SINGLE", "capacity": "1", "price": "9000"})
    room = session.exec(select(Room)).first()

    res = make_client()
    login(res, "8000000002", "RESIDENT")
    create_resident_profile(res)
    submit_kyc(res)
    res.post("/api/bookings", json={"roomId": str(room.id)})

    r = res.get("/api/bookings/mine")
    assert r.status_code == 200, r.text
    bookings = r.json()["bookings"]
    assert len(bookings) == 1
    b = bookings[0]
    assert b["status"] == "REQUESTED"
    assert b["room"]["id"] == str(room.id)
    assert b["hostel"]["name"] == "Sunrise Residency"
    assert b["roommate_match_id"] is None


def test_hostel_detail_and_rooms_b1_b2(make_client, session):
    owner = make_client()
    login(owner, "8000000001", "OWNER")
    _list_a_hostel(owner)
    hostel = session.exec(select(Hostel)).first()
    owner.post(f"/api/hostels/{hostel.id}/rooms", data={"type": "SHARED", "capacity": "2", "price": "6000"})

    res = make_client()
    login(res, "8000000002", "RESIDENT")
    create_resident_profile(res)

    # B1
    r = res.get(f"/api/hostels/{hostel.id}")
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "Sunrise Residency"
    assert r.json()["id"] == str(hostel.id)

    # B1 — unknown hostel 404s
    import uuid

    assert res.get(f"/api/hostels/{uuid.uuid4()}").status_code == 404

    # B2
    r = res.get(f"/api/hostels/{hostel.id}/rooms")
    assert r.status_code == 200, r.text
    rooms = r.json()["rooms"]
    assert len(rooms) == 1 and rooms[0]["type"] == "SHARED"
    assert "image_paths" not in rooms[0]


def test_hostel_reads_require_resident_auth(make_client, session):
    owner = make_client()
    login(owner, "8000000001", "OWNER")
    _list_a_hostel(owner)
    hostel = session.exec(select(Hostel)).first()

    anon = make_client()
    assert anon.get(f"/api/hostels/{hostel.id}").status_code == 401
    # Owner role can't hit resident-scoped reads
    assert owner.get(f"/api/hostels/{hostel.id}").status_code == 403


def test_owner_edit_hostel_b3(make_client, session):
    owner = make_client()
    login(owner, "8000000001", "OWNER")
    _list_a_hostel(owner)
    hostel = session.exec(select(Hostel)).first()

    r = owner.put(
        f"/api/owners/hostels/{hostel.id}",
        data={
            "name": "Sunrise Residency (renovated)",
            "address": "12 Main Rd",
            "location": "indiranagar",
            "gender_policy": "MALE",
            "listing_tier": "FREE",
            "amenities": "wifi, ac, gym",
            "veg_only": "true",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name"] == "Sunrise Residency (renovated)"
    assert body["location"] == "indiranagar"
    assert body["gender_policy"] == "MALE"
    assert body["veg_only"] is True
    assert "ac" in body["amenities"]

    session.expire_all()
    refreshed = session.get(Hostel, hostel.id)
    assert refreshed.location == "indiranagar"


def test_owner_cannot_edit_foreign_hostel_b3(make_client, session):
    owner_a = make_client()
    login(owner_a, "8000000001", "OWNER")
    _list_a_hostel(owner_a)
    hostel = session.exec(select(Hostel)).first()

    owner_b = make_client()
    login(owner_b, "8000000009", "OWNER")
    owner_b.post("/api/owners/profile", data={"name": "Other Owner", "contact": "b@pg.in"})
    submit_kyc(owner_b)

    r = owner_b.put(
        f"/api/owners/hostels/{hostel.id}",
        data={
            "name": "Hijacked",
            "address": "x",
            "location": "koramangala",
            "gender_policy": "COED",
            "listing_tier": "FREE",
        },
    )
    assert r.status_code == 404


def test_write_endpoints_return_json(make_client, session):
    owner = make_client()
    login(owner, "8000000001", "OWNER")
    r = owner.post("/api/owners/profile", data={"name": "Rajesh Kumar", "contact": "r@pg.in"})
    assert r.status_code == 200 and r.json()["name"] == "Rajesh Kumar"
    submit_kyc(owner)

    r = owner.post(
        "/api/owners/hostels",
        data={
            "name": "Sunrise Residency",
            "address": "12 Main Rd",
            "location": "koramangala",
            "gender_policy": "COED",
            "listing_tier": "FREE",
        },
    )
    assert r.status_code == 200
    hostel_json = r.json()
    assert hostel_json["name"] == "Sunrise Residency" and "id" in hostel_json

    r = owner.post(
        f"/api/hostels/{hostel_json['id']}/rooms",
        data={"type": "SINGLE", "capacity": "1", "price": "9000"},
    )
    assert r.status_code == 200
    room_json = r.json()
    assert room_json["type"] == "SINGLE" and room_json["image_count"] == 0
    assert "image_paths" not in room_json

    # Resident profile create returns the self view
    res = make_client()
    login(res, "8000000002", "RESIDENT")
    r = res.post("/api/residents/profile", data={
        "name": "Aarav Sharma", "age": "22", "gender": "MALE",
        "budget_min": "5000", "budget_max": "9000", "preferred_location": "koramangala",
        "sleep_schedule": "EARLY", "cleanliness": "4", "diet": "VEG", "social_type": "INTROVERT",
        "gaming_freq": "2", "study_habits": "4", "fitness_freq": "2", "visitors_freq": "1",
    })
    assert r.status_code == 200 and r.json()["name"] == "Aarav Sharma"

    # Place booking returns the booking shape (single room → not shared, no match)
    submit_kyc(res)
    r = res.post("/api/bookings", json={"roomId": room_json["id"]})
    assert r.status_code == 200, r.text
    booking_json = r.json()
    assert booking_json["status"] == "REQUESTED"
    assert booking_json["is_shared"] is False
    assert booking_json["prebooked_match"] is False
    assert booking_json["roommate_match_id"] is None


def test_room_image_readable_by_resident(make_client, session):
    owner = make_client()
    login(owner, "8000000001", "OWNER")
    _list_a_hostel(owner)
    hostel = session.exec(select(Hostel)).first()
    owner.post(
        f"/api/hostels/{hostel.id}/rooms",
        data={"type": "SHARED", "capacity": "2", "price": "6000"},
        files={"images": ("room.jpg", _JPEG_BYTES, "image/jpeg")},
    )
    room = session.exec(select(Room)).first()
    assert room.image_paths  # an image was persisted

    res = make_client()
    login(res, "8000000002", "RESIDENT")
    create_resident_profile(res)
    # Resident can now read room listing images (previously owner-only)
    r = res.get(f"/api/assets/rooms/{room.id}/0")
    assert r.status_code == 200, r.text

    # Auth still required — the gated proxy never serves to anonymous callers
    anon = make_client()
    assert anon.get(f"/api/assets/rooms/{room.id}/0").status_code == 401


def test_booking_detail_owner_contact_gated_on_confirmed(make_client, session):
    """B3: a resident's own booking detail. Owner contact (PII) is null while
    REQUESTED and only revealed once the owner approves (CONFIRMED)."""
    owner = make_client()
    login(owner, "8000000001", "OWNER")
    _list_a_hostel(owner)  # owner name "Rajesh Kumar", contact "r@pg.in"
    hostel = session.exec(select(Hostel)).first()
    owner.post(f"/api/hostels/{hostel.id}/rooms", data={"type": "SINGLE", "capacity": "1", "price": "9000"})
    room = session.exec(select(Room)).first()

    res = make_client()
    login(res, "8000000002", "RESIDENT")
    create_resident_profile(res)
    submit_kyc(res)
    res.post("/api/bookings", json={"roomId": str(room.id)})
    booking_id = res.get("/api/bookings/mine").json()["bookings"][0]["id"]

    # REQUESTED — facility detail visible, owner contact withheld
    r = res.get(f"/api/bookings/{booking_id}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "REQUESTED"
    assert body["hostel"]["address"] == "12 Main Rd"
    assert body["room"]["id"] == str(room.id)
    assert body["owner"] is None

    # Owner approves → CONFIRMED unlocks the contact
    assert owner.post(f"/api/bookings/{booking_id}/approve").status_code == 200
    body = res.get(f"/api/bookings/{booking_id}").json()
    assert body["status"] == "CONFIRMED"
    assert body["owner"] == {"name": "Rajesh Kumar", "contact": "r@pg.in"}


def test_booking_detail_idor_and_auth(make_client, session):
    """A resident can only read their own booking; unknown ids 404; owners are
    out of scope for this resident-facing read."""
    import uuid

    owner = make_client()
    login(owner, "8000000001", "OWNER")
    _list_a_hostel(owner)
    hostel = session.exec(select(Hostel)).first()
    owner.post(f"/api/hostels/{hostel.id}/rooms", data={"type": "SINGLE", "capacity": "1", "price": "9000"})
    room = session.exec(select(Room)).first()

    res_a = make_client()
    login(res_a, "8000000002", "RESIDENT")
    create_resident_profile(res_a)
    submit_kyc(res_a)
    res_a.post("/api/bookings", json={"roomId": str(room.id)})
    booking_id = res_a.get("/api/bookings/mine").json()["bookings"][0]["id"]

    # A different resident must not read A's booking
    res_b = make_client()
    login(res_b, "8000000003", "RESIDENT")
    create_resident_profile(res_b)
    assert res_b.get(f"/api/bookings/{booking_id}").status_code == 403

    # Unknown booking 404s for the owner-of-record
    assert res_a.get(f"/api/bookings/{uuid.uuid4()}").status_code == 404

    # Owner role can't hit a resident-scoped read
    assert owner.get(f"/api/bookings/{booking_id}").status_code == 403

    # Anonymous is rejected before any scoping
    anon = make_client()
    assert anon.get(f"/api/bookings/{booking_id}").status_code == 401


def test_pending_matches_json_a4(make_client, session):
    # Owner + shared room
    owner = make_client()
    login(owner, "8000000001", "OWNER")
    _list_a_hostel(owner)
    hostel = session.exec(select(Hostel)).first()
    owner.post(f"/api/hostels/{hostel.id}/rooms", data={"type": "SHARED", "capacity": "2", "price": "6000"})
    room = session.exec(select(Room)).first()

    # Resident A books + proposes to B
    res_a = make_client()
    login(res_a, "8000000002", "RESIDENT")
    create_resident_profile(res_a, name="Aarav Sharma")
    submit_kyc(res_a)
    res_a.post("/api/bookings", json={"roomId": str(room.id)})

    res_b = make_client()
    login(res_b, "8000000003", "RESIDENT")
    create_resident_profile(res_b, name="Vihaan Patel", cleanliness=3, gaming_freq=3)
    submit_kyc(res_b)

    booking_a = session.exec(select(Booking)).first()
    cands = res_a.get(f"/api/bookings/{booking_a.id}/roommate-recommendations").json()["candidates"]
    cand_id = next(c["candidate_id"] for c in cands if c["first_name"] == "Vihaan")
    res_a.post("/api/roommate-matches", data={"candidateId": cand_id})

    # B sees the incoming proposal as JSON
    r = res_b.get("/api/roommate-matches/pending")
    assert r.status_code == 200, r.text
    pending = r.json()["pending"]
    assert len(pending) == 1
    item = pending[0]
    assert item["from"]["first_name"] == "Aarav"
    assert isinstance(item["score"], int)
    assert isinstance(item["breakdown"], dict)
    assert "match_id" in item
