"""Mock KYC submission + status (HLD §4.1, §6.2).

DPDP purpose-bound deletion: on decision both tables update atomically and the
raw document is purged (doc_ref -> '[PURGED]', file deleted from disk).
"""
import os
import uuid

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from app.db import get_session
from app.dependencies import get_current_user
from app.models import KycStatus, KycVerification, User
from app.services.kyc import kyc_provider
from app.services.uploads import KYC_DIR, read_capped, sniff_document_ext

router = APIRouter(prefix="/api/kyc", tags=["KYC"])


def apply_kyc_decision(session: Session, user: User, record: KycVerification, decision: str) -> None:
    """Authoritative write-back (HLD Listings 5/6): both tables + purge, one commit."""
    file_path = record.doc_ref
    user.kyc_status = decision
    record.status = decision
    record.doc_ref = "[PURGED]"
    session.add(user)
    session.add(record)
    session.commit()
    if file_path and file_path != "[PURGED]" and os.path.isfile(file_path):
        os.remove(file_path)


@router.post("/submit", response_class=HTMLResponse)
async def submit_kyc(
    request: Request,
    doc_type: str = Form(...),
    document: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    data = await read_capped(document)
    ext = sniff_document_ext(data)  # raises 400 if not a real PDF/image
    os.makedirs(KYC_DIR, exist_ok=True)
    # Filename is fully server-generated — the client filename is never trusted.
    safe_name = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(KYC_DIR, safe_name)
    with open(path, "wb") as fh:
        fh.write(data)

    record = KycVerification(user_id=user.id, doc_type=doc_type, doc_ref=path)
    user.kyc_status = KycStatus.PENDING.value
    session.add(record)
    session.add(user)
    session.commit()
    session.refresh(record)

    decision = kyc_provider.verify(doc_type, path)
    if decision in (KycStatus.VERIFIED.value, KycStatus.REJECTED.value):
        apply_kyc_decision(session, user, record, decision)

    return HTMLResponse(
        f"<div id='kyc-status' class='text-sm'>KYC status: <b>{user.kyc_status}</b></div>"
    )


@router.get("/status")
def kyc_status(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    latest = session.exec(
        select(KycVerification)
        .where(KycVerification.user_id == user.id)
        .order_by(KycVerification.created_at.desc())
    ).first()
    return {
        "kyc_status": user.kyc_status,
        "latest_submission": {
            "id": str(latest.id),
            "doc_type": latest.doc_type,
            "status": latest.status,
        }
        if latest
        else None,
    }
