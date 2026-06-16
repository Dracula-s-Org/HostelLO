"""Adapters: ORM models -> the duck-typed dicts Dev A's pure engine consumes.

The engine (app/engine/matching.py) keys off names like `smoking_allowed`,
`age_min`, `vegetarian`, `tier`, `gender_policy == 'any'` — these map the
frozen HLD schema (allow_smoking, min_age, diet, listing_tier, COED) onto
that shape so the hard gates evaluate per HLD §2.1/§2.2 semantics.
"""
from typing import Iterable

from app.models import DietType, GenderPolicy, Hostel, ResidentProfile, Room


def resident_to_engine(profile: ResidentProfile) -> dict:
    return {
        "id": str(profile.user_id),
        "gender": profile.gender,
        "smoking": profile.smoking,
        "drinking": profile.drinking,
        "vegetarian": profile.diet == DietType.VEG.value,
        "age": profile.age,
        "budget_min": float(profile.budget_min),
        "budget_max": float(profile.budget_max),
        "location": profile.preferred_location,
        "amenities": list(profile.amenity_preferences or []),
        "sleep_schedule": profile.sleep_schedule,
        "cleanliness": profile.cleanliness,
        "social_profile": profile.social_type,
        "gaming_frequency": profile.gaming_freq,
        "study_frequency": profile.study_habits,
        "fitness_frequency": profile.fitness_freq,
        "visitor_frequency": profile.visitors_freq,
    }


def hostel_to_engine(hostel: Hostel, rooms: Iterable[Room]) -> dict:
    return {
        "id": str(hostel.id),
        # Engine treats 'any' as the open policy; HLD freezes COED for that
        "gender_policy": "any" if hostel.gender_policy == GenderPolicy.COED.value else hostel.gender_policy,
        "smoking_allowed": hostel.allow_smoking,
        "drinking_allowed": hostel.allow_drinking,
        "veg_only": hostel.veg_only,
        "age_min": hostel.min_age if hostel.min_age is not None else 0,
        "age_max": hostel.max_age if hostel.max_age is not None else 200,
        "location": hostel.location,
        "amenities": list(hostel.amenities or []),
        "tier": hostel.listing_tier,
        "verified": hostel.verified,
        "rooms": [{"id": str(r.id), "price": float(r.price)} for r in rooms],
    }
