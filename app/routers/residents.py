from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Form, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

# Import the matching engine and operational configuration
from app.engine.matching import recommend_hostels
from app.config import config

# We assume the existence of these modules based on standard FastAPI structural patterns.
from app.db import get_session
from app.models import User, ResidentProfile, Hostel, Room
from app.dependencies import get_current_resident

router = APIRouter(prefix="/api/residents", tags=["Residents"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/me")
def get_me(current_resident: ResidentProfile = Depends(get_current_resident)):
    """
    Fetches and returns the active resident's database profile data.
    Protected by the `get_current_resident` session middleware dependency.
    """
    return current_resident


@router.put("/profile", response_class=HTMLResponse)
def update_profile(
    current_resident: ResidentProfile = Depends(get_current_resident),
    session: Session = Depends(get_session),
    age: Optional[int] = Form(None),
    budget_min: Optional[float] = Form(None),
    budget_max: Optional[float] = Form(None),
    location: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    smoking: Optional[bool] = Form(None),
    drinking: Optional[bool] = Form(None),
    vegetarian: Optional[bool] = Form(None),
    sleep_schedule: Optional[str] = Form(None),
    cleanliness: Optional[int] = Form(None),
    social_profile: Optional[str] = Form(None),
    gaming_frequency: Optional[int] = Form(None),
    study_frequency: Optional[int] = Form(None),
    fitness_frequency: Optional[int] = Form(None),
    visitor_frequency: Optional[int] = Form(None),
):
    """
    Parses incoming web form data from the resident profile settings page.
    Updates the resident's fields in the database and saves the changes atomically.
    """
    try:
        if age is not None: current_resident.age = age
        if budget_min is not None: current_resident.budget_min = budget_min
        if budget_max is not None: current_resident.budget_max = budget_max
        if location is not None: current_resident.location = location
        if gender is not None: current_resident.gender = gender
        if smoking is not None: current_resident.smoking = smoking
        if drinking is not None: current_resident.drinking = drinking
        if vegetarian is not None: current_resident.vegetarian = vegetarian
        if sleep_schedule is not None: current_resident.sleep_schedule = sleep_schedule
        if cleanliness is not None: current_resident.cleanliness = cleanliness
        if social_profile is not None: current_resident.social_profile = social_profile
        if gaming_frequency is not None: current_resident.gaming_frequency = gaming_frequency
        if study_frequency is not None: current_resident.study_frequency = study_frequency
        if fitness_frequency is not None: current_resident.fitness_frequency = fitness_frequency
        if visitor_frequency is not None: current_resident.visitor_frequency = visitor_frequency

        session.add(current_resident)
        session.commit()
        session.refresh(current_resident)
        
        return HTMLResponse(content="<div class='success-alert'>Profile updated successfully.</div>")
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the profile."
        )


@router.get("/recommendations", response_class=HTMLResponse)
def get_recommendations(
    request: Request,
    current_resident: ResidentProfile = Depends(get_current_resident),
    session: Session = Depends(get_session)
):
    """
    Queries ALL available hostels and passes them to the matching engine, 
    returning the rendered HTML fragment containing the sorted recommendations.
    """
    hostels = session.exec(select(Hostel)).all()
    ranked_hostels = recommend_hostels(current_resident, hostels, config)
    
    return templates.TemplateResponse(
        "recommendations_dashboard.html",
        {
            "request": request, 
            "recommendations": ranked_hostels
        }
    )