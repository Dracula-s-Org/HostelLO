"""Resident profile + hostel discovery (HLD §4.1/§4.2).

Engine calls go through app/services/engine_adapters.py — the engine is pure
and duck-typed, so ORM rows are adapted to its expected dict shape.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, status
from sqlmodel import Session, select

from app.config import config
from app.db import get_session
from app.dependencies import get_current_resident, require_role
from app.engine.matching import recommend_hostels
from app.models import (
    DietType,
    GenderType,
    Hostel,
    ResidentProfile,
    Room,
    SleepSchedule,
    SocialType,
    User,
    UserRole,
)
from app.serializers import to_recommendation_view, to_resident_self_view
from app.services.engine_adapters import hostel_to_engine, resident_to_engine
from app.validators import validate_enum, validate_phone

router = APIRouter(prefix="/api/residents", tags=["Residents"])


def _validate_profile_enums(
    *,
    gender: Optional[str],
    sleep_schedule: Optional[str],
    diet: Optional[str],
    social_type: Optional[str],
    prebooked_roommate_phone: Optional[str],
) -> None:
    """Allowlist the free-`str` domain fields (the DB columns don't constrain
    them) — only the values actually present are checked, so PUT can patch a
    single field. Mirrors owners.py's gender_policy/listing_tier checks."""
    if gender is not None:
        validate_enum(gender, GenderType, "gender")
    if sleep_schedule is not None:
        validate_enum(sleep_schedule, SleepSchedule, "sleep_schedule")
    if diet is not None:
        validate_enum(diet, DietType, "diet")
    if social_type is not None:
        validate_enum(social_type, SocialType, "social_type")
    if prebooked_roommate_phone and prebooked_roommate_phone.strip():
        validate_phone(prebooked_roommate_phone.strip(), "roommate phone")


def _assert_budget_order(profile: ResidentProfile) -> None:
    if profile.budget_min > profile.budget_max:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="budget_min cannot exceed budget_max",
        )


@router.get("/me")
def get_me(current_resident: ResidentProfile = Depends(get_current_resident)):
    """The resident's own profile via an explicit allowlist (no raw model dump —
    a pre-booked roommate's phone is third-party PII and is never echoed in full).
    """
    return to_resident_self_view(current_resident)


def _apply_profile_fields(
    profile: ResidentProfile,
    *,
    name: Optional[str],
    age: Optional[int],
    gender: Optional[str],
    budget_min: Optional[float],
    budget_max: Optional[float],
    preferred_location: Optional[str],
    smoking: Optional[bool],
    drinking: Optional[bool],
    sleep_schedule: Optional[str],
    cleanliness: Optional[int],
    diet: Optional[str],
    social_type: Optional[str],
    gaming_freq: Optional[int],
    study_habits: Optional[int],
    fitness_freq: Optional[int],
    visitors_freq: Optional[int],
    seeking_shared: Optional[bool],
    prebooked_roommate_phone: Optional[str],
    amenity_preferences: Optional[str],
) -> None:
    if name is not None:
        profile.name = name
    if age is not None:
        profile.age = age
    if gender is not None:
        profile.gender = gender
    if budget_min is not None:
        profile.budget_min = budget_min
    if budget_max is not None:
        profile.budget_max = budget_max
    if preferred_location is not None:
        profile.preferred_location = preferred_location
    if smoking is not None:
        profile.smoking = smoking
    if drinking is not None:
        profile.drinking = drinking
    if sleep_schedule is not None:
        profile.sleep_schedule = sleep_schedule
    if cleanliness is not None:
        profile.cleanliness = cleanliness
    if diet is not None:
        profile.diet = diet
    if social_type is not None:
        profile.social_type = social_type
    if gaming_freq is not None:
        profile.gaming_freq = gaming_freq
    if study_habits is not None:
        profile.study_habits = study_habits
    if fitness_freq is not None:
        profile.fitness_freq = fitness_freq
    if visitors_freq is not None:
        profile.visitors_freq = visitors_freq
    if seeking_shared is not None:
        profile.seeking_shared = seeking_shared
    if prebooked_roommate_phone is not None:
        profile.prebooked_roommate_phone = prebooked_roommate_phone.strip() or None
    if amenity_preferences is not None:
        profile.amenity_preferences = [
            a.strip().lower() for a in amenity_preferences.split(",") if a.strip()
        ]


