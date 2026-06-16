"""Shared request-layer validators (HLD §6 input hardening).

Centralizes the phone-format and enum-allowlist checks so every router rejects
malformed domain input the same way — instead of trusting DB column types
(SQLite ignores VARCHAR length, and the free-`str` profile columns would
otherwise accept any value).
"""
import re
from enum import Enum
from typing import Type

from fastapi import HTTPException, status

# E.164-ish: optional leading +, then 10–15 digits. Identical to the login
# check, so the only phone shape we ever store is one that could also log in.
PHONE_RE = re.compile(r"^\+?\d{10,15}$")


def validate_enum(value: str, enum: Type[Enum], field: str) -> str:
    """Reject any value outside the enum allowlist with a 400 (mirrors the
    inline checks owners.py already does for gender_policy/listing_tier)."""
    allowed = [e.value for e in enum]
    if value not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field}. Allowed: {', '.join(allowed)}",
        )
    return value


def validate_phone(value: str, field: str = "phone") -> str:
    if not PHONE_RE.match(value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field} number",
        )
    return value
