"""Shared DPDP data-gating serializers (HLD §6.1).

Every resident-profile exposure flows through these views — no hand-rolled
field stripping anywhere else. The schema keeps a single `name`; "first name"
is its first token.
"""
from app.models import ResidentProfile, User


def _first_name(profile: ResidentProfile) -> str:
    return (profile.name or "").split()[0] if profile.name else ""


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
