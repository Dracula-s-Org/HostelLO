# HostelLO

HostelLo is a dual-profile hostel management application that connects students seeking accommodation with property owners. It uses an intelligent matching system, including a "habits-match" mechanism, to pair residents with suitable rooms and compatible roommates.

## Quick start

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m app.seed          # idempotent demo data
.venv/bin/uvicorn app.main:app --reload
```

Open http://localhost:8000 — OTP is always `123456` in mock mode.

| Login | Phone |
|---|---|
| Owner | `9100000001` |
| Residents | `9000000001` … `9000000005` |

Tests: `.venv/bin/python -m pytest`

## Golden path (demo)

1. Owner signs up, completes mocked KYC, lists a hostel with tenant criteria + rooms.
2. Resident completes profile + habits and sees a filtered, ranked hostel list.
3. Resident picks a **shared** room → compatible roommate recommended → both accept (mutual consent).
4. Booking request reaches the owner (DPDP-redacted view) → owner approves → both linked bookings confirm atomically; full rooms sweep competing requests.

## Layout

- `app/engine/` — pure matching engines (hostel recommendation + roommate ranking)
- `app/services/` — booking allocation (ordered-lock transaction), lifecycle cascades, candidate pool, storage
- `app/routers/` — auth (OTP→JWT cookie), KYC mock, resident/owner verticals, assets
- `app/serializers.py` — shared DPDP data-gating views
- `app/spa.py` — serves the built React bundle (`frontend/dist`) + a catch-all so client-side routes resolve; the API is JSON-only (React frontend)

Deployment (Render + Neon + Cloudinary): see [DEPLOY.md](DEPLOY.md).
