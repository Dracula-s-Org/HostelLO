"""HostelLo — FastAPI entrypoint. All routers pre-registered (Phase 0 contract,
frozen afterward).
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import config
from app.db import init_db
from app.ratelimit import limiter
from app.routers import (
    assets,
    auth,
    bookings,
    hostels,
    kyc,
    owner_bookings,
    owners,
    residents,
    roommate_matches,
)
from app.spa import mount_spa
from app.services.uploads import KYC_DIR, ROOM_DIR

# Gated upload store lives outside the StaticFiles tree (see services/uploads.py).
os.makedirs(ROOM_DIR, exist_ok=True)
os.makedirs(KYC_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="HostelLo", lifespan=lifespan)

# IP-based rate limiting. The default 100/min/IP applies globally via the
# middleware; routers add tighter per-route caps (OTP, KYC, uploads).
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

if config.allowed_hosts != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=config.allowed_hosts)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    # React-only: the bundle is served same-origin, so no external script/style
    # CDNs are allowlisted (HTMX/unpkg + Tailwind CDN retired with the templates).
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' https: data:; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; frame-ancestors 'none'",
    )
    return response


app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth.router)
app.include_router(kyc.router)
app.include_router(residents.router)
app.include_router(bookings.router)
app.include_router(roommate_matches.router)
app.include_router(hostels.router)
app.include_router(owners.router)
app.include_router(owners.hostel_rooms_router)
app.include_router(owner_bookings.router)
app.include_router(assets.router)

# SPA catch-all must be registered LAST so it only receives non-API routes.
mount_spa(app)
