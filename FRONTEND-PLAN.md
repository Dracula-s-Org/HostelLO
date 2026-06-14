# HostelLo — Frontend Implementation Plan

**Status:** Draft for review · **Date:** 2026-06-14
**Source design:** `~/Downloads/stitch_hostello_roommate_matcher` (Google Stitch export — design system + ~33 screens)
**Decision so far:** React app in a subfolder of this repo (`/frontend`), monorepo.

---

## 1. The decision that shapes everything: API shape

The backend is **not** a JSON API today. It is a server-rendered **HTMX + Jinja2** app:

- `app/routers/pages.py` serves full HTML pages (`/`, `/resident`, `/owner`).
- Most data endpoints return **HTML fragments**, not JSON:
  `GET /api/residents/recommendations`, `GET /api/bookings/mine`,
  `GET /api/roommate-matches/pending`, `GET /api/owners/hostels`,
  `GET /api/owners/bookings`.
- Only `auth` content-negotiates to JSON. `residents/me`, `owners/me`, `kyc/status`
  already return JSON.

A React SPA needs JSON for every screen. So **workstream #1 is exposing a JSON API.**

### Decided approach: React-only
We're retiring the HTMX/Jinja UI, not running it in parallel.

- The five HTML-fragment endpoints get **converted** to return JSON (no content
  negotiation, no dual paths).
- `app/serializers.py` already shapes several views — each endpoint reuses or extends
  these. PII-gating logic (`to_owner_applicant_view`, etc.) must be preserved.
- The template layer (`templates/`, partials, `app/templating.py`) and the
  page-serving routes in `pages.py` get removed; FastAPI serves the SPA instead.

> This is the largest single piece of backend work, and it's specced for the backend
> team in `BACKEND-HANDOFF.md`. Until it's done, React screens can't be wired to live
> data.

### Auth for a SPA — already in good shape
Auth uses **JWT in an httpOnly cookie**, which works cleanly for a same-origin SPA
(no token-in-localStorage XSS risk). With React served same-origin (Vite dev proxy +
prod served by FastAPI/Render), cookies "just work." No major change needed.

---

## 2. Proposed frontend architecture

```
/frontend
  ├─ index.html
  ├─ vite.config.ts          # dev proxy: /api + /static → FastAPI
  ├─ tailwind.config.ts      # design tokens ported from DESIGN.md (see §3)
  ├─ tsconfig.json
  ├─ package.json
  └─ src/
     ├─ main.tsx
     ├─ App.tsx              # router
     ├─ lib/
     │   ├─ api.ts           # typed fetch client (credentials: 'include')
     │   └─ types.ts         # mirrors domain models
     ├─ components/          # design-system primitives (Button, Chip, Card, …)
     ├─ layouts/             # TopNav / BottomNav shells (mobile-first)
     ├─ features/
     │   ├─ auth/            # welcome, OTP, KYC
     │   ├─ resident/        # onboarding, search, booking, roommates
     │   └─ owner/           # dashboard, hostels, rooms, approvals
     └─ routes.tsx
```

**Stack:** Vite + React + TypeScript, React Router, Tailwind (build step, **not** CDN).
**Mobile-first** — the designs are phone screens with a bottom nav bar + desktop breakpoints.

**Deploy (decided):** single same-origin service — `vite build` → static assets, served
by FastAPI (catch-all returns `index.html` so client routes resolve). One Render
service, no CORS. Wire into `render.yaml` at the end.

---

## 3. Design system port

`hostello_design_system/DESIGN.md` is the source of truth. The Stitch `code.html`
files already contain a working `tailwind.config` block — port it verbatim into
`tailwind.config.ts`:

- **Colors** — full Material-style token set (`primary #003b5a`, `secondary-container`
  coral `#fe6f42`, tertiary teal, surface ladder, etc.).
- **Typography** — Plus Jakarta Sans (headings) + Inter (body); named scales
  `display-lg`, `headline-lg`, `body-md`, `label-sm`, …
