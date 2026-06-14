"""Shared auth/role/KYC route guards (Phase 0 contract)."""
import uuid

from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session

from app.db import get_session
from app.models import KycStatus, OwnerProfile, ResidentProfile, User, UserRole
from app.security import COOKIE_NAME, decode_access_token


def get_current_user(
    request: Request, session: Session = Depends(get_session)
) -> User:
    token = request.cookies.get(COOKIE_NAME)
    payload = decode_access_token(token) if token else None
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user = session.get(User, uuid.UUID(payload["sub"]))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown user")
    return user


def get_optional_user(request: Request, session: Session = Depends(get_session)):
    token = request.cookies.get(COOKIE_NAME)
    payload = decode_access_token(token) if token else None
    if not payload:
        return None
    return session.get(User, uuid.UUID(payload["sub"]))


def require_role(role: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {role} role",
            )
        return user

    return checker


def get_current_resident(
    user: User = Depends(require_role(UserRole.RESIDENT.value)),
    session: Session = Depends(get_session),
) -> ResidentProfile:
    profile = session.get(ResidentProfile, user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resident profile not found. Complete your profile first.",
        )
    return profile


def get_current_owner(
    user: User = Depends(require_role(UserRole.OWNER.value)),
    session: Session = Depends(get_session),
) -> OwnerProfile:
    profile = session.get(OwnerProfile, user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Owner profile not found. Complete your profile first.",
        )
    return profile


def require_kyc_verified(user: User = Depends(get_current_user)) -> User:
    if user.kyc_status != KycStatus.VERIFIED.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="KYC verification required for this action.",
        )
    return user
