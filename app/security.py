"""JWT issuance + in-memory OTP store.

Single-worker deployment (uvicorn -w 1, HLD §7.3) makes the in-process OTP
dict safe; a multi-worker deploy would need Redis/shared SQLite instead.
"""
import hmac
import time
import uuid
from typing import Optional

import jwt

from app.config import config

COOKIE_NAME = "access_token"

# phone -> {code, expires_at, attempts, sends: [timestamps]}
# `attempts` is cumulative across re-issues within the window so re-requesting an
# OTP does NOT reset the brute-force budget. State is cleared on success/expiry.
_otp_state: dict = {}


def _prune_sends(phone: str, now: float) -> list:
    st = _otp_state.get(phone)
    if not st:
        return []
    st["sends"] = [t for t in st.get("sends", []) if now - t < config.OTP_WINDOW_SECONDS]
    return st["sends"]


def can_request_otp(phone: str) -> tuple[bool, str]:
    """Throttle OTP sends per phone within the window to blunt SMS-bomb / DB-bloat abuse."""
    sends = _prune_sends(phone, time.time())
    if len(sends) >= config.OTP_MAX_SENDS_PER_WINDOW:
        return False, "Too many OTP requests. Try again later."
    return True, ""


def issue_otp(phone: str, code: str) -> None:
    now = time.time()
    st = _otp_state.setdefault(phone, {"attempts": 0, "sends": []})
    _prune_sends(phone, now)
    st["sends"].append(now)
    st["code"] = code
    st["expires_at"] = now + config.OTP_WINDOW_SECONDS
    # NB: attempts intentionally preserved across re-issues.


def check_otp(phone: str, code: str) -> tuple[bool, str]:
    """Returns (ok, error_message). Cumulative, constant-time, rate-limited."""
    entry = _otp_state.get(phone)
    if not entry or "code" not in entry:
        return False, "No OTP requested for this phone."
    if time.time() > entry["expires_at"]:
        _otp_state.pop(phone, None)
        return False, "OTP expired. Request a new one."
    entry["attempts"] += 1
    if entry["attempts"] > config.MAX_OTP_ATTEMPTS:
        _otp_state.pop(phone, None)
        return False, "Too many attempts. Request a new OTP."
    # Constant-time comparison to avoid leaking the code via response timing.
    if not hmac.compare_digest(entry["code"], code):
        return False, "Invalid OTP."
    _otp_state.pop(phone, None)
    return True, ""


def create_access_token(user_id: uuid.UUID, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": int(time.time()) + config.JWT_EXPIRE_MINUTES * 60,
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Verifies signature + expiry and requires the claims we depend on.

    Returns None for any invalid/forged/expired/malformed token (callers treat
    None as unauthenticated) — never raises into the request path.
    """
    try:
        payload = jwt.decode(
            token,
            config.JWT_SECRET,
            algorithms=[config.JWT_ALGORITHM],
            options={"require": ["exp", "sub", "role"]},
        )
    except jwt.PyJWTError:
        return None
    # `sub` must be a well-formed UUID, else the token is unusable downstream.
    try:
        uuid.UUID(str(payload["sub"]))
    except (ValueError, TypeError, KeyError):
        return None
    return payload
