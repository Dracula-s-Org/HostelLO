"""Frozen data contract — HLD §3 (Final Release).

Enums are stored as plain strings matching the HLD CREATE TYPE values exactly.
Postgres TEXT[] / JSONB columns are mapped to JSON for SQLite<->Postgres parity.
"""
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List

from sqlalchemy import CheckConstraint, Column, JSON, Index, text
from sqlmodel import SQLModel, Field


# --- Frozen enumerated types (HLD §3 Listing 1) ---

class UserRole(str, Enum):
    OWNER = "OWNER"
    RESIDENT = "RESIDENT"


class KycStatus(str, Enum):
    NONE = "NONE"
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class GenderType(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"


class GenderPolicy(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    COED = "COED"


class SleepSchedule(str, Enum):
    EARLY = "EARLY"
    NIGHT = "NIGHT"


class DietType(str, Enum):
    VEG = "VEG"
    NONVEG = "NONVEG"
    EGGETARIAN = "EGGETARIAN"


class SocialType(str, Enum):
    INTROVERT = "INTROVERT"
    EXTROVERT = "EXTROVERT"


class ListingTier(str, Enum):
    FREE = "FREE"
    PREMIUM = "PREMIUM"


class RoomType(str, Enum):
    SINGLE = "SINGLE"
    SHARED = "SHARED"


class RoomStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    FULL = "FULL"


class BookingStatus(str, Enum):
    REQUESTED = "REQUESTED"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class MatchStatus(str, Enum):
    PROPOSED = "PROPOSED"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class DocType(str, Enum):
    """Accepted KYC identity documents (request-layer allowlist; the DB column
    stays free TEXT for forward-compat)."""
    AADHAAR = "AADHAAR"
    PAN = "PAN"
    PASSPORT = "PASSPORT"
    DRIVING_LICENSE = "DRIVING_LICENSE"
    VOTER_ID = "VOTER_ID"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --- Tables ---

class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    phone: str = Field(max_length=15, unique=True, index=True)
    role: str  # UserRole
    kyc_status: str = Field(default=KycStatus.NONE.value)  # global source of truth
    created_at: datetime = Field(default_factory=utcnow)


class OwnerProfile(SQLModel, table=True):
    __tablename__ = "owner_profiles"

    user_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True)
    name: str = Field(max_length=100)
    contact: str = Field(max_length=50)


class ResidentProfile(SQLModel, table=True):
    __tablename__ = "resident_profiles"

    user_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True)
    name: str = Field(max_length=100)
    gender: str  # GenderType
    age: int
    budget_min: float
    budget_max: float
    preferred_location: str = Field(max_length=150)
    smoking: bool = Field(default=False)
    drinking: bool = Field(default=False)
    sleep_schedule: str  # SleepSchedule
    cleanliness: int  # 1..5
    diet: str  # DietType
    social_type: str  # SocialType
    gaming_freq: int  # 1..4
    study_habits: int  # 1..4
    fitness_freq: int  # 1..4
    visitors_freq: int  # 1..4
    seeking_shared: bool = Field(default=True)
    prebooked_roommate_phone: Optional[str] = Field(default=None, max_length=15)
    amenity_preferences: List[str] = Field(default_factory=list, sa_column=Column(JSON))


class Hostel(SQLModel, table=True):
    __tablename__ = "hostels"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(foreign_key="owner_profiles.user_id", index=True)
    name: str = Field(max_length=150)
    address: str
    location: str = Field(max_length=100, index=True)
    gender_policy: str  # GenderPolicy
    listing_tier: str = Field(default=ListingTier.FREE.value)
    verified: bool = Field(default=False)
    allow_smoking: bool = Field(default=False)
    allow_drinking: bool = Field(default=False)
    veg_only: bool = Field(default=False)
    min_age: Optional[int] = Field(default=None)
    max_age: Optional[int] = Field(default=None)
    amenities: List[str] = Field(default_factory=list, sa_column=Column(JSON))


class Room(SQLModel, table=True):
    __tablename__ = "rooms"
    __table_args__ = (
        # Defense-in-depth backstop: occupancy can never exceed capacity or go
        # negative, even if application logic regresses (HLD §7.1).
        CheckConstraint(
            "occupied_count >= 0 AND occupied_count <= capacity",
            name="ck_room_occupancy_bounds",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hostel_id: uuid.UUID = Field(foreign_key="hostels.id", index=True)
    type: str  # RoomType
    capacity: int
    occupied_count: int = Field(default=0)
    price: float
    status: str = Field(default=RoomStatus.AVAILABLE.value)  # RoomStatus
    image_paths: List[str] = Field(default_factory=list, sa_column=Column(JSON))


class RoommateMatch(SQLModel, table=True):
    __tablename__ = "roommate_matches"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    room_id: uuid.UUID = Field(foreign_key="rooms.id", index=True)
    resident_a: uuid.UUID = Field(foreign_key="resident_profiles.user_id")
    resident_b: uuid.UUID = Field(foreign_key="resident_profiles.user_id")
    a_accepted: bool = Field(default=False)
    b_accepted: bool = Field(default=False)
    score: int
    breakdown: dict = Field(default_factory=dict, sa_column=Column(JSON))
    status: str = Field(default=MatchStatus.PROPOSED.value)  # MatchStatus
    created_at: datetime = Field(default_factory=utcnow)


class Booking(SQLModel, table=True):
    __tablename__ = "bookings"
    __table_args__ = (
        Index(
            "idx_unique_active_resident_booking",
            "resident_id",
            unique=True,
            postgresql_where=text("status IN ('REQUESTED', 'CONFIRMED')"),
            sqlite_where=text("status IN ('REQUESTED', 'CONFIRMED')"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    resident_id: uuid.UUID = Field(foreign_key="resident_profiles.user_id", index=True)
    room_id: uuid.UUID = Field(foreign_key="rooms.id", index=True)
    roommate_match_id: Optional[uuid.UUID] = Field(default=None, foreign_key="roommate_matches.id")
    status: str = Field(default=BookingStatus.REQUESTED.value)  # BookingStatus
    created_at: datetime = Field(default_factory=utcnow)


class KycVerification(SQLModel, table=True):
    __tablename__ = "kyc_verifications"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    doc_type: str = Field(max_length=50)
    doc_ref: str
    status: str = Field(default=KycStatus.PENDING.value)
    created_at: datetime = Field(default_factory=utcnow)
