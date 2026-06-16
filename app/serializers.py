"""Shared DPDP data-gating serializers (HLD §6.1).

Every resident-profile exposure flows through these views — no hand-rolled
field stripping anywhere else. The schema keeps a single `name`; "first name"
is its first token.
"""
from app.models import Hostel, OwnerProfile, ResidentProfile, Room, User


def _first_name(profile: ResidentProfile) -> str:
    return (profile.name or "").split()[0] if profile.name else ""


def _mask_phone(phone: str) -> str:
    if not phone:
        return ""
    return phone[:3] + "****" + phone[-2:] if len(phone) >= 5 else "****"


def to_resident_self_view(profile: ResidentProfile) -> dict:
    """The resident's OWN profile (GET /api/residents/me). Explicit allowlist so no
    column is auto-exposed. A pre-booked roommate's phone is third-party PII, so it
    is surfaced only as a masked hint, never echoed in full.
    """
    return {
        "user_id": str(profile.user_id),
        "name": profile.name,
        "age": profile.age,
        "gender": profile.gender,
        "budget_min": profile.budget_min,
        "budget_max": profile.budget_max,
        "preferred_location": profile.preferred_location,
        "smoking": profile.smoking,
        "drinking": profile.drinking,
        "sleep_schedule": profile.sleep_schedule,
        "cleanliness": profile.cleanliness,
        "diet": profile.diet,
        "social_type": profile.social_type,
        "gaming_freq": profile.gaming_freq,
        "study_habits": profile.study_habits,
        "fitness_freq": profile.fitness_freq,
        "visitors_freq": profile.visitors_freq,
        "seeking_shared": profile.seeking_shared,
        "amenity_preferences": profile.amenity_preferences,
        "has_prebooked_roommate": bool(profile.prebooked_roommate_phone),
        "prebooked_roommate_phone_masked": _mask_phone(profile.prebooked_roommate_phone or ""),
    }


def to_owner_self_view(profile: OwnerProfile) -> dict:
    """The owner's OWN profile (GET /api/owners/me) — explicit allowlist."""
    return {
        "user_id": str(profile.user_id),
        "name": profile.name,
        "contact": profile.contact,
    }


def to_owner_contact_view(owner: OwnerProfile) -> dict:
    """Owner name + contact, revealed ONLY to a resident holding a CONFIRMED
    booking in this owner's hostel (booking detail, B3). PII — the caller MUST
    gate on booking status before invoking this.
    """
    return {
        "name": owner.name,
        "contact": owner.contact,
    }


def to_hostel_view(hostel: Hostel) -> dict:
    """Public hostel shape shared by recommendations (A1), hostel detail (B1),
    and the owner dashboard (A5). No PII — address/amenities are listing data.
    """
    return {
        "id": str(hostel.id),
        "name": hostel.name,
        "address": hostel.address,
        "location": hostel.location,
        "gender_policy": hostel.gender_policy,
        "listing_tier": hostel.listing_tier,
        "verified": hostel.verified,
        "amenities": hostel.amenities or [],
        "veg_only": hostel.veg_only,
        "allow_smoking": hostel.allow_smoking,
        "allow_drinking": hostel.allow_drinking,
        "min_age": hostel.min_age,
        "max_age": hostel.max_age,
    }


def to_room_view(room: Room) -> dict:
    """Room shape shared by A1/A5/B2. Exposes `image_count`, never raw paths —
    images are pulled through the gated GET /api/assets/rooms/{room_id}/{index}.
    """
    return {
        "id": str(room.id),
        "type": room.type,
        "capacity": room.capacity,
        "occupied_count": room.occupied_count,
        "price": room.price,
        "status": room.status,
        "image_count": len(room.image_paths or []),
    }


def to_recommendation_view(
    hostel: Hostel,
    rooms: list,
    score: float,
    price_fit: float,
    location_fit: float,
    amenity_fit: float,
) -> dict:
    """One ranked recommendation card (A1): hostel + its rooms + fit vectors."""
    return {
        "hostel": to_hostel_view(hostel),
        "rooms": [to_room_view(r) for r in rooms],
        "score": round(score, 1),
        "price_fit": price_fit,
        "location_fit": location_fit,
        "amenity_fit": amenity_fit,
    }


def to_candidate_view(profile: ResidentProfile, score: float, breakdown: dict) -> dict:
    """Discovery / pool selection: first name + score + habit breakdown.

    Hidden: last name, phone, KYC references.
    """
    return {
        "candidate_id": str(profile.user_id),
        "first_name": _first_name(profile),
        "overall_score": round(score, 1),
        "breakdown": breakdown,
        "habits": {
            "sleep_schedule": profile.sleep_schedule,
            "cleanliness": profile.cleanliness,
            "social_type": profile.social_type,
        },
    }


def to_match_confirmed_view(profile: ResidentProfile, user: User) -> dict:
    """Match confirmation (CONFIRMED): full name + verified mobile for move-in
    coordination. Hidden: government identity-document references.
    """
    return {
        "resident_id": str(profile.user_id),
        "full_name": profile.name,
        "phone": user.phone,
        "kyc_status": user.kyc_status,
    }


def to_owner_applicant_view(profile: ResidentProfile) -> dict:
    """Owner pre-approval evaluation: first name + sub-score fit vectors
    (age, habits). Hidden: full name, contact details, identity subledger.
    """
    return {
        "resident_id": str(profile.user_id),
        "first_name": _first_name(profile),
        "age": profile.age,
        "habits": {
            "smoking": profile.smoking,
            "drinking": profile.drinking,
            "diet": profile.diet,
            "sleep_schedule": profile.sleep_schedule,
            "cleanliness": profile.cleanliness,
            "social_type": profile.social_type,
            "gaming_freq": profile.gaming_freq,
            "study_habits": profile.study_habits,
            "fitness_freq": profile.fitness_freq,
            "visitors_freq": profile.visitors_freq,
        },
    }


def to_owner_confirmed_view(profile: ResidentProfile, user: User) -> dict:
    """Owner booking approval (CONFIRMED): full identity profile, first & last
    name, verified mobile. Hidden: government identity-document references.
    """
    return {
        "resident_id": str(profile.user_id),
        "full_name": profile.name,
        "phone": user.phone,
        "age": profile.age,
        "gender": profile.gender,
        "kyc_status": user.kyc_status,
    }
