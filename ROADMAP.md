# RideCare Roadmap

What has shipped on `main`, and what comes next. Product overview: [README.md](README.md).

---

## Shipped

### Auth & security
- Register / login with JWT access tokens (httpOnly cookies)
- **Email verification** — SMTP magic link on register; login blocked until confirmed; resend endpoint
- Changing email resets verification, sends a new link, and clears sessions
- Refresh-token rotation in Redis; logout revokes sessions
- Password strength policy; profile + password change with session revoke **and cookie clear**
- Access-token blocklisting in Redis (`jti`) on logout / refresh; per-user revoke epoch on password change
- IP- and user-based rate limiting (user limiter pipelined with auth Redis reads)

### Vehicles & odometer
- Multi-vehicle CRUD with ownership checks
- Live odometer = `max(baseline, fuel max, service max)`
- Cursor-paginated vehicle list + garage **Load more**
- Baseline change recalculates stored fuel mileage
- `GET /vehicles/{id}/summary` — spend, mileage, recent fill-ups, next service, **service_reminder**, **document_reminders**
- `GET /vehicles/{id}/analytics` — totals, **cost-per-km (fuel + service)**, last-10 mileage trend, last-6 months fuel spend
- `GET /vehicles/compare` — side-by-side spend, mileage, and ₹/km across the garage

### Fuel & mileage
- Fill-up logging with server-side liters and km/L
- Timeline-aware odometer validation
- Full mileage recalculation on create / update / delete / baseline change
- Stable cursor pagination (date + id) + fuel tab **Load more**
- **CSV export** of full fuel history (`GET /fuel_logs/export`)

### Service history
- Service visits with tags, cost, and next-due fields
- `GET /service_logs/next` for reminders
- Cursor-paginated list + service tab **Load more**
- Partial PATCH validates next-service odometer against existing reading
- Reminder clears once a visit meets the due date or odometer
- **CSV export** of full service history (`GET /service_logs/export`)

### Documents
- Insurance / licence / RC vault via Supabase Storage
- Typed uploads (PDF / JPEG / PNG, 10 MB), signed download URLs
- Clear expiry date / notes on update
- Vehicle delete removes linked storage objects
- Document writes invalidate vehicle summary cache (reminder freshness)
- Cursor-paginated list + docs tab **Load more**; API returns `days_until` / `expiry_status`

### Maintenance guide
- Static JSON catalog (24 tasks) with in-memory cache
- Filterable API + `/maintenance` page (component / severity)

### Caching & platform
- Redis cache for vehicle list/detail, summary, analytics, and compare
- Write-through invalidation on fuel / service / vehicle / document writes
- Auth hot path: one Redis pipeline for rate limit + blocklist + revoke-epoch + user identity; warm requests skip the Postgres user lookup
- Identity cache invalidated on profile / password change
- Query-shaped **composite indexes** (`vehicle_id`/`owner_id` + sort columns) for list/pagination paths
- Alembic migrations, async SQLAlchemy, GitHub Actions CI (pytest)
- Deployed API (Render) + frontend (Vercel) with same-origin `/api` proxy for cookies
- Local Vite `/api` proxy to `127.0.0.1:8000` (same-origin cookies, no Windows `localhost` IPv6 delay)

### Frontend product surface
- Dark rider UI: auth (login · register · **check-email** · **verify-email**), garage, compare, vehicle detail (Fuel · Service · Docs · Analytics)
- Dashboard driven by the summary API
- **In-app reminders** on the dashboard — service soon/overdue + document expiry
- Settings (profile / password), error boundary, 404 page
- Recharts analytics: cost-per-km, summary cards, mileage trend, monthly fuel spend

---

## Next

In progress on `feature/reminder-emails`:

- **Email digests** for service soon/overdue and document expiry (SMTP; GitHub Actions daily cron → secured API endpoint)
- **Suggest next-due** from the maintenance catalog intervals when logging a service (UI + API; rider can override)

---

## Later

These are out of scope for now — not missing pieces of the current product.

- Push notifications for reminders
- Structured insurance fields (provider, number, coverage)
- Multi-rider / shared garage permissions
- AI assists: natural-language “when is my next service?”, fuel-price context
