# Backend handoff: API changes for the React frontend

**From:** Frontend (HostelLo web app, `/frontend`)
**Date:** 2026-06-14
**Context:** We're building the React UI in a subfolder of this repo. The screens are ready (Stitch export + design system). We've decided to go **React-only** — the HTMX/Jinja frontend is being retired. So the data endpoints that currently return HTML need to return JSON, and the template-serving layer comes out. Full screen→endpoint mapping is in `FRONTEND-PLAN.md`; this doc is the backend work I need.

None of this touches your domain logic, auth model, or the matching engine.

---

## Decisions already made (so nobody's guessing)

- **React-only.** The Jinja templates and HTMX partials are being removed, not kept in parallel. The five data endpoints below should just return JSON — no content negotiation, no dual HTML/JSON paths.
- **Single same-origin service.** FastAPI serves the built React bundle in prod (one Render service). That means **no CORS work** — auth cookies work as-is because everything is one origin. In dev, Vite proxies `/api` to FastAPI, also same-origin from the browser's view.
- **Auth unchanged.** JWT in an httpOnly cookie stays exactly as it is.
- **PII gating reused.** Every JSON response goes through the existing `app/serializers.py` views. Same allowlists, same masking. Please don't hand-roll field stripping in the new paths.

---

## Part A — Convert these 5 endpoints from HTML to JSON

Each of these returns `HTMLResponse` / `TemplateResponse` today. Change them to return JSON. The serializers mostly already exist, so this is mostly deleting the template render and returning the dict.

### A1. `GET /api/residents/recommendations`
`app/routers/residents.py:211` already builds a `cards` list (hostel + rooms + score + fit vectors) before rendering. Serialize that instead of rendering `recommendations.html`. Proposed shape:

```json
{
  "results": [
    {
      "hostel": {
        "id": "uuid", "name": "…", "address": "…", "location": "bangalore",
        "gender_policy": "COED", "listing_tier": "PREMIUM", "verified": true,
        "amenities": ["wifi", "ac"], "veg_only": false,
        "allow_smoking": false, "allow_drinking": false,
        "min_age": null, "max_age": null
      },
      "rooms": [
        { "id": "uuid", "type": "SHARED", "capacity": 3, "occupied_count": 1,
          "price": 8000, "status": "AVAILABLE", "image_count": 2 }
      ],
      "score": 87.4, "price_fit": 0.9, "location_fit": 1.0, "amenity_fit": 0.75
    }
  ]
}
```

`image_count` rather than raw paths — the client pulls images through the gated `GET /api/assets/rooms/{room_id}/{index}` you already have. A small `to_recommendation_view(...)` in `serializers.py` would keep the hostel/room shapes consistent across A1, B1, and B2.

### A2. `GET /api/bookings/mine`
Resident's bookings with enough room/hostel context for the status screens:

```json
{
  "bookings": [
    {
      "id": "uuid", "status": "REQUESTED", "created_at": "2026-06-14T10:00:00Z",
      "room": { "id": "uuid", "type": "SHARED", "price": 8000 },
      "hostel": { "id": "uuid", "name": "…", "location": "bangalore" },
      "roommate_match_id": "uuid-or-null"
    }
  ]
}
```

### A3. `GET /api/bookings/{booking_id}/roommate-recommendations`
The candidate pool for a shared-room booking. Maps straight to the existing `to_candidate_view` (first name + score + breakdown + habits):

```json
{ "candidates": [ { /* to_candidate_view output */ } ] }
```

### A4. `GET /api/roommate-matches/pending`
Incoming roommate proposals for the logged-in resident. This backs the `booking_approval_*` screens — confirmed as the resident-side "someone wants to room with you, accept/decline" flow. Per item I need: `match_id`, proposer first name, compatibility score, and the breakdown so we can draw the bars.

```json
{
  "pending": [
    { "match_id": "uuid", "score": 82,
      "breakdown": { "social_style": 90, "study_habits": 88, "...": 0 },
      "from": { "first_name": "Rahul" } }
  ]
}
```

### A5. Owner endpoints — `GET /api/owners/hostels` and `GET /api/owners/bookings`
- `owners/hostels`: the owner's hostels with their room matrix and a pending-booking count per hostel.
- `owners/bookings`: the review queue. Applicant data must come from `to_owner_applicant_view` (first name + habits only, pre-approval). Include the roommate match breakdown when one is linked.

No strong opinion on exact field names for these two — give me the JSON you find natural and I'll match the client to it.

---

## Part B — New endpoints

### B1. `GET /api/hostels/{hostel_id}` — hostel detail
Single hostel by id, for the `hostel_details` screen. Same hostel fields as A1. Resident-authenticated is fine. 404 if not found.

### B2. `GET /api/hostels/{hostel_id}/rooms` — room list for a hostel
Rooms for the `room_selection` screen. Same room shape as A1 (`image_count`, not paths). Today rooms can only be created, never listed by a resident.

### B3. `PUT /api/owners/hostels/{hostel_id}` — edit a hostel
Hostel editing is in scope. Mirror the `POST /api/owners/hostels` create endpoint's fields, with the same ownership + KYC-verified checks. Backs the edit half of the `create_edit_hostel` screen.

---

## Part C — Retire the template layer

Going React-only means the server-rendered UI comes out. This can land after Part A/B (it doesn't block me), but it's part of the same migration:

- Remove the Jinja templates (`templates/`), the HTMX partials, and `app/templating.py`.
- The page-serving routes in `app/routers/pages.py` (`/`, `/resident`, `/owner`) get replaced by serving the SPA: FastAPI returns the built `index.html` for non-API routes (a catch-all so client-side routes like `/resident/hostels/:id` resolve). I can help wire this when the bundle exists — happy to own the static-mount + catch-all piece if you'd rather I do it.
- The CSP in `app/main.py` currently allowlists `unpkg.com` (HTMX) and `cdn.tailwindcss.com`. Once we're React-only with a Tailwind build step, both can be dropped and the CSP tightened. Low priority, but worth doing before launch.

---

## What I am NOT asking you to change

- Auth flow (`request-otp` / `verify-otp` / `logout`).
- The matching engine and booking/allocation services.
- KYC submit/status, assets gating, the upload store.

---

## Suggested order

B1 and B2 first — small, and they unblock the most screens. Then A1–A3 (resident flow), then A4–A5 (owner flow) and B3 (hostel edit). Part C (template teardown) last, since it doesn't block frontend work.

When a batch is ready, the most useful handback is the actual JSON each endpoint returns — a curl dump or a couple of example responses against seed data (`app/seed.py`). With that I can wire the client without guessing field names.
