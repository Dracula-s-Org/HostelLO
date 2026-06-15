import os

# Must be set before any app import — config reads env at import time
os.environ["DATABASE_URL"] = "sqlite:///./test_hostello.db"
os.environ["MOCK_OTP"] = "true"
os.environ["MOCK_KYC"] = "true"

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel

from app.db import engine
from app.main import app
from app import models  # noqa: F401 — register tables on metadata


@pytest.fixture(autouse=True)
def fresh_db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield


@pytest.fixture
def session():
    with Session(engine) as s:
        yield s


@pytest.fixture
def make_client():
    """Factory: one TestClient per actor (separate cookie jars)."""
    clients = []

    def _make():
        c = TestClient(app)
        c.__enter__()
        clients.append(c)
        return c

    yield _make
    for c in clients:
        c.__exit__(None, None, None)


def login(client: TestClient, phone: str, role: str) -> None:
    r = client.post("/api/auth/request-otp", data={"phone": phone, "role": role})
    assert r.status_code == 200, r.text
    r = client.post("/api/auth/verify-otp", data={"phone": phone, "code": "123456"})
    assert r.status_code == 200, r.text


# Minimal valid JPEG header — uploads are now validated by magic bytes, not the
# client-supplied content-type, so the fixture must look like a real image.
_JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01" + b"\x00" * 32


def submit_kyc(client: TestClient) -> None:
    r = client.post(
        "/api/kyc/submit",
        data={"doc_type": "AADHAAR"},
        files={"document": ("id.jpg", _JPEG_BYTES, "image/jpeg")},
    )
    assert r.status_code == 200, r.text


RESIDENT_FORM = {
    "name": "Test Resident",
    "age": "22",
    "gender": "MALE",
    "budget_min": "5000",
    "budget_max": "9000",
    "preferred_location": "koramangala",
    "sleep_schedule": "EARLY",
    "cleanliness": "4",
    "diet": "VEG",
    "social_type": "INTROVERT",
    "gaming_freq": "2",
    "study_habits": "4",
    "fitness_freq": "2",
    "visitors_freq": "1",
    "smoking": "false",
    "drinking": "false",
    "seeking_shared": "true",
}


def create_resident_profile(client: TestClient, **overrides) -> None:
    form = {**RESIDENT_FORM, **{k: str(v) for k, v in overrides.items()}}
    r = client.post("/api/residents/profile", data=form)
    assert r.status_code == 200, r.text