- **Radius / spacing** — `rounded-xl` cards, `stack-md` (24px) rhythm, 8px base scale.
- **Components** — habit chips (pills), compatibility bars (rounded end-caps),
  KYC status dots, hostel cards, progress steppers, "verified" badges.

Fonts via `@fontsource` (bundled) rather than Google CDN, to satisfy the existing CSP
and avoid a runtime dependency. Icons are **Material Symbols** — use the icon font or
an SVG set.

Converting each `code.html` → React becomes largely mechanical once tokens match:
extract repeated markup into the `components/` primitives, replace placeholder data
with API calls.

---

## 4. Screen → route → endpoint map

Several `_interactive` variants are just state variations of the same screen and will
collapse into one React component with state. The 6 `untitled_prototype_*` folders are
byte-identical copies of one file: the **public marketing landing page** (hero, match-
engine explainer, feature pillars, match demo, CTA, footer). We keep one as the public
landing route and drop the duplicates.

### Public & onboarding (shared)
| Screen(s) | React route | Backend endpoint(s) | Notes |
|---|---|---|---|
| `untitled_prototype_*` (marketing) | `/` (public) | — | Marketing landing; CTA → role pick → OTP |
| `hostello_welcome_1/2` | `/welcome` | — | Role pick (resident/owner) → OTP |
| `verify_your_phone_1`, `verify_your_phone_interactive` | `/auth/otp` | `POST /api/auth/request-otp`, `POST /api/auth/verify-otp` | Cookie set on verify; `verify_your_phone_2` has no png |
| `kyc_verification` | `/kyc` | `POST /api/kyc/submit`, `GET /api/kyc/status` | File upload; dev provider auto-decides |

### Resident — onboarding profile
All of these write to **one** profile via `POST /api/residents/profile` (create) /
`PUT /api/residents/profile` (update). They're a multi-step wizard over one model.
| Screen(s) | React route | Endpoint | Fields |
|---|---|---|---|
| `setup_identity_budget`, `setup_identity_interactive` | `/onboarding/identity` | profile (create) | name, age, gender, budget_min/max, preferred_location |
| `setup_lifestyle_intent`, `setup_lifestyle_interactive` | `/onboarding/lifestyle` | profile (update) | sleep_schedule, diet, social_type, smoking, drinking, seeking_shared |
| `setup_core_habits`, `setup_core_habits_interactive` | `/onboarding/habits` | profile (update) | cleanliness, gaming_freq, study_habits, fitness_freq, visitors_freq, amenity_preferences |

### Resident — discovery & booking
| Screen(s) | React route | Endpoint | Notes |
|---|---|---|---|
| `hostello_interactive_home` | `/resident` | `GET /api/residents/me`, recommendations | Dashboard |
| `hostels_for_you`, `hostels_for_you_interactive_1/2` | `/resident/hostels` | `GET /api/residents/recommendations` | **Needs JSON** (currently HTML). Score/price/location/amenity fit |
| `hostel_details`, `hostel_details_interactive` | `/resident/hostels/:id` | **GAP — no endpoint** | See §5: need `GET /api/hostels/:id` |
| `room_selection`, `room_selection_interactive` | `/resident/hostels/:id/rooms` | **GAP — no endpoint** + `POST /api/bookings` | See §5: need `GET /api/hostels/:id/rooms` |
| `roommate_recommendation`, `roommate_recommendation_interactive_1/2` | `/resident/bookings/:id/roommates` | `GET /api/bookings/:id/roommate-recommendations`, `POST /api/roommate-matches` | Shared-room flow; compatibility breakdown |
| `booking_status`, `booking_status_interactive_1/2` | `/resident/bookings` | `GET /api/bookings/mine`, `POST /api/bookings/:id/cancel` | REQUESTED/CONFIRMED/etc. states |
| `booking_confirmed`, `booking_confirmed_interactive` | `/resident/bookings/:id` (confirmed state) | `GET /api/bookings/mine` | Success state |
| `booking_approval_interactive`, `booking_approval_request_1/2` | `/resident/roommate-requests` | `GET /api/roommate-matches/pending`, `POST .../accept`, `POST .../reject` | **Incoming roommate proposals** to this resident (accept requires KYC) — confirm interpretation (Q4) |

