"""Shared DPDP data-gating serializers (HLD §6.1).

Every resident-profile exposure flows through these views — no hand-rolled
field stripping anywhere else. The schema keeps a single `name`; "first name"
is its first token.
"""
from app.models import OwnerProfile, ResidentProfile, User


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
