"""HostelLo — FastAPI entrypoint. All routers pre-registered (Phase 0 contract,
frozen afterward).
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import config
from app.db import init_db
from app.routers import (
    assets,
    auth,
    bookings,
    kyc,
    owner_bookings,
    owners,
    pages,
    residents,
    roommate_matches,
)
from app.services.uploads import KYC_DIR, ROOM_DIR

# Gated upload store lives outside the StaticFiles tree (see services/uploads.py).
os.makedirs(ROOM_DIR, exist_ok=True)
os.makedirs(KYC_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="HostelLo", lifespan=lifespan)

if config.allowed_hosts != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=config.allowed_hosts)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' https: data:; "
        "script-src 'self' https://unpkg.com https://cdn.tailwindcss.com 'unsafe-inline'; "
        "style-src 'self' https: 'unsafe-inline'; frame-ancestors 'none'",
    )
    return response


app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(pages.router)
app.include_router(auth.router)
app.include_router(kyc.router)
app.include_router(residents.router)
app.include_router(bookings.router)
app.include_router(roommate_matches.router)
app.include_router(owners.router)
app.include_router(owners.hostel_rooms_router)
app.include_router(owner_bookings.router)
app.include_router(assets.router)
