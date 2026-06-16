"""OTP auth (mocked SMS) -> JWT httpOnly cookie. HLD §4.1, TDD §10."""
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, Response
from markupsafe import escape
from sqlmodel import Session, select

from app.config import config
from app.db import get_session
from app.models import User, UserRole
from app.ratelimit import limiter
from app.security import (
    COOKIE_NAME,
    can_request_otp,
    check_otp,
    create_access_token,
    issue_otp,
)
from app.services.sms import sms_provider
from app.validators import PHONE_RE

router = APIRouter(prefix="/api/auth", tags=["Auth"])


def _is_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"


def _otp_sent_response(request: Request, phone: str):
    """Uniform 'OTP sent' response — never leaks whether the phone exists or its role."""
    if _is_htmx(request):
        return HTMLResponse(
            "<form id='otp-step' hx-post='/api/auth/verify-otp' hx-target='#otp-step' hx-swap='outerHTML' "
            "class='space-y-3'>"
            f"<input type='hidden' name='phone' value='{escape(phone)}'>"
            "<p class='text-sm text-gray-600'>If that number is eligible, an OTP has been sent.</p>"
            "<input name='code' placeholder='Enter OTP' class='border rounded p-2 w-full' required>"
            "<button class='bg-indigo-600 text-white rounded px-4 py-2 w-full'>Verify</button>"
            "</form>"
        )
    return {"detail": "If that number is eligible, an OTP has been sent."}


@router.post("/request-otp")
@limiter.limit("30/minute")  # per-IP; per-phone send cap still applies. Raised so several judges behind one venue NAT don't collectively 429.
def request_otp(
    request: Request,
    phone: str = Form(..., min_length=10, max_length=15),
    role: str = Form(...),
    session: Session = Depends(get_session),
):
    if role not in (UserRole.OWNER.value, UserRole.RESIDENT.value):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")
    if not PHONE_RE.match(phone):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid phone number")

    ok, _ = can_request_otp(phone)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many OTP requests. Try again later.",
        )

    user = session.exec(select(User).where(User.phone == phone)).first()
    if user is not None and user.role != role:
        # Enforce one-role-per-account, but DON'T name the existing role — that
        # turned the response into a role-enumeration oracle.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This phone number is already registered. One role per account.",
        )
    if user is None:
        user = User(phone=phone, role=role)
        session.add(user)
        session.commit()

    code = sms_provider.send_otp(phone)
    issue_otp(phone, code)

    return _otp_sent_response(request, phone)


@router.post("/verify-otp")
@limiter.limit("30/minute")  # per-IP; per-phone attempt budget still applies. Raised for shared-NAT demo audiences.
def verify_otp(
    request: Request,
    phone: str = Form(...),
    code: str = Form(...),
    session: Session = Depends(get_session),
):
    ok, err = check_otp(phone, code)
    if not ok:
        if _is_htmx(request):
            return HTMLResponse(f"<div class='text-red-600 text-sm'>{err}</div>", status_code=400)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)

    user = session.exec(select(User).where(User.phone == phone)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    token = create_access_token(user.id, user.role)
    target = "/owner" if user.role == UserRole.OWNER.value else "/resident"

    if _is_htmx(request):
        response: Response = HTMLResponse("<div class='text-green-700'>Logged in. Redirecting…</div>")
        response.headers["HX-Redirect"] = target
    else:
        response = JSONResponse({"detail": "Logged in", "role": user.role, "redirect": target})
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        secure=config.cookie_secure,
        samesite="lax",
        max_age=config.JWT_EXPIRE_MINUTES * 60,
        path="/",
    )
    return response


@router.post("/logout")
def logout():
    response = JSONResponse({"detail": "Logged out"})
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, secure=config.cookie_secure, samesite="lax")
    response.headers["HX-Redirect"] = "/"
    return response
