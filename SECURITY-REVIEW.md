# HostelLo — Security Review Report

**Scope:** `develop` branch + PR #5 (`fix/security-hardening`)
**Method:** Static / code-level adversarial review (no live dynamic scan, no dependency CVE audit)
**Date:** 2026-06-14

---

## TL;DR

The app is **well-hardened for an MVP** on the classic OWASP axes — auth, access control, injection, XSS, uploads, and the booking-integrity race are all properly closed. There is **one must-fix-before-launch issue** (no global rate limiting → user-flood + SMS-cost DoS) and a few lower-severity items.

| Area | Status |
|------|--------|
| RBAC / object-level authorization | ✅ Pass |
| Input sanitization (XSS, SQLi, uploads, IDs) | ✅ Pass |
| Input validation (domain/business rules) | ⚠️ Gaps |
| CORS | ✅ Correct (same-origin) |
| Rate limiting | 🔴 Gap (OTP only, no global) |
| Secret/link expiry | ✅ Pass (no passwords; OTP + JWT expire) |
| SSTI | ✅ Not possible |
| Booking-integrity / overbooking race | ✅ Pass |

---

## 🔴 MUST FIX BEFORE LAUNCH

### 1. No global / IP-based rate limiting → DoS + SMS-cost amplification

**Where it fails:** `POST /api/auth/request-otp` ([app/routers/auth.py:45-80](app/routers/auth.py#L45-L80)).
OTP sends are throttled **per phone number** (5 / 5 min, [app/security.py:31-36](app/security.py#L31-L36)), but an attacker rotating through fake phone numbers bypasses this entirely. Each new phone also **creates a `User` row** ([app/routers/auth.py:72-75](app/routers/auth.py#L72-L75)), so the attack floods the database with junk accounts for free. Once a real SMS provider is wired, every request also burns SMS credits → **toll fraud**.

Secondary: no per-user cap on hostels/rooms/image uploads → an authenticated owner can exhaust disk.

**Severity:** HIGH (the one I would actually exploit against a live deploy).

**How to fix:**
1. Add IP-based rate limiting with [`slowapi`](https://github.com/laurentS/slowapi):
   ```python
   # app/main.py
   from slowapi import Limiter, _rate_limit_exceeded_handler
   from slowapi.util import get_remote_address
   from slowapi.errors import RateLimitExceeded

   limiter = Limiter(key_func=get_remote_address)
   app.state.limiter = limiter
   app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
   ```
   ```python
   # app/routers/auth.py
   @router.post("/request-otp")
   @limiter.limit("5/minute")          # per-IP, on top of the existing per-phone cap
   def request_otp(request: Request, ...):
       ...
   ```
   Apply a sane global default (e.g. `100/minute` per IP) and tighter limits on `request-otp`, `verify-otp`, `kyc/submit`, and the upload routes.
2. **Behind a proxy (Render):** trust `X-Forwarded-For` so the limiter sees the real client IP, not the proxy.
3. If you ever run more than one worker, move the OTP state (and the limiter store) to **Redis** — the current in-memory dict is single-worker only and resets on restart.
4. Add a per-owner cap on rooms/images, and confirm the 5 MiB per-file cap is enough (it is bounded today: [app/services/uploads.py:51-61](app/services/uploads.py#L51-L61)).

---

## 🟠 SHOULD FIX BEFORE LAUNCH

### 2. Production config protection depends on env vars being set correctly

**Where it fails (potentially):** The fail-fast validator ([app/config.py](app/config.py) `_enforce_production_safety`) only triggers when `ENVIRONMENT=production`. If the deploy doesn't set that — or ships without a strong `JWT_SECRET` — the app silently runs on the **dev default secret** (`hostello-dev-secret-change-me`), making session tokens forgeable.

**Severity:** HIGH *if misconfigured*, otherwise N/A. The protection itself is well-written; the risk is purely operational.

**How to fix:**
- Confirm `render.yaml` (or the deploy env) sets:
  - `ENVIRONMENT=production`
  - `JWT_SECRET=<32+ char random secret>` (generate: `python -c "import secrets; print(secrets.token_urlsafe(48))"`)
  - `MOCK_OTP=false`, `MOCK_KYC=false`
  - `ALLOWED_HOSTS=<your-domain>` (so `TrustedHostMiddleware` engages)
- Add a deploy smoke test that asserts the app refuses to boot with the default secret in production.

---

## 🟡 LOWER SEVERITY / POST-MVP

### 3. Input validation gaps (data integrity, not an attack vector)

Sanitization is solid (XSS via auto-escape, SQLi via ORM). But several **domain inputs accept garbage**:

**Where:** [app/routers/residents.py:98-208](app/routers/residents.py#L98-L208), [app/routers/kyc.py:35-42](app/routers/kyc.py#L35-L42), models at [app/models.py:108-130](app/models.py#L108-L130).

- `gender`, `sleep_schedule`, `diet`, `social_type` are stored as free `str` with **no enum allowlist** (the owner side *does* validate `gender_policy`/`listing_tier`/room `type` — the resident side just wasn't given the same treatment).
- `budget_min` / `budget_max` are floats with **no `ge=0`** and **no `budget_min <= budget_max`** check.
- KYC `doc_type` is unvalidated free text.
- `prebooked_roommate_phone` is stored without the phone regex used at login.
- String `max_length` is DB-enforced only — **SQLite ignores `VARCHAR` length**, so locally names can be arbitrarily long.

**How to fix:**
- Define `Enum`s (`GenderType`, `DietType`, `SocialType`, `SleepSchedule`, `DocType`) and validate in the router the same way owners.py already does:
  ```python
  if gender not in [g.value for g in GenderType]:
      raise HTTPException(400, "Invalid gender")
  ```
  or type the `Form(...)` params as the enums so FastAPI rejects bad values with 422.
- Add bounds: `budget_min: float = Form(..., ge=0)`, `budget_max: float = Form(..., ge=0)`, and after parsing: `if budget_min > budget_max: raise HTTPException(400, ...)`.
- Validate `prebooked_roommate_phone` against the same `_PHONE_RE`.
- Add explicit `max_length` validation at the request layer (don't rely on the DB).

### 4. `403` vs `404` reveals record existence (enumeration)

**Where:** e.g. cancel returns `403 "Not your booking"` ([app/services/booking_lifecycle.py:134-135](app/services/booking_lifecycle.py#L134-L135)), assets return `403 "Not your property"` ([app/routers/assets.py:31-32](app/routers/assets.py#L31-L32)).

A `403` (vs `404`) confirms a record with that ID exists. Low value because IDs are UUIDs (not guessable).

**How to fix:** Return `404` instead of `403` for cross-account access so existence is never confirmed. Normalize across all routers.

### 5. Stateless JWT with long lifetime, no revocation

**Where:** `JWT_EXPIRE_MINUTES: 720` (12h) in [app/config.py](app/config.py); logout only clears the cookie ([app/routers/auth.py:120-125](app/routers/auth.py#L120-L125)).

A stolen/leaked token stays valid until `exp` — logout can't revoke it.

**How to fix:** Shorten to ~1–2h, or add a server-side token denylist / `token_version` claim checked against the DB user. Lower priority given `httpOnly` + `SameSite=Lax`.

### 6. CSP uses `'unsafe-inline'` for scripts

**Where:** [app/main.py:49-54](app/main.py#L49-L54). Weakens the XSS defense-in-depth layer; documented as required by the HTMX / Tailwind CDN setup.

**How to fix:** When the React frontend lands and is self-hosted, drop the CDNs and remove `'unsafe-inline'` (use nonces/hashes).

### 7. CORS — currently correct, but a known future decision

**Where:** No `CORSMiddleware` is configured ([app/main.py](app/main.py)). This is **correct today** because the app is same-origin (UI + API served from one FastAPI process) with a `SameSite=Lax` cookie. Adding a permissive CORS policy now would be a *vulnerability*.

**How to fix (only when needed):** When the React SPA runs on a different origin (e.g. the Vite dev server on `:5173`, or a separate CDN domain in prod), add:
```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],   # explicit, NEVER "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
Never combine `allow_origins=["*"]` with `allow_credentials=True`.

---

## ✅ Verified secure (attacks that fail)

| Attack | Why it fails |
|--------|--------------|
| Forge / replay JWT | PyJWT signature verify; requires `sub`/`role`/`exp`; role re-read from DB, not trusted from token; prod fails-fast on default/weak secret ([app/security.py:77-97](app/security.py#L77-L97)) |
| OTP brute force | 5 cumulative attempts, constant-time compare, 5-min expiry ([app/security.py:49-65](app/security.py#L49-L65)) |
| IDOR / read another user's data | Ownership scoping on every ID path (residents, owners, bookings, matches, assets, KYC docs) |
| Resident harvesting owner contact (PII) | `GET /api/bookings/{id}` reveals `to_owner_contact_view` (owner name + contact) **only** for the requesting resident's own booking **and only** when `status == CONFIRMED`; REQUESTED/REJECTED/CANCELLED return `owner: null`, foreign bookings 403. Browse/listing views (`to_hostel_view`) stay PII-free ([app/routers/bookings.py](app/routers/bookings.py), [app/serializers.py](app/serializers.py)) |
| Overbook a room (concurrency race) | Atomic conditional `UPDATE ... occupied_count + delta <= capacity` + CHECK constraint ([app/services/booking_allocation.py:109-125](app/services/booking_allocation.py#L109-L125)) |
| Path traversal via `/api/assets` | `commonpath` guard rejects paths outside `var/uploads` ([app/services/uploads.py:21-32](app/services/uploads.py#L21-L32)) |
| Upload a web shell / disguised script | Magic-byte sniff, 5 MiB cap, server-generated filename, stored outside static tree, gated read |
| Stored / reflected XSS | Jinja2 auto-escape + explicit `escape()` on hand-built HTML |
| SSTI | No dynamic template rendering (`render_template_string` / `Template(user_input)` absent) |
| CSRF | `httpOnly` + `SameSite=Lax` cookie; all mutations are POST |
| Login role/account enumeration | Uniform "if eligible, OTP sent" response ([app/routers/auth.py:30-42](app/routers/auth.py#L30-L42)) |
| SQL injection | All queries via SQLModel/SQLAlchemy bound parameters; no raw SQL |

---

## Not covered by this review (recommended next steps)

- **Dynamic scan** against the running app (the PR removed vulnerable `ecdsa` via the `python-jose`→PyJWT migration, but the live surface wasn't fuzzed).
- **Dependency CVE audit** — run `pip-audit` against the full requirements tree.
- **Load / abuse test** of the rate-limiting fix once implemented.

---

## Prioritized fix checklist

- [ ] **#1** Add global + per-IP rate limiting (`slowapi`); move OTP state to Redis if multi-worker — *must fix*
- [ ] **#2** Verify `render.yaml` sets `ENVIRONMENT=production`, strong `JWT_SECRET`, `MOCK_*=false`, `ALLOWED_HOSTS` — *must fix*
- [ ] **#3** Enum allowlists for resident fields + `doc_type`; bound budgets; validate prebooked phone — *should fix*
- [ ] **#4** Normalize cross-account `403` → `404` — *post-MVP*
- [ ] **#5** Shorten JWT lifetime / add revocation — *post-MVP*
- [ ] **#6** Remove CSP `'unsafe-inline'` after React/self-hosting migration — *post-MVP*
- [ ] **#7** Add explicit CORS allowlist *only* if the frontend moves off-origin — *decision pending*
- [ ] Run `pip-audit` + a dynamic scan before go-live
