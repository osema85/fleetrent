# FleetRent — Car Rental Agency Management

FleetRent is a web application for running a car rental agency. Staff use it to manage the fleet, customers, bookings, vehicle pickups and returns, payments, invoices and maintenance. Customers use it to book cars online.

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript (Vite), served by nginx |
| Backend | FastAPI (Python 3.12), SQLAlchemy 2, Alembic |
| Database | PostgreSQL 16 |
| Containers | Docker + Docker Compose |

- **How to use the app:** [docs/TUTORIAL.md](docs/TUTORIAL.md)
- **How the pieces fit together:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## Features

**Agency operations**
- **Dashboard:** today's pickups and returns, overdue rentals, bookings waiting for approval, fleet utilization, monthly revenue and a 6-month revenue trend.
- **Fleet:** cars with plate, VIN, category, transmission, fuel type, seats, mileage, daily rate and branch. Each car has a status: available, rented, maintenance or retired.
- **Branches:** multiple locations. A booking can be picked up at one branch and returned to another (one-way rental), and the car's location updates on return.
- **Customers:**
  - Driver records with license number, issuing country and expiry, plus ID document and notes.
  - Search, and rental history per customer.
  - A blacklist (managers only). Blacklisted customers can't book.
  - Deletion of customers with no rental history, for the right to erasure.
- **Reservations:**
  - Availability search and an instant price quote.
  - Extras: basic or full insurance, GPS, child seat, additional driver.
  - Statuses: pending → confirmed → active → completed, or cancelled / no-show.
- **Double-booking protection:** the app checks availability, and a PostgreSQL exclusion constraint makes overlapping bookings of the same car impossible, even when two requests arrive at the same moment.
- **Business rules:** minimum driver age (21), the license must be valid through the return date, and a rental can last at most 90 days.
- **Check-out (pickup):** records the odometer, fuel level and the car's condition.
- **Check-in (return):** the final bill is calculated automatically:
  - a late-return fee, after a 60-minute grace period
  - extra mileage beyond 300 km/day
  - missing fuel or battery charge
  - damage fees
  - tax
- **Payments:** payments, refunds, deposits received and deposits returned, by cash, card or bank transfer. Each booking shows its balance, and refunds can't exceed what was paid.
- **Invoices:** printable, and can be saved as PDF from the browser's print dialog.
- **Maintenance:** schedule → start (car becomes unavailable) → complete (car available again, mileage updated). Records cost and garage.
- **Users & roles:** `admin`, `manager`, `agent` and `customer`, each with least-privilege permissions.
- **Audit log:** records every login, failed login, change and money movement, with the user and IP address.

**Customer portal**
- Self-registration, with an option to turn it off.
- Book online with live pricing. Online bookings wait for staff confirmation.
- View your own reservations and invoices, cancel before pickup, and update your profile and driver license.

**In-app help** is available on the *Help* page, with content tailored to each role.

---

## Quick start

Requirements: **Docker** (with Compose v2) and **openssl**.

```bash
# 1. Generate your private .env with strong random secrets (prints the admin password once)
./scripts/generate-env.sh you@your-agency.com

# 2. Build and start everything
docker compose up -d --build

# 3. Open the app (accept the self-signed certificate warning the first time)
#    https://localhost:8443
```

Log in with the admin email and password printed in step 1. **Change that password right away** under *My profile*.

Demo data (2 branches, 9 cars, 2 customers) is loaded when `SEED_DEMO_DATA=true`, which is the default in `.env.example`. Set it to `false` for a real deployment.

> **Linux tip:** if `docker` says *permission denied*, either run the commands with `sudo`, or add yourself to the docker group with `sudo usermod -aG docker $USER`, then log out and back in.

### Everyday commands

```bash
docker compose ps                      # container status / health
docker compose logs -f backend         # API logs
docker compose down                    # stop (data is kept)
docker compose up -d --build           # rebuild after code changes
docker compose down -v                 # stop AND DELETE all data (database, certificates)
```

---

## Project structure

