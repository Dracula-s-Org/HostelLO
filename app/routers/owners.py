"""Owner profile, hostel listings, and room configuration (HLD §4.3)."""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse
from markupsafe import escape
from sqlmodel import Session, select

from app.db import get_session
from app.dependencies import get_current_owner, require_kyc_verified, require_role
from app.models import (
    Booking,
    BookingStatus,
    GenderPolicy,
    Hostel,
    ListingTier,
    OwnerProfile,
    Room,
    RoomType,
    User,
    UserRole,
)
from app.serializers import to_owner_self_view
from app.services.storage import save_room_image
from app.templating import templates

router = APIRouter(prefix="/api/owners", tags=["Owners"])
# /api/hostels/{id}/rooms lives outside the /api/owners prefix (HLD §4.3)
hostel_rooms_router = APIRouter(prefix="/api/hostels", tags=["Owners"])


@router.get("/me")
def get_me(owner: OwnerProfile = Depends(get_current_owner)):
    return to_owner_self_view(owner)


@router.post("/profile", response_class=HTMLResponse)
def upsert_profile(
    user: User = Depends(require_role(UserRole.OWNER.value)),
    session: Session = Depends(get_session),
    name: str = Form(...),
    contact: str = Form(...),
):
    profile = session.get(OwnerProfile, user.id)
    if profile:
        profile.name = name
        profile.contact = contact
    else:
        profile = OwnerProfile(user_id=user.id, name=name, contact=contact)
    session.add(profile)
    session.commit()
    return HTMLResponse(
        "<div class='rounded bg-green-50 text-green-800 p-3'>Owner profile saved.</div>"
    )


@router.post("/hostels", response_class=HTMLResponse)
def create_hostel(
    user: User = Depends(require_kyc_verified),
    owner: OwnerProfile = Depends(get_current_owner),
    session: Session = Depends(get_session),
    name: str = Form(...),
    address: str = Form(...),
    location: str = Form(...),
    gender_policy: str = Form(...),
    listing_tier: str = Form(ListingTier.FREE.value),
    allow_smoking: bool = Form(False),
    allow_drinking: bool = Form(False),
    veg_only: bool = Form(False),
    min_age: Optional[int] = Form(None),
    max_age: Optional[int] = Form(None),
    amenities: Optional[str] = Form(None),
):
    if gender_policy not in [g.value for g in GenderPolicy]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid gender_policy")
    if listing_tier not in [t.value for t in ListingTier]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid listing_tier")
    hostel = Hostel(
        owner_id=owner.user_id,
        name=name,
        address=address,
        location=location.strip().lower(),
        gender_policy=gender_policy,
        listing_tier=listing_tier,
        allow_smoking=allow_smoking,
        allow_drinking=allow_drinking,
        veg_only=veg_only,
        min_age=min_age,
        max_age=max_age,
        amenities=[a.strip().lower() for a in (amenities or "").split(",") if a.strip()],
    )
    session.add(hostel)
    session.commit()
    session.refresh(hostel)
    return HTMLResponse(
        f"<div class='rounded bg-green-50 text-green-800 p-3'>Hostel <b>{escape(hostel.name)}</b> listed. "
        "Add rooms from the dashboard.</div>"
    )


@router.get("/hostels", response_class=HTMLResponse)
def list_hostels(
    request: Request,
    owner: OwnerProfile = Depends(get_current_owner),
    session: Session = Depends(get_session),
):
    """Dashboard matrix of owned properties (HTMX fragment)."""
    hostels = session.exec(select(Hostel).where(Hostel.owner_id == owner.user_id)).all()
    matrix = []
    for h in hostels:
        rooms = session.exec(select(Room).where(Room.hostel_id == h.id)).all()
        pending = session.exec(
            select(Booking)
            .where(Booking.status == BookingStatus.REQUESTED.value)
            .where(Booking.room_id.in_([r.id for r in rooms] or [uuid.uuid4()]))
        ).all()
        matrix.append({"hostel": h, "rooms": rooms, "pending_count": len(pending)})
    return templates.TemplateResponse(request, "owner/hostels.html", {"matrix": matrix})


@hostel_rooms_router.post("/{hostel_id}/rooms", response_class=HTMLResponse)
async def create_room(
    hostel_id: uuid.UUID,
    user: User = Depends(require_kyc_verified),
    owner: OwnerProfile = Depends(get_current_owner),
    session: Session = Depends(get_session),
    type: str = Form(...),
    capacity: int = Form(..., ge=1),
    price: float = Form(..., gt=0),
    images: List[UploadFile] = File(default=[]),
):
    hostel = session.get(Hostel, hostel_id)
    if not hostel or hostel.owner_id != owner.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hostel not found")
    if type not in [t.value for t in RoomType]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid room type")

    image_paths = []
    for img in images:
        if img and img.filename:
            image_paths.append(await save_room_image(img))

    room = Room(
        hostel_id=hostel.id,
        type=type,
        capacity=capacity,
        price=price,
        image_paths=image_paths,
    )
    session.add(room)
    session.commit()
    session.refresh(room)
    return HTMLResponse(
        f"<div class='rounded bg-green-50 text-green-800 p-3'>{escape(room.type)} room added to "
        f"<b>{escape(hostel.name)}</b> at ₹{room.price:.0f} ({len(image_paths)} image(s)).</div>"
    )
