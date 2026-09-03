<p align="center">
  <img src="frontend/public/ridecare-logo.png" alt="RideCare" width="180" />
</p>

<h1 align="center">RideCare</h1>

<p align="center">
  <strong>Fuel. Service. Documents. Guides. Analytics.<br/>One garage for every rider.</strong>
</p>

<p align="center">
  <a href="https://ride-care-jade.vercel.app"><strong>Live app</strong></a>
  ·
  <a href="https://ride-care.onrender.com/docs">API docs</a>
  ·
  <a href="ROADMAP.md">Roadmap</a>
</p>

<p align="center">
  A backend-first vehicle companion — FastAPI owns the mileage math,<br/>
  PostgreSQL holds the truth, and a dark React UI makes every kilometer count.
</p>

<p align="center">
  <a href="https://ride-care-jade.vercel.app"><img alt="Live" src="https://img.shields.io/badge/Live-App-black?style=flat-square&logo=vercel&logoColor=white" /></a>
  <a href="https://ride-care.onrender.com/docs"><img alt="API" src="https://img.shields.io/badge/API-OpenAPI-009688?style=flat-square&logo=fastapi&logoColor=white" /></a>
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" />
  <img alt="React" src="https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black" />
  <img alt="TypeScript" src="https://img.shields.io/badge/TypeScript-Strict-3178C6?style=flat-square&logo=typescript&logoColor=white" />
  <img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-Supabase-4169E1?style=flat-square&logo=postgresql&logoColor=white" />
  <img alt="Redis" src="https://img.shields.io/badge/Redis-Upstash-DC382D?style=flat-square&logo=redis&logoColor=white" />
  <img alt="CI" src="https://img.shields.io/badge/CI-GitHub%20Actions-2088FF?style=flat-square&logo=githubactions&logoColor=white" />
</p>

---

## Why RideCare

Most garage apps are thin CRUD. RideCare keeps **truth on the server**:

| Capability | What the API owns |
|------------|-------------------|
| Mileage math | Liters + km/L from cost, price/L, and odometer deltas — recalculated on every fill-up edit/delete **and** baseline change |
| Live odometer | `max(baseline, fuel, service)` so garage and dashboard never lie |
| Dashboard aggregates | `GET /vehicles/{id}/summary` scans **all** logs — plus `service_reminder` and `document_reminders` for in-app alerts |
| Charts | `GET /vehicles/{id}/analytics` — cost-per-km (fuel + service), trend series, monthly fuel spend |
| Compare | `GET /vehicles/compare` — side-by-side spend, mileage, and ₹/km across the garage |
| Scale | Stable cursor pagination (`date`/`created_at` + `id`) — same-day rows never skip |
| Speed | Redis cache with write-through invalidation on fuel, service, vehicle, and document writes; auth identity cache so warm requests skip the user `SELECT` |
| Auth | httpOnly cookie JWT + refresh rotation, **email verification** (SMTP magic link), access-token blocklist (`jti`) + revoke-epoch on password change, pipelined rate limits |
| Docs | Typed vault uploads with signed URLs — never public blobs; vehicle delete cleans storage |
| Guidelines | File-backed maintenance catalog (in-memory), filterable without a DB table |

The frontend stays thin: sheets, charts, and **Load more** lists over a clear REST API.

---

## Product tour

### Dashboard — status at a glance

Multi-bike picker, live odometer, average mileage, next-service countdown, **in-app reminders** (service due + document expiry), this-month spend, and month-over-month mileage change — all from the summary API. Charts live on the vehicle Analytics tab.

![RideCare dashboard](docs/screenshots/01-dashboard.png)

### Garage — every machine in one place

Add, edit, and open bikes. Registration, year, and live kilometers on each card. **Load more** when the fleet grows.

![Garage](docs/screenshots/02-garage.png)

### Fuel — mileage as the headline

Chronological fill-ups with date, odometer, liters, and cost. km/L is calculated server-side. **Load more** via cursor pages. **Export CSV** of the full history.

![Fuel logs](docs/screenshots/03-fuel-logs.png)

![Log fuel sheet](docs/screenshots/04-log-fuel.png)

### Service — history + next due

Cost, odometer, tagged jobs, and next service date / km reminders. Cursor-paginated list with **Load more**. **Export CSV** of the full history.

![Service logs](docs/screenshots/05-service-logs.png)

![Log service sheet](docs/screenshots/06-log-service.png)

### Docs — digital vault

Insurance, driving licence, and RC — PDF / JPEG / PNG, max 10 MB, signed downloads. Expiry and notes can be cleared on edit.

