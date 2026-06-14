"""JWT issuance + in-memory OTP store.

Single-worker deployment (uvicorn -w 1, HLD §7.3) makes the in-process OTP
dict safe; a multi-worker deploy would need Redis/shared SQLite instead.
"""
import time
import uuid
from typing import Optional

from jose import jwt, JWTError

from app.config import config

COOKIE_NAME = "access_token"

# phone -> {code, expires_at, attempts}
_otp_store: dict = {}


def issue_otp(phone: str, code: str) -> None:
    _otp_store[phone] = {
        "code": code,
        "expires_at": time.time() + config.OTP_WINDOW_SECONDS,
        "attempts": 0,
    }


def check_otp(phone: str, code: str) -> tuple[bool, str]:
    """Returns (ok, error_message). Rate-limits attempts per OTP window."""
    entry = _otp_store.get(phone)
    if not entry:
        return False, "No OTP requested for this phone."
    if time.time() > entry["expires_at"]:
        _otp_store.pop(phone, None)
        return False, "OTP expired. Request a new one."
    entry["attempts"] += 1
    if entry["attempts"] > config.MAX_OTP_ATTEMPTS:
        _otp_store.pop(phone, None)
        return False, "Too many attempts. Request a new OTP."
    if entry["code"] != code:
        return False, "Invalid OTP."
    _otp_store.pop(phone, None)
    return True, ""


def create_access_token(user_id: uuid.UUID, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": int(time.time()) + config.JWT_EXPIRE_MINUTES * 60,
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
    except JWTError:
        return None
