"""Owner profile, hostel listings, and room configuration (HLD §4.3)."""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
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
from app.serializers import to_hostel_view, to_owner_self_view, to_room_view
from app.services.storage import save_room_image

router = APIRouter(prefix="/api/owners", tags=["Owners"])
# /api/hostels/{id}/rooms lives outside the /api/owners prefix (HLD §4.3)
hostel_rooms_router = APIRouter(prefix="/api/hostels", tags=["Owners"])


@router.get("/me")
def get_me(owner: OwnerProfile = Depends(get_current_owner)):
    return to_owner_self_view(owner)


@router.post("/profile")
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
    session.refresh(profile)
    return to_owner_self_view(profile)


@router.post("/hostels")
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
    return to_hostel_view(hostel)


@router.get("/hostels")
def list_hostels(
    owner: OwnerProfile = Depends(get_current_owner),
    session: Session = Depends(get_session),
):
    """Owner dashboard: owned properties with their room matrix and a
    pending-booking count per hostel, as JSON.
    """
    hostels = session.exec(select(Hostel).where(Hostel.owner_id == owner.user_id)).all()
    items = []
    for h in hostels:
        rooms = session.exec(select(Room).where(Room.hostel_id == h.id)).all()
        pending = session.exec(
            select(Booking)
            .where(Booking.status == BookingStatus.REQUESTED.value)
            .where(Booking.room_id.in_([r.id for r in rooms] or [uuid.uuid4()]))
        ).all()
        items.append(
            {
                "hostel": to_hostel_view(h),
                "rooms": [to_room_view(r) for r in rooms],
                "pending_count": len(pending),
            }
        )
    return {"hostels": items}


@router.put("/hostels/{hostel_id}")
def update_hostel(
    hostel_id: uuid.UUID,
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
    """Edit a hostel — mirrors the create endpoint's fields, same ownership +
    KYC-verified checks. Returns the updated hostel view.
    """
    hostel = session.get(Hostel, hostel_id)
    if not hostel or hostel.owner_id != owner.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hostel not found")
    if gender_policy not in [g.value for g in GenderPolicy]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid gender_policy")
    if listing_tier not in [t.value for t in ListingTier]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid listing_tier")

    hostel.name = name
    hostel.address = address
    hostel.location = location.strip().lower()
    hostel.gender_policy = gender_policy
    hostel.listing_tier = listing_tier
    hostel.allow_smoking = allow_smoking
    hostel.allow_drinking = allow_drinking
    hostel.veg_only = veg_only
    hostel.min_age = min_age
    hostel.max_age = max_age
    hostel.amenities = [a.strip().lower() for a in (amenities or "").split(",") if a.strip()]
    session.add(hostel)
    session.commit()
    session.refresh(hostel)
    return to_hostel_view(hostel)


@hostel_rooms_router.post("/{hostel_id}/rooms")
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
    return to_room_view(room)