![Documents vault](docs/screenshots/07-documents.png)

![Upload document](docs/screenshots/08-upload-document.png)

### Analytics — spend and mileage charts

Per-vehicle Analytics tab (Recharts): **cost-per-km (fuel + service)**, summary cards, last-10 mileage trend, last-6 months fuel spend — from `GET /vehicles/{id}/analytics`.

![Analytics](docs/screenshots/09-analytics.png)

### Compare — fleet side by side

`GET /vehicles/compare` puts every bike next to each other: km driven, average km/L, fuel vs service spend, and ₹/km. Best mileage and lowest cost-per-km are called out.

![Compare](docs/screenshots/10-compare.png)

### Maintenance guide — interval tips

Oil, chain, brakes, tyres, CVT… filterable by component and severity from a static JSON catalog.

![Maintenance guide](docs/screenshots/11-maintenance-guide.png)

### Settings — profile and password

Update name/email or change password (revokes all sessions and clears auth cookies). Changing email resets verification and sends a new confirmation link.

![Settings](docs/screenshots/12-settings.png)

---

## Architecture

```
┌─────────────────┐   httpOnly JWT + refresh   ┌─────────────────────────────┐
│  React + Vite   │ ◄────────────────────────► │  FastAPI (async)            │
│  TanStack Query │        REST / JSON         │  routes · schemas · utils   │
│  Zustand hint   │                            └──────────────┬──────────────┘
└─────────────────┘                                           │
         same-origin /api (Vercel) → Render                   │
                    ┌─────────────────────────────────────────┼─────────────────┐
                    │                     │                   │                 │
                    ▼                     ▼                   ▼                 ▼
             PostgreSQL              Redis               Supabase          Alembic
             (Supabase)            (Upstash)             Storage          migrations
             users · vehicles      refresh tokens        document files
             fuel · service        access blocklist
             documents             revoke-epoch
                                   rate limits
                                   email verify tokens
                                   user identity cache
                                   response cache
```

Every fuel / service / document row is scoped by `vehicle_id`; vehicles by `owner_id`. Routes verify ownership before mutations (missing or foreign → **404**).

---

## Tech stack

| Layer | Choices |
|-------|---------|
| API | FastAPI, Pydantic v2, SQLAlchemy 2 (async), Alembic |
| Data | PostgreSQL (Supabase), Redis (Upstash) |
| Files | Supabase Storage + signed URLs |
| Auth | bcrypt, JWT access + refresh rotation (httpOnly cookies), SMTP verification email |
| UI | React 19, TypeScript, Vite 8, Tailwind CSS v4, shadcn/ui, Recharts |
| Client | TanStack Query, Zustand, Axios, Zod + React Hook Form |
| Hosting | Frontend on **Vercel** (`/api` proxy) · API on **Render** |
| Quality | pytest on GitHub Actions · oxlint locally |

---

## API map

