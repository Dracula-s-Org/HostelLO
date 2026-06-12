"""Full-page routes (Jinja2). Action endpoints elsewhere return HTMX fragments."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session

from app.db import get_session
from app.dependencies import get_optional_user
from app.models import OwnerProfile, ResidentProfile, UserRole
from app.templating import templates

router = APIRouter(tags=["Pages"])


@router.get("/", response_class=HTMLResponse)
def login_page(request: Request, user=Depends(get_optional_user)):
    if user:
        return RedirectResponse("/owner" if user.role == UserRole.OWNER.value else "/resident")
    return templates.TemplateResponse(request, "auth/login.html", {})


@router.get("/resident", response_class=HTMLResponse)
def resident_dashboard(
    request: Request,
    user=Depends(get_optional_user),
    session: Session = Depends(get_session),
):
    if not user or user.role != UserRole.RESIDENT.value:
        return RedirectResponse("/")
    profile = session.get(ResidentProfile, user.id)
    return templates.TemplateResponse(
        request,
        "resident/dashboard.html",
        {"user": user, "profile": profile},
    )


@router.get("/owner", response_class=HTMLResponse)
def owner_dashboard(
    request: Request,
    user=Depends(get_optional_user),
    session: Session = Depends(get_session),
):
    if not user or user.role != UserRole.OWNER.value:
        return RedirectResponse("/")
    profile = session.get(OwnerProfile, user.id)
    return templates.TemplateResponse(
        request,
        "owner/dashboard.html",
        {"user": user, "profile": profile},
    )
