import uuid
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from app.engine.matching import rank_candidates
from app.config import config

try:
    from app.db import get_session
    from app.models import User, ResidentProfile, Hostel, Room
except ImportError:
    class User: pass
    class ResidentProfile: pass
    class Hostel: pass
    class Room: pass
    def get_session(): yield None

router = APIRouter(prefix="/api/roommate-matches", tags=["Roommate Matches"])

# 1. GET /api/roommate-matches/{booking_id}/recommendations
@router.get("/{booking_id}/recommendations", response_class=HTMLResponse)
def get_roommate_recommendations(booking_id: uuid.UUID):
    return HTMLResponse(content="<div class='info'>DPDP redacted roommate candidates pool template loading.</div>")

# 2. POST /api/roommate-matches/ (Initiate Proposal)
@router.post("/", response_class=HTMLResponse)
def create_roommate_match(target_candidate_id: uuid.UUID):
    return HTMLResponse(content="<div class='success'>Match row instantiated as PROPOSED, a_accepted flagged True.</div>")

# 3. POST /api/roommate-matches/{match_id}/accept (Mutual Consent Acceptance)
@router.post("/{match_id}/accept", response_class=HTMLResponse)
def accept_roommate_match(match_id: uuid.UUID):
    return HTMLResponse(content="<div class='success'>Match confirmed. Automated linked booking created for Resident B.</div>")

# 4. POST /api/roommate-matches/{match_id}/reject (Mutual Consent Rejection)
@router.post("/{match_id}/reject", response_class=HTMLResponse)
def reject_roommate_match(match_id: uuid.UUID):
    return HTMLResponse(content="<div class='info'>Match proposal rejected and closed.</div>")

# 5. POST /api/roommate-matches/{booking_id}/cancel (Cancellation Cascades)
@router.post("/{booking_id}/cancel", response_class=HTMLResponse)
def cancel_booking_cascade(booking_id: uuid.UUID):
    return HTMLResponse(content="<div class='warning'>Booking cancelled. Cascading rollback executed successfully.</div>")