### Owner
| Screen(s) | React route | Endpoint | Notes |
|---|---|---|---|
| `owner_dashboard`, `owner_dashboard_interactive` | `/owner` | `GET /api/owners/me`, `GET /api/owners/hostels`, `GET /api/owners/bookings` | All three currently HTML → need JSON |
| `create_edit_hostel`, `create_edit_hostel_interactive` | `/owner/hostels/new` (+ edit) | `POST /api/owners/hostels` | Requires KYC_VERIFIED. **GAP: no edit/update endpoint** — only create (Q5) |
| `add_configure_rooms`, `add_configure_rooms_interactive` | `/owner/hostels/:id/rooms` | `POST /api/hostels/:id/rooms` | Multipart image upload; KYC-gated |
| (owner approval queue — part of `owner_dashboard`) | `/owner/bookings` | `GET /api/owners/bookings`, `POST /api/bookings/:id/approve`, `POST /api/bookings/:id/reject` | Applicant PII-gated pre-approval |

---

## 5. Backend gaps the designs assume but the API lacks

These screens need endpoints that **don't exist yet**:

1. **`GET /api/hostels/:id`** — public hostel detail (for `hostel_details`). Today
   there's no read endpoint for a single hostel from the resident side.
2. **`GET /api/hostels/:id/rooms`** — room list for a hostel (for `room_selection`).
   Rooms can only be *created* today, not listed by a resident.
3. **Hostel edit** — `create_edit_hostel` implies update; only `POST` (create) exists.
   Need `PUT /api/owners/hostels/:id`.
4. **JSON variants** of the five HTML-fragment endpoints (see §1).

None are large, but they're prerequisites — the React screens for hostel detail and
room selection are blocked without #1 and #2.

---

## 6. Assets

- Stitch placeholder images point at `lh3.googleusercontent.com` (throwaway) — replace.
- **Room images:** already handled — `static/uploads/rooms/` + gated
  `GET /api/assets/rooms/:room_id/:index`. Cloudinary (in the infra plan) is the
  production target.
- **Icons:** Material Symbols — bundle the font or an SVG subset.
- **Logo / illustrations:** none in the export; need source files (Q6).

---

## 7. Phased build plan

1. **Backend JSON API** — content negotiation + serializers for the 5 HTML endpoints;
   add the 3 missing endpoints (§5). *Prereq for everything.*
2. **Scaffold `/frontend`** — Vite + React + TS, Tailwind tokens, fonts, router shell,
   typed API client, mobile layout with TopNav/BottomNav.
3. **Design-system primitives** — Button, Chip, CompatibilityBar, Card, StatusDot,
   Stepper, etc., from `DESIGN.md` + `code.html`.
4. **Auth + onboarding vertical** — welcome → OTP → KYC → resident profile wizard.
5. **Resident vertical** — discovery, hostel detail, room selection, booking, roommate
   matching, booking status.
6. **Owner vertical** — dashboard, create/edit hostel, configure rooms, approval queue.
7. **Deploy wiring** — `vite build`, serve via FastAPI/Render, update `render.yaml`.

---

## 8. Decisions (resolved 2026-06-14)

- **Q1 — Templates:** React-only. Retire the HTMX/Jinja layer (see §1).
- **Q2 — Serving:** Single same-origin service, FastAPI serves the bundle (see §2).
- **Q3 — `untitled_prototype_*`:** The marketing landing page. Keep one, drop the
  5 duplicates (see §4).
- **Q4 — `booking_approval_*`:** Resident-side incoming roommate accept/reject, mapped
  to `/api/roommate-matches/pending`.
- **Q5 — Hostel edit:** In scope. Needs `PUT /api/owners/hostels/:id` (in handoff).
- **Q6 — Brand assets:** Placeholders for now; real logo/illustrations to follow.
- **Q7 — Scope:** Both verticals (resident + owner).
