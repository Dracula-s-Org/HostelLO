"""Asset access control (HLD §6.2): proxied room images + KYC document access.

Local files never serve via raw paths — these routes gate every read.
KYC documents are purged on decision, so reads usually return 410 GONE.
"""
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlmodel import Session

from app.db import get_session
from app.dependencies import get_current_owner, get_current_user
from app.models import Hostel, KycVerification, OwnerProfile, Room, User

router = APIRouter(prefix="/api/assets", tags=["Assets"])


@router.get("/rooms/{room_id}/{index}")
def room_image(
    room_id: uuid.UUID,
    index: int,
    owner: OwnerProfile = Depends(get_current_owner),
    session: Session = Depends(get_session),
):
    room = session.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    hostel = session.get(Hostel, room.hostel_id)
    if hostel.owner_id != owner.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your property")
    paths = room.image_paths or []
    if index < 0 or index >= len(paths):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such image")
    ref = paths[index]
    if ref.startswith("http"):
        return RedirectResponse(ref)
    local = ref.lstrip("/")
    if not os.path.isfile(local):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image missing from disk")
    return FileResponse(local)


@router.get("/kyc/{verification_id}")
def kyc_document(
    verification_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    record = session.get(KycVerification, verification_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verification not found")
    if record.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your document")
    if record.doc_ref == "[PURGED]":
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Document purged after decision (DPDP purpose-bound deletion).",
        )
    if not os.path.isfile(record.doc_ref):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document missing from disk")
    return FileResponse(record.doc_ref)
