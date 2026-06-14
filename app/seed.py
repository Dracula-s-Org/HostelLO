"""Idempotent demo seed (TDD §11): 1 owner, 2 hostels, 6 rooms, 5 residents
with varied habits, plus a ready-to-approve shared-room pair so the owner
review queue is populated on first load.

Run:  python -m app.seed
Safe to re-run — exits early if the seed owner already exists.
"""
from sqlmodel import Session, select

from app.db import engine, init_db
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
from app.services.matchmaking import score_pair

OWNER_PHONE = "9100000001"

RESIDENTS = [
    # (phone, name, gender, age, bmin, bmax, location, smoking, drinking, sleep,
    #  clean, diet, social, gaming, study, fitness, visitors, kyc)
    ("9000000001", "Aarav Sharma", "MALE", 21, 5000, 8000, "koramangala", False, False,
     "EARLY", 4, "VEG", "INTROVERT", 2, 4, 2, 1, KycStatus.VERIFIED),
    ("9000000002", "Vihaan Patel", "MALE", 22, 5500, 9000, "koramangala", False, False,
     "EARLY", 3, "VEG", "INTROVERT", 3, 4, 2, 2, KycStatus.VERIFIED),
    ("9000000003", "Kabir Singh", "MALE", 24, 8000, 14000, "indiranagar", True, True,
     "NIGHT", 2, "NONVEG", "EXTROVERT", 4, 1, 3, 4, KycStatus.VERIFIED),
    ("9000000004", "Ananya Iyer", "FEMALE", 20, 5000, 9000, "koramangala", False, False,
     "NIGHT", 5, "VEG", "EXTROVERT", 1, 3, 4, 2, KycStatus.VERIFIED),
    ("9000000005", "Diya Nair", "FEMALE", 23, 6000, 10000, "koramangala", False, True,
     "NIGHT", 4, "EGGETARIAN", "INTROVERT", 2, 3, 3, 3, KycStatus.NONE),
]


def seed() -> None:
    init_db()
    with Session(engine) as session:
        if session.exec(select(User).where(User.phone == OWNER_PHONE)).first():
            print("Seed data already present — nothing to do.")
            return

        # Owner
        owner_user = User(phone=OWNER_PHONE, role=UserRole.OWNER.value,
                          kyc_status=KycStatus.VERIFIED.value)
        session.add(owner_user)
        session.flush()
        owner = OwnerProfile(user_id=owner_user.id, name="Rajesh Kumar",
                             contact="rajesh@sunrisepg.in")
        session.add(owner)

        # Hostels
        sunrise = Hostel(
            owner_id=owner.user_id,
            name="Sunrise Residency",
            address="12, 5th Block, Koramangala, Bengaluru",
            location="koramangala",
            gender_policy="COED",
            listing_tier="FREE",
            verified=True,
            allow_smoking=False,
            allow_drinking=False,
            veg_only=False,
            min_age=18,
            max_age=30,
            amenities=["wifi", "laundry", "mess"],
        )
        elite = Hostel(
            owner_id=owner.user_id,
            name="Elite Stay PG",
            address="48, 100ft Road, Indiranagar, Bengaluru",
            location="indiranagar",
            gender_policy="MALE",
            listing_tier="PREMIUM",
            verified=True,
            allow_smoking=True,
            allow_drinking=True,
            veg_only=False,
            amenities=["wifi", "gym", "parking", "mess"],
        )
        session.add(sunrise)
        session.add(elite)
        session.flush()

        rooms = [
            Room(hostel_id=sunrise.id, type="SINGLE", capacity=1, price=8000),
            Room(hostel_id=sunrise.id, type="SHARED", capacity=2, price=6000),
            Room(hostel_id=sunrise.id, type="SHARED", capacity=2, price=6500),
            Room(hostel_id=elite.id, type="SINGLE", capacity=1, price=12000),
            Room(hostel_id=elite.id, type="SHARED", capacity=2, price=9000),
            Room(hostel_id=elite.id, type="SHARED", capacity=2, price=9500),
        ]
        session.add_all(rooms)
        session.flush()

        # Residents with varied habits
        profiles = {}
        for (phone, name, gender, age, bmin, bmax, loc, smoking, drinking, sleep,
             clean, diet, social, gaming, study, fitness, visitors, kyc) in RESIDENTS:
            user = User(phone=phone, role=UserRole.RESIDENT.value, kyc_status=kyc.value)
            session.add(user)
            session.flush()
            profile = ResidentProfile(
                user_id=user.id, name=name, gender=gender, age=age,
                budget_min=bmin, budget_max=bmax, preferred_location=loc,
                smoking=smoking, drinking=drinking, sleep_schedule=sleep,
                cleanliness=clean, diet=diet, social_type=social,
                gaming_freq=gaming, study_habits=study, fitness_freq=fitness,
                visitors_freq=visitors, seeking_shared=True,
                amenity_preferences=["wifi", "mess"],
            )
            session.add(profile)
            profiles[phone] = profile

        # Ready-to-approve shared pair: Aarav + Vihaan on Sunrise shared room.
        # Real engine score keeps the owner-side breakdown bars honest.
        aarav, vihaan = profiles["9000000001"], profiles["9000000002"]
        pair = score_pair(aarav, vihaan)
        match = RoommateMatch(
            room_id=rooms[1].id,
            resident_a=aarav.user_id,
            resident_b=vihaan.user_id,
            a_accepted=True,
            b_accepted=True,
            score=int(round(pair["overall_score"])) if pair else 0,
            breakdown=pair["breakdown"] if pair else {},
            status=MatchStatus.CONFIRMED.value,
        )
        session.add(match)
        session.flush()
        session.add_all([
            Booking(resident_id=aarav.user_id, room_id=rooms[1].id,
                    roommate_match_id=match.id, status=BookingStatus.REQUESTED.value),
            Booking(resident_id=vihaan.user_id, room_id=rooms[1].id,
                    roommate_match_id=match.id, status=BookingStatus.REQUESTED.value),
        ])

        session.commit()
        print("Seeded: 1 owner, 2 hostels, 6 rooms, 5 residents, 1 approvable shared pair.")
        print(f"Owner login: {OWNER_PHONE} / OTP 123456")
        print("Resident logins: 9000000001..9000000005 / OTP 123456")


if __name__ == "__main__":
    seed()