Live docs: **[https://ride-care.onrender.com/docs](https://ride-care.onrender.com/docs)** · local: [http://localhost:8000/docs](http://localhost:8000/docs)

| Module | Surface | Highlights |
|--------|---------|------------|
| **Auth** | `register` · `verify-email` · `resend-verification` · `login` · `token` · `refresh` · `logout` | httpOnly cookies; SMTP magic-link verification before login; access JWT blocklist on logout/refresh; one Redis pipeline for rate limit + blocklist + identity; Swagger OAuth2 form still returns bearer body |
| **Users** | `GET/PATCH /users/me` · password change | Session revoke + access revoke-epoch + identity-cache refresh + cookie clear; email change re-triggers verification |
| **Vehicles** | CRUD · `…/summary` · `…/analytics` · `GET /vehicles/compare` | Live odometer; cost-per-km (fuel + service); garage compare |
| **Fuel** | CRUD `/fuel_logs/?vehicle_id=` · `GET …/export` | Liters + km/L; cascade recalc; CSV of full history |
| **Service** | CRUD · `suggest-next-due` · `GET …/next` · `GET …/export` | Catalog-based next-due suggestions; CSV of full history |
| **Documents** | Multipart CRUD · cursor list | Type enum, 10 MB, signed URLs; clear expiry/notes; expiry status from API |
| **Guidelines** | `/maintenance-guidelines/` + filters | JSON file + in-memory cache |
| **Internal** | `POST /internal/reminder-digests` | Cron-secured daily email digests (service + document reminders) |

List responses use a shared cursor page (stable across same-day rows):

```json
{
  "items": [],
  "next_cursor": null,
  "has_more": false,
  "total": 36
}
```

---

## Explore the code

| Start here | What you’ll see |
|------------|-----------------|
| [`backend/app/routes/vehicles.py`](backend/app/routes/vehicles.py) | Summary, analytics, compare, live odometer, Redis-cached reads |
| [`backend/app/utils/analytics.py`](backend/app/utils/analytics.py) | Cost-per-km (fuel + service) over km since baseline |
| [`backend/app/routes/fuel_logs.py`](backend/app/routes/fuel_logs.py) | Mileage recalculation + odometer rules |
| [`backend/app/utils/fuel_mileage.py`](backend/app/utils/fuel_mileage.py) | Shared timeline recalc (fuel writes + baseline updates) |
| [`backend/app/utils/cache.py`](backend/app/utils/cache.py) | Cache helpers, `CACHE_MISS` sentinel, vehicle + user-identity keys |
| [`backend/app/utils/auth_context.py`](backend/app/utils/auth_context.py) | Shared auth hot-path state (rate-limit pipeline → `get_current_user`) |
| [`backend/app/utils/pagination.py`](backend/app/utils/pagination.py) | Composite cursor paginator |
| [`backend/app/utils/email.py`](backend/app/utils/email.py) | SMTP transactional mail (verification links) |
| [`backend/app/utils/email_verification_service.py`](backend/app/utils/email_verification_service.py) | Redis one-time verification tokens |
| [`backend/app/utils/reminders.py`](backend/app/utils/reminders.py) | Service soon/overdue + document expiry rules |
| [`backend/data/maintenance_guidelines.json`](backend/data/maintenance_guidelines.json) | Guideline catalog |
| [`backend/tests/`](backend/tests/) | Auth (incl. verify/resend), users, CRUD, pagination, cache, summary, analytics, compare, export, documents, rate limits, guidelines |
| [`frontend/src/features/`](frontend/src/features/) | Domain modules (hooks · forms · charts) |
| [`frontend/src/pages/`](frontend/src/pages/) | Auth (login · register · check-email · verify-email), dashboard, garage, compare, detail, settings, maintenance |
| [`ROADMAP.md`](ROADMAP.md) | Shipped vs next |

```
RideCare/
├── backend/          # FastAPI · models · routes · Redis · tests
├── frontend/         # React app (api · features · pages)
├── docs/screenshots/ # Product captures
└── .github/workflows/
```

---

## Quick start

### Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # DATABASE_URL, JWT, Supabase, Redis, SMTP, FRONTEND_URL, ALLOWED_ORIGINS
alembic upgrade head
uvicorn main:app --reload
```

- Health: [http://localhost:8000/health](http://localhost:8000/health)
- OpenAPI: [http://localhost:8000/docs](http://localhost:8000/docs)

### Frontend

```bash
cd frontend
npm install
cp .env.example .env   # VITE_API_URL=/api (Vite proxies to 127.0.0.1:8000)
npm run dev
```

App: [http://localhost:5173](http://localhost:5173)

Production builds always call **`/api`** (same origin). Local Vite proxies `/api` to `127.0.0.1:8000` so cookies stay first-party and Windows does not pay the `localhost` IPv6 delay. Vercel rewrites `/api/*` to the Render API.

### Tests

Tests use a **separate** Supabase project via `backend/.env.test` (never commit it).

```bash
cd backend
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

---

## Environment

| File | Role | Commit? |
|------|------|---------|
| `backend/.env` | Dev DB, JWT, Supabase, Redis, SMTP | No |
| `backend/.env.test` | Pytest isolation | No |
| `backend/.env.example` | Required keys template | Yes |
| `frontend/.env` | Local `VITE_API_URL` | No |
| `frontend/.env.example` / `.env.production` | API URL templates | Yes |

---

## What’s included

Auth (email verification via SMTP) · multi-vehicle garage with **Load more** · server-side mileage (including baseline recalc) · service history with **Load more** · **CSV export** of fuel and service history · document vault with **Load more** · summary dashboard with **in-app reminders** · **cost-per-km (fuel + service)** · **garage compare** · analytics charts · maintenance guide · stable cursor pagination · query-shaped composite indexes · Redis caching with write-through invalidation · pipelined auth (rate limit + identity cache) · access-token blocklisting · CI + production deploy

What’s next → [ROADMAP.md](ROADMAP.md)

---

<p align="center">
  <sub>Built for riders who want numbers they can trust — and an API recruiters can read.</sub>
</p>
