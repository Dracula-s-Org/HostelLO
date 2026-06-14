"""Resident profile + hostel discovery (HLD §4.1/§4.2).

Engine calls go through app/services/engine_adapters.py — the engine is pure
and duck-typed, so ORM rows are adapted to its expected dict shape.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from app.config import config
from app.db import get_session
from app.dependencies import get_current_resident, require_role
from app.engine.matching import recommend_hostels
from app.models import Hostel, ResidentProfile, Room, User, UserRole
from app.services.engine_adapters import hostel_to_engine, resident_to_engine
from app.templating import templates

router = APIRouter(prefix="/api/residents", tags=["Residents"])


@router.get("/me")
def get_me(current_resident: ResidentProfile = Depends(get_current_resident)):
    """The resident's own profile — self-access, no DPDP redaction needed."""
    return current_resident.model_dump(mode="json")


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


@router.post("/profile", response_class=HTMLResponse)
def create_profile(
    user: User = Depends(require_role(UserRole.RESIDENT.value)),
    session: Session = Depends(get_session),
    name: str = Form(...),
    age: int = Form(...),
    gender: str = Form(...),
    budget_min: float = Form(...),
    budget_max: float = Form(...),
    preferred_location: str = Form(...),
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
    prebooked_roommate_phone: Optional[str] = Form(None),
    amenity_preferences: Optional[str] = Form(None),
):
    existing = session.get(ResidentProfile, user.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile already exists; use PUT /api/residents/profile.",
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
    session.add(profile)
    session.commit()
    return HTMLResponse(
        "<div class='rounded bg-green-50 text-green-800 p-3'>Profile saved. "
        "Head to <b>Recommendations</b> to find your hostel.</div>"
    )


@router.put("/profile", response_class=HTMLResponse)
def update_profile(
    current_resident: ResidentProfile = Depends(get_current_resident),
    session: Session = Depends(get_session),
    name: Optional[str] = Form(None),
    age: Optional[int] = Form(None),
    gender: Optional[str] = Form(None),
    budget_min: Optional[float] = Form(None),
    budget_max: Optional[float] = Form(None),
    preferred_location: Optional[str] = Form(None),
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
    prebooked_roommate_phone: Optional[str] = Form(None),
    amenity_preferences: Optional[str] = Form(None),
):
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
    session.add(current_resident)
    session.commit()
    return HTMLResponse("<div class='rounded bg-green-50 text-green-800 p-3'>Profile updated.</div>")


@router.get("/recommendations", response_class=HTMLResponse)
def get_recommendations(
    request: Request,
    current_resident: ResidentProfile = Depends(get_current_resident),
    session: Session = Depends(get_session),
):
    """Ranked, hard-filtered hostels rendered as an HTMX fragment."""
    hostels = session.exec(select(Hostel)).all()
    rooms_by_hostel: dict = {}
    for room in session.exec(select(Room)).all():
        rooms_by_hostel.setdefault(room.hostel_id, []).append(room)

    engine_input = [hostel_to_engine(h, rooms_by_hostel.get(h.id, [])) for h in hostels]
    ranked = recommend_hostels(resident_to_engine(current_resident), engine_input, config)

    hostels_by_id = {str(h.id): h for h in hostels}
    cards = []
    for r in ranked:
        hostel = hostels_by_id.get(r["hostel_id"])
        if not hostel:
            continue
        cards.append(
            {
                "hostel": hostel,
                "rooms": rooms_by_hostel.get(hostel.id, []),
                "score": r["final_score"],
                "price_fit": r["price_fit"],
                "location_fit": r["location_fit"],
                "amenity_fit": r["amenity_fit"],
            }
        )

    return templates.TemplateResponse(
        request,
        "resident/recommendations.html",
        {"cards": cards},
    )