```
.
├── docker-compose.yml        # 3 services: db, backend, frontend (+ networks, volumes)
├── .env.example              # template of every setting (no secrets)
├── scripts/generate-env.sh   # creates the private .env with random secrets
├── backend/                  # FastAPI application
│   ├── app/
│   │   ├── main.py           # app setup, middleware, error handlers
│   │   ├── core/             # settings (env vars) + security (hashing, JWT, password policy)
│   │   ├── db/               # SQLAlchemy engine/session + base classes
│   │   ├── models/           # database tables
│   │   ├── schemas/          # Pydantic request/response validation
│   │   ├── services/         # pricing, billing, audit logging
│   │   ├── api/deps.py       # authentication, role checks, CSRF check
│   │   ├── api/routes/       # one file per resource (auth, cars, reservations, ...)
│   │   └── initial_data.py   # creates the first admin + optional demo data
│   ├── alembic/              # database migrations
│   ├── tests/                # unit tests (pricing, security)
│   ├── entrypoint.sh         # migrate → bootstrap → start uvicorn
│   └── Dockerfile
├── frontend/                 # React application
│   ├── src/
│   │   ├── api/              # fetch client (token handling) + TypeScript types
│   │   ├── auth/             # login state (AuthContext)
│   │   ├── components/       # layout, guards, UI building blocks
│   │   └── pages/            # one file per screen
│   ├── nginx/                # nginx config: TLS, security headers, rate limits, proxy
│   └── Dockerfile            # build with Node → serve with unprivileged nginx
└── docs/
    ├── TUTORIAL.md           # how to use the app, step by step
    └── ARCHITECTURE.md       # how all the technologies work together
```

---

## Configuration

All settings are environment variables in `.env`. That file is **gitignored and never committed**. Every variable is documented in [`.env.example`](.env.example). The most important ones:

| Variable | Purpose |
|---|---|
| `POSTGRES_PASSWORD`, `SECRET_KEY` | Generated secrets. The API refuses to start if they are missing, too short, or still `CHANGE_ME`. |
| `FIRST_ADMIN_EMAIL`, `FIRST_ADMIN_PASSWORD` | The first admin account, created only when no admin exists yet. |
| `PUBLIC_HOSTNAME`, `ALLOWED_HOSTS` | The domain users type in the browser. Requests for any other host are rejected. |
| `HTTP_PORT`, `HTTPS_PORT` | Ports published on the host (default 8080 / 8443). |
| `ENVIRONMENT` | `production` hides the API docs. `development` exposes them at `/api/docs`. |
| `ALLOW_SELF_REGISTRATION` | Whether customers can create accounts online. |
| `CURRENCY`, `TAX_RATE`, `COMPANY_NAME` | Shown on quotes and invoices. |
| `MAX_FAILED_LOGINS`, `LOCKOUT_MINUTES` | Brute-force lockout policy. |

Prices for extras, deposits and fees are in [backend/app/services/pricing.py](backend/app/services/pricing.py). Grace period and allowances are in [backend/app/core/config.py](backend/app/core/config.py).

> Changing `POSTGRES_PASSWORD` after the first start doesn't change the existing database user's password. Either change the password inside Postgres too, or reset the data with `docker compose down -v`.

---

## Security

The security measures, layer by layer:

| Area | Measures |
|---|---|
| **Secrets** | Kept only in the gitignored `.env` (mode 600), generated randomly. `.dockerignore` keeps them out of images. The app refuses to start with placeholder or weak secrets. |
| **Transport** | HTTPS only: HTTP redirects to HTTPS. TLS 1.2/1.3 only, HSTS, no session tickets. A self-signed certificate is generated on first run; replace it with a real one for production (see below). |
| **Passwords** | Argon2id hashing. Policy: 12+ characters with upper and lower case, a digit and a symbol, and the password can't contain the email name. Hashes are upgraded automatically when parameters change. |
| **Login** | One generic error message, and the same response time whether or not the account exists (no user enumeration). The account locks after 5 failures. nginx limits login/register to 10 requests per minute per IP. |
| **Sessions** | Access token: a JWT that lives 15 minutes, held **only in browser memory**. Issuer, audience, algorithm and token type are all checked. Refresh token: random, **httpOnly + Secure + SameSite=Strict** cookie limited to `/api/auth`, stored **hashed** and **rotated** on every use. Reusing an old refresh token revokes the whole session family. A password change, role change or deactivation logs the user out everywhere. |
| **CSRF** | Cookie endpoints require a custom header plus an Origin check, on top of the SameSite=Strict cookie. |
| **Authorization** | Role checks on **every** API endpoint (server side). Customers can only reach their own data (ownership checks on every reservation, invoice and payment lookup). Random UUID identifiers. |
| **Input** | Strict Pydantic validation with unknown fields rejected (prevents mass assignment), length limits and formats. The ORM's parameterized queries prevent SQL injection. Request bodies are capped at 1 MB. |
| **Browser** | Strict Content-Security-Policy (no inline scripts, no third-party sources), X-Frame-Options DENY, nosniff, no-referrer, Permissions-Policy, COOP/CORP. React escapes all output. The API sends `Cache-Control: no-store`. |
| **Errors** | No stack traces or submitted values in error responses. Details are logged server-side only. |
| **Containers** | Every service runs as non-root with all Linux capabilities dropped (the database keeps only the 5 it needs to start) and `no-new-privileges`. The API runs on a read-only filesystem. Memory and process limits are set. |
| **Network** | Only nginx publishes ports. The database is on an **internal** Docker network with no route to the outside or the host. The API sits behind nginx and only trusts nginx's forwarded IP. |
| **Data integrity** | DB constraints: no overlapping bookings, positive payments, valid periods. Row locks during check-out and check-in. |
| **Accountability** | The audit log records logins, failures, lockouts, token-reuse alerts, changes and payments. |
| **Dependencies** | All versions pinned. `npm audit` reports 0 vulnerabilities in shipped frontend dependencies. |

### Going to production — checklist

1. Point a domain at the server and set `PUBLIC_HOSTNAME` and `ALLOWED_HOSTS`. Optionally set `HTTP_PORT=80` and `HTTPS_PORT=443`.
2. Install a real certificate, for example from Let's Encrypt. Copy `fullchain.pem` → `server.crt` and `privkey.pem` → `server.key` into the `tls_certs` volume, or bind-mount a folder at `/etc/nginx/certs`, then restart `frontend`.
3. Set `SEED_DEMO_DATA=false` and `ENVIRONMENT=production`.
4. Enable a host firewall that allows only ports 80, 443 and SSH.
5. Set up encrypted, off-site database backups (see below) and test a restore.
6. Keep images updated: `docker compose pull && docker compose up -d --build`.

---

## Backups

```bash
# Backup (compressed, includes all data)
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > backup-$(date +%F).dump

# Restore into a running stack
docker compose exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists' < backup-YYYY-MM-DD.dump
```

`*.dump` files are gitignored. Store backups encrypted, because they contain personal data.

---

## Development

**Backend tests** (unit tests for pricing and security; no database needed):

```bash
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt pytest
pytest -q
```

**Frontend with hot reload:** run the stack with `docker compose up`, or run the API locally on port 8000, then:

```bash
cd frontend
npm ci
npm run dev        # http://localhost:5173 — /api is proxied to localhost:8000
```

For the local dev server, set `COOKIE_SECURE=false` and add `localhost` to `ALLOWED_HOSTS`, because the dev server uses plain HTTP.

**Database changes:** edit the models in `backend/app/models/`, then create a migration and review it before committing:

```bash
docker compose exec backend alembic revision --autogenerate -m "describe change"
```

The backend container's filesystem is read-only. In practice, run the command above in a local venv that points at the database, or temporarily remove `read_only: true` while you generate the migration.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Set POSTGRES_PASSWORD in .env` | You haven't created `.env` yet. Run `./scripts/generate-env.sh`. |
| Backend keeps restarting | Check `docker compose logs backend`. Usually a secret is too short or still `CHANGE_ME`. |
| Browser warns about the certificate | Expected with the self-signed certificate. Use a real certificate in production. |
| `400 Invalid host header` | Add the hostname you use to `ALLOWED_HOSTS`. |
| `429 Too many requests` | The rate limit was hit. Wait a minute. |
| Can't log in after several attempts | The account is locked for 15 minutes, or an admin can unlock it under *Users*. |
| Logged out after changing your password | Intended: every session is revoked. |