@router.post("/profile")
def create_profile(
    user: User = Depends(require_role(UserRole.RESIDENT.value)),
    session: Session = Depends(get_session),
    name: str = Form(..., max_length=100),
    age: int = Form(..., ge=16, le=120),
    gender: str = Form(...),
    budget_min: float = Form(..., ge=0),
    budget_max: float = Form(..., ge=0),
    preferred_location: str = Form(..., max_length=150),
    sleep_schedule: str = Form(...),
    cleanliness: int = Form(..., ge=1, le=5),
    diet: str = Form(...),
    social_type: str = Form(...),
    gaming_freq: int = Form(..., ge=1, le=4),
    study_habits: int = Form(..., ge=1, le=4),
    fitness_freq: int = Form(..., ge=1, le=4),
    visitors_freq: int = Form(..., ge=1, le=4),
    smoking: bool = Form(False),
    drinking: bool = Form(False),
    seeking_shared: bool = Form(True),
    prebooked_roommate_phone: Optional[str] = Form(None, max_length=15),
    amenity_preferences: Optional[str] = Form(None),
):
    existing = session.get(ResidentProfile, user.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile already exists; use PUT /api/residents/profile.",
        )
    _validate_profile_enums(
        gender=gender,
        sleep_schedule=sleep_schedule,
        diet=diet,
        social_type=social_type,
        prebooked_roommate_phone=prebooked_roommate_phone,
    )
    profile = ResidentProfile(
        user_id=user.id,
        name=name,
        age=age,
        gender=gender,
        budget_min=budget_min,
        budget_max=budget_max,
        preferred_location=preferred_location.strip().lower(),
        smoking=smoking,
        drinking=drinking,
        sleep_schedule=sleep_schedule,
        cleanliness=cleanliness,
        diet=diet,
        social_type=social_type,
        gaming_freq=gaming_freq,
        study_habits=study_habits,
        fitness_freq=fitness_freq,
        visitors_freq=visitors_freq,
        seeking_shared=seeking_shared,
        prebooked_roommate_phone=(prebooked_roommate_phone or "").strip() or None,
        amenity_preferences=[
            a.strip().lower() for a in (amenity_preferences or "").split(",") if a.strip()
        ],
    )
    _assert_budget_order(profile)
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return to_resident_self_view(profile)


@router.put("/profile")
def update_profile(
    current_resident: ResidentProfile = Depends(get_current_resident),
    session: Session = Depends(get_session),
    name: Optional[str] = Form(None, max_length=100),
    age: Optional[int] = Form(None, ge=16, le=120),
    gender: Optional[str] = Form(None),
    budget_min: Optional[float] = Form(None, ge=0),
    budget_max: Optional[float] = Form(None, ge=0),
    preferred_location: Optional[str] = Form(None, max_length=150),
    smoking: Optional[bool] = Form(None),
    drinking: Optional[bool] = Form(None),
    sleep_schedule: Optional[str] = Form(None),
    cleanliness: Optional[int] = Form(None, ge=1, le=5),
    diet: Optional[str] = Form(None),
    social_type: Optional[str] = Form(None),
    gaming_freq: Optional[int] = Form(None, ge=1, le=4),
    study_habits: Optional[int] = Form(None, ge=1, le=4),
    fitness_freq: Optional[int] = Form(None, ge=1, le=4),
    visitors_freq: Optional[int] = Form(None, ge=1, le=4),
    seeking_shared: Optional[bool] = Form(None),
    prebooked_roommate_phone: Optional[str] = Form(None, max_length=15),
    amenity_preferences: Optional[str] = Form(None),
):
    _validate_profile_enums(
        gender=gender,
        sleep_schedule=sleep_schedule,
        diet=diet,
        social_type=social_type,
        prebooked_roommate_phone=prebooked_roommate_phone,
    )
    _apply_profile_fields(
        current_resident,
        name=name,
        age=age,
        gender=gender,
        budget_min=budget_min,
        budget_max=budget_max,
        preferred_location=preferred_location.strip().lower() if preferred_location else None,
        smoking=smoking,
        drinking=drinking,
        sleep_schedule=sleep_schedule,
        cleanliness=cleanliness,
        diet=diet,
        social_type=social_type,
        gaming_freq=gaming_freq,
        study_habits=study_habits,
        fitness_freq=fitness_freq,
        visitors_freq=visitors_freq,
        seeking_shared=seeking_shared,
        prebooked_roommate_phone=prebooked_roommate_phone,
        amenity_preferences=amenity_preferences,
    )
    _assert_budget_order(current_resident)
    session.add(current_resident)
    session.commit()
    session.refresh(current_resident)
    return to_resident_self_view(current_resident)


@router.get("/recommendations")
def get_recommendations(
    current_resident: ResidentProfile = Depends(get_current_resident),
    session: Session = Depends(get_session),
):
    """Ranked, hard-filtered hostels as JSON for the recommendations screen."""
    hostels = session.exec(select(Hostel)).all()
    rooms_by_hostel: dict = {}
    for room in session.exec(select(Room)).all():
        rooms_by_hostel.setdefault(room.hostel_id, []).append(room)

    engine_input = [hostel_to_engine(h, rooms_by_hostel.get(h.id, [])) for h in hostels]
    ranked = recommend_hostels(resident_to_engine(current_resident), engine_input, config)

    hostels_by_id = {str(h.id): h for h in hostels}
    results = []
    for r in ranked:
        hostel = hostels_by_id.get(r["hostel_id"])
        if not hostel:
            continue
        results.append(
            to_recommendation_view(
                hostel,
                rooms_by_hostel.get(hostel.id, []),
                r["final_score"],
                r["price_fit"],
                r["location_fit"],
                r["amenity_fit"],
            )
        )

    return {"results": results}
