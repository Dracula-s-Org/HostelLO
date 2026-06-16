"""Direct-DB scenario builders for service-level tests."""
from sqlmodel import Session

from app.models import (
    Booking,
    BookingStatus,
    Hostel,
    KycStatus,
    MatchStatus,
    OwnerProfile,
    ResidentProfile,
    Room,
    RoommateMatch,
    User,
    UserRole,
)

_counter = {"n": 0}


def _phone() -> str:
    _counter["n"] += 1
    return f"99999{_counter['n']:05d}"


def make_owner(session: Session) -> OwnerProfile:
    user = User(phone=_phone(), role=UserRole.OWNER.value, kyc_status=KycStatus.VERIFIED.value)
    session.add(user)
    session.flush()
    owner = OwnerProfile(user_id=user.id, name="Owner One", contact="o@x.in")
    session.add(owner)
    session.flush()
    return owner


def make_hostel(session: Session, owner: OwnerProfile, **kw) -> Hostel:
    defaults = dict(
        owner_id=owner.user_id,
        name="Test Hostel",
        address="1 Test St",
        location="koramangala",
        gender_policy="COED",
        listing_tier="FREE",
        verified=True,
        allow_smoking=False,
        allow_drinking=False,
        veg_only=False,
        amenities=["wifi"],
    )
    defaults.update(kw)
    hostel = Hostel(**defaults)
    session.add(hostel)
    session.flush()
    return hostel


def make_room(session: Session, hostel: Hostel, **kw) -> Room:
    defaults = dict(hostel_id=hostel.id, type="SHARED", capacity=2, price=6000.0)
    defaults.update(kw)
    room = Room(**defaults)
    session.add(room)
    session.flush()
    return room


def make_resident(session: Session, *, kyc=KycStatus.VERIFIED, **kw) -> tuple[User, ResidentProfile]:
    user = User(phone=kw.pop("phone", _phone()), role=UserRole.RESIDENT.value, kyc_status=kyc.value)
    session.add(user)
    session.flush()
    defaults = dict(
        user_id=user.id,
        name="Res Ident",
        gender="MALE",
        age=22,
        budget_min=5000.0,
        budget_max=9000.0,
        preferred_location="koramangala",
        smoking=False,
        drinking=False,
        sleep_schedule="EARLY",
        cleanliness=4,
        diet="VEG",
        social_type="INTROVERT",
        gaming_freq=2,
        study_habits=4,
        fitness_freq=2,
        visitors_freq=1,
        seeking_shared=True,
        amenity_preferences=["wifi"],
    )
    defaults.update(kw)
    profile = ResidentProfile(**defaults)
    session.add(profile)
    session.flush()
    return user, profile


def make_pair_on_room(session: Session, room: Room, profile_a, profile_b,
                      match_status=MatchStatus.CONFIRMED) -> tuple[RoommateMatch, Booking, Booking]:
    match = RoommateMatch(
        room_id=room.id,
        resident_a=profile_a.user_id,
        resident_b=profile_b.user_id,
        a_accepted=True,
        b_accepted=match_status == MatchStatus.CONFIRMED,
        score=80,
        breakdown={"social": 1.0, "gaming": 1.0, "study": 1.0, "fitness": 0.5, "visitors": 0.5},
        status=match_status.value,
    )
    session.add(match)
    session.flush()
    booking_a = Booking(resident_id=profile_a.user_id, room_id=room.id,
                        roommate_match_id=match.id, status=BookingStatus.REQUESTED.value)
    booking_b = Booking(resident_id=profile_b.user_id, room_id=room.id,
                        roommate_match_id=match.id, status=BookingStatus.REQUESTED.value)
    session.add_all([booking_a, booking_b])
    session.flush()
    return match, booking_a, booking_b
