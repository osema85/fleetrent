# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

FleetRent is a car rental agency management app: React 18 + TypeScript (Vite) frontend served by nginx, FastAPI (Python 3.12) backend with SQLAlchemy 2 + Alembic, PostgreSQL 16, all run via Docker Compose. `README.md` covers features/config/security; `docs/ARCHITECTURE.md` covers request flow and auth in depth.

## Commands

Full stack (requires a `.env`; create it once with `./scripts/generate-env.sh admin@example.com` — it refuses to overwrite an existing one):

```bash
docker compose up -d --build        # build + start db, backend, frontend → https://localhost:8443
docker compose ps                   # health status
docker compose logs -f backend      # API logs
docker compose down -v              # stop AND wipe DB + certs
```

Backend tests (pure unit tests, no database — `tests/conftest.py` sets dummy env vars so `Settings` loads):

```bash
cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt pytest
pytest -q                                          # all
pytest tests/test_pricing.py::test_name -q         # single test
```

Frontend (no test suite or linter configured; `build` runs `tsc --noEmit` as the type check):

```bash
cd frontend && npm ci
npm run build      # type-check + production build
npm run dev        # http://localhost:5173, proxies /api → localhost:8000
```

For the Vite dev server against a local API, set `COOKIE_SECURE=false` and include `localhost` in `ALLOWED_HOSTS` (plain HTTP).

Migrations: `alembic revision --autogenerate -m "..."` from `backend/` in a venv pointed at the DB (the backend container is `read_only`). Migrations run automatically on container start via `backend/entrypoint.sh` (`alembic upgrade head` → `python -m app.initial_data` → uvicorn).

## Architecture

**Topology.** Only the nginx `frontend` container publishes ports; it terminates TLS, applies security headers / rate limits (`frontend/nginx/`), serves the built SPA, and proxies `/api/*` to `backend:8000`. The DB is on an `internal` Docker network reachable only by the backend. Page and API are same-origin, so no CORS is normally configured.

**Backend request pipeline** (`backend/app/`):
- `main.py` — TrustedHost middleware, security headers, error handlers that never echo input or stack traces; every router in `api/routes/` is mounted under `/api` via the loop at the bottom. A new route module must be added to that import list and loop.
- `api/deps.py` — the authorization primitives. Use the `Annotated` dependency types in route signatures: `DB`, `CurrentUser`, `StaffUser` (admin/manager/agent), `ManagerUser`, `AdminUser`. Customer-accessible endpoints take `CurrentUser` and must do an explicit ownership check (`is_staff(user)` or the record belongs to the user's customer). Cookie-based endpoints (refresh/logout) use `require_csrf`.
- `schemas/common.py` — request bodies inherit `InputModel` (`extra="forbid"`, rejects unknown fields); responses inherit `OutputModel` (`from_attributes`). Reuse the constrained types there (`Money`, `PositiveMoney`, `Mileage`, `Percent`, `Phone`, ...).
- `services/pricing.py` — all money math (quotes, deposits, final check-in charges: late fee, extra km, fuel, damage, tax). Grace period / allowances live in `core/config.py`. `services/billing.py` computes reservation balances from payments.
- `services/audit.py` — `audit.record(db, request, user, action, entity_type, entity_id, details)` adds an `AuditLog` row to the current transaction; call it before `db.commit()` in every mutating endpoint so the audit entry commits atomically with the change.
- `models/enums.py` — `StrEnum`s for roles and statuses, plus `STAFF_ROLES` / `MANAGER_ROLES`.

**Integrity is enforced in PostgreSQL, not just Python.** Migration `0001_initial.py` hand-writes a `btree_gist` exclusion constraint preventing overlapping pending/confirmed/active reservations for the same car, plus check constraints (positive payments, `end_at > start_at`). Autogenerate won't produce these, so review generated migrations. Check-out/check-in lock the car row (`SELECT ... FOR UPDATE`). Conflicts surface as `409`.

**Reservation lifecycle:** pending → confirmed → active (check-out creates a `Rental`, car → rented) → completed (check-in computes final charges, car → available at the return branch); or cancelled / no-show. Business rules: driver age ≥ 21, license valid through return date, max 90 days, blacklisted customers can't book.

**Auth model.** Access JWT (15 min) is held only in memory in the frontend (`src/api/client.ts`), never in storage. The refresh token is an httpOnly `SameSite=Strict` cookie scoped to `/api/auth`, stored hashed, rotated on every use; reuse revokes the whole family. On page load the SPA calls `/api/auth/refresh` to restore the session. Password/role/active changes revoke all sessions, and access tokens with `iat` before `password_changed_at` are rejected. All frontend requests send `X-Requested-With: fleetrent`.

**Frontend** (`frontend/src/`): `api/client.ts` is the only fetch wrapper (handles token, auto-refresh on 401 with a single shared in-flight refresh, error formatting); `api/types.ts` mirrors backend output schemas; `auth/AuthContext.tsx` holds login state; `components/RequireRole.tsx` guards routes. The UI makes no security decisions — the backend re-checks everything. Adding a screen = page in `pages/` + route in `App.tsx` + nav link in `components/Layout.tsx`. nginx CSP forbids inline scripts and third-party sources, so don't add CDN assets or inline `<script>`.

**Config.** All settings are env vars read by `core/config.py` (pydantic-settings) and documented in `.env.example`. The API refuses to start if `SECRET_KEY` / `POSTGRES_PASSWORD` are missing, short, or `CHANGE_ME`. `ENVIRONMENT=development` exposes `/api/docs`. Dependency versions are pinned exactly in `requirements.txt` and `package.json`.
