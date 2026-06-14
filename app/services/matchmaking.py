"""Candidate-pool construction (HLD §2.2.1) + ranking via Dev A's pure engine."""
import uuid
from typing import Optional

from sqlmodel import Session, select

from app.config import config
from app.engine.matching import rank_candidates, recommend_hostels
from app.models import (
    Booking,
    BookingStatus,
    GenderPolicy,
    Hostel,
    ResidentProfile,
    Room,
)
from app.services.engine_adapters import hostel_to_engine, resident_to_engine

ACTIVE_BOOKING_STATUSES = (BookingStatus.REQUESTED.value, BookingStatus.CONFIRMED.value)


def has_active_booking(session: Session, resident_id: uuid.UUID) -> bool:
    row = session.exec(
        select(Booking.id).where(
            Booking.resident_id == resident_id,
            Booking.status.in_(ACTIVE_BOOKING_STATUSES),
        )
    ).first()
    return row is not None


def clears_hostel_gate(profile: ResidentProfile, hostel: Hostel, rooms: list[Room]) -> bool:
    """Stage-1 hard-filter eligibility for one hostel, reusing the engine."""
    results = recommend_hostels(
        resident_to_engine(profile), [hostel_to_engine(hostel, rooms)], config
    )
    return len(results) > 0


def passes_gender_policy(profile: ResidentProfile, seeker: ResidentProfile, hostel: Hostel) -> bool:
    """Gender-policy isolation (HLD §2.2.1): COED pairs same-gender; otherwise
    the candidate's gender must equal the hostel policy."""
    if hostel.gender_policy == GenderPolicy.COED.value:
        return profile.gender == seeker.gender
    return profile.gender == hostel.gender_policy


def build_candidate_pool(
    session: Session, seeker: ResidentProfile, room: Room
) -> list[ResidentProfile]:
    hostel = session.get(Hostel, room.hostel_id)
    rooms = session.exec(select(Room).where(Room.hostel_id == hostel.id)).all()
    candidates = session.exec(
        select(ResidentProfile).where(
            ResidentProfile.user_id != seeker.user_id,
            ResidentProfile.seeking_shared == True,  # noqa: E712
        )
    ).all()
    pool = []
    for cand in candidates:
        if has_active_booking(session, cand.user_id):
            continue
        if not passes_gender_policy(cand, seeker, hostel):
            continue
        if not clears_hostel_gate(cand, hostel, list(rooms)):
            continue
        pool.append(cand)
    return pool


def rank_pool(seeker: ResidentProfile, pool: list[ResidentProfile]) -> list[tuple[ResidentProfile, dict]]:
    """Returns (profile, engine result) pairs sorted by score desc."""
    by_id = {str(p.user_id): p for p in pool}
    results = rank_candidates(
        resident_to_engine(seeker), [resident_to_engine(p) for p in pool], config
    )
    return [(by_id[r["candidate_id"]], r) for r in results if r["candidate_id"] in by_id]


def score_pair(seeker: ResidentProfile, candidate: ResidentProfile) -> Optional[dict]:
    """Pairwise score for one candidate, or None if hard gates exclude them."""
    ranked = rank_pool(seeker, [candidate])
    return ranked[0][1] if ranked else None
