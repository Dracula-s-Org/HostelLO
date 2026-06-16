"""Resident-facing hostel reads (HLD §4.2): hostel detail + room listing.

These back the `hostel_details` and `room_selection` screens. Authenticated as
a resident; data flows through the shared serializers (image_count, never raw
paths).
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.db import get_session
from app.dependencies import get_current_resident
from app.models import Hostel, ResidentProfile, Room
from app.serializers import to_hostel_view, to_room_view

router = APIRouter(prefix="/api/hostels", tags=["Hostels"])


@router.get("/{hostel_id}")
def hostel_detail(
    hostel_id: uuid.UUID,
    _: ResidentProfile = Depends(get_current_resident),
    session: Session = Depends(get_session),
):
    """A single hostel by id for the hostel detail screen. 404 if not found."""
    hostel = session.get(Hostel, hostel_id)
    if not hostel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hostel not found")
    return to_hostel_view(hostel)


@router.get("/{hostel_id}/rooms")
def hostel_rooms(
    hostel_id: uuid.UUID,
    _: ResidentProfile = Depends(get_current_resident),
    session: Session = Depends(get_session),
):
    """Rooms for a hostel (room_selection screen). 404 if the hostel is unknown."""
    hostel = session.get(Hostel, hostel_id)
    if not hostel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hostel not found")
    rooms = session.exec(select(Room).where(Room.hostel_id == hostel_id)).all()
    return {"rooms": [to_room_view(r) for r in rooms]}
