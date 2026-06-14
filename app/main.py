"""HostelLo — FastAPI entrypoint. All routers pre-registered (Phase 0 contract,
frozen afterward).
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

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


os.makedirs(os.path.join("static", "uploads"), exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="HostelLo", lifespan=lifespan)

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
