"""OTP auth (mocked SMS) -> JWT httpOnly cookie. HLD §4.1, TDD §10."""
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, Response
from sqlmodel import Session, select

from app.db import get_session
from app.models import User, UserRole
from app.security import COOKIE_NAME, check_otp, create_access_token, issue_otp
from app.services.sms import sms_provider

router = APIRouter(prefix="/api/auth", tags=["Auth"])


def _is_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"


@router.post("/request-otp")
def request_otp(
    request: Request,
    phone: str = Form(..., min_length=10, max_length=15),
    role: str = Form(...),
    session: Session = Depends(get_session),
):
    if role not in (UserRole.OWNER.value, UserRole.RESIDENT.value):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")

    user = session.exec(select(User).where(User.phone == phone)).first()
    if user and user.role != role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This phone is registered as {user.role}. One role per account.",
        )
    if not user:
        user = User(phone=phone, role=role)
        session.add(user)
        session.commit()

    code = sms_provider.send_otp(phone)
    issue_otp(phone, code)

    if _is_htmx(request):
        return HTMLResponse(
            "<form id='otp-step' hx-post='/api/auth/verify-otp' hx-target='#otp-step' hx-swap='outerHTML' "
            "class='space-y-3'>"
            f"<input type='hidden' name='phone' value='{phone}'>"
            "<p class='text-sm text-gray-600'>OTP sent (dev code: <b>123456</b>).</p>"
            "<input name='code' placeholder='Enter OTP' class='border rounded p-2 w-full' required>"
            "<button class='bg-indigo-600 text-white rounded px-4 py-2 w-full'>Verify</button>"
            "</form>"
        )
    return {"detail": "OTP sent", "phone": phone}


@router.post("/verify-otp")
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
        COOKIE_NAME, token, httponly=True, samesite="lax", max_age=60 * 60 * 12, path="/"
    )
    return response


@router.post("/logout")
def logout():
    response = JSONResponse({"detail": "Logged out"})
    response.delete_cookie(COOKIE_NAME, path="/")
    response.headers["HX-Redirect"] = "/"
    return response
