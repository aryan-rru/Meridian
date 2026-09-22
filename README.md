<div align="center">

# 🛡️ meridian

**A unified GRC workspace — one control library, every framework.**

Maintain a single control library across ISO 27001, SOC 2, and NIST CSF.  
Then use it for crosswalks, gap analysis, risk scoring, remediation prioritisation, and evidence tracking — all in one place.

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/Frontend-React%20%2B%20TypeScript-61DAFB?style=flat-square&logo=react)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%2016-4169E1?style=flat-square&logo=postgresql)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Runs%20on-Docker-2496ED?style=flat-square&logo=docker)](https://www.docker.com/)

</div>

---

## What is meridian?

GRC (Governance, Risk & Compliance) teams waste enormous time maintaining separate control spreadsheets for each framework. meridian solves this with a **single source of truth** — write a control once and map it across every framework you operate under.

| Problem | meridian's answer |
|---|---|
| Duplicate controls across ISO 27001, SOC 2, NIST CSF | One shared control library with multi-framework mapping |
| "Which frameworks are we missing coverage for?" | Visual coverage heatmap and gap detail view |
| Risk register disconnected from controls | Risks linked directly to controls and their framework requirements |
| Evidence scattered across Google Drive and email | Centralised evidence library with Google Drive integration |
| "What should we fix first?" | Scored, ranked remediation queue |

---

## ✨ Features

- **Control Library** — Create, edit, and tag controls. Map each control to one or more framework requirements in a single action.
- **Framework Crosswalk** — Visual matrix showing how ISO 27001, SOC 2, and NIST CSF requirements overlap and share controls.
- **Coverage Heatmap** — Heat-mapped view of framework coverage with drill-down into gaps.
- **Risk Register** — Full risk lifecycle: inherent score → controls applied → residual score. Drill into any risk to trace it back through controls to framework requirements.
- **Risk Heatmap** — 5×5 inherent vs. residual heat map for at-a-glance portfolio risk posture.
- **Remediation Queue** — Auto-ranked list of the highest-impact controls to implement next, based on configurable scoring weights.
- **Evidence Library** — Upload files, link Google Drive documents, or paste URLs as evidence. Attach evidence to controls.
- **Import / Export** — Bulk-import controls and mappings from Excel; export your entire library or save to Google Drive.
- **Settings** — Configure scoring bands, risk labels, and remediation priority weights to match your organisation's methodology.

---

## 🖥️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite |
| Backend | Python 3.11, FastAPI, SQLAlchemy 2, Alembic |
| Database | PostgreSQL 16 (SQLite supported for local dev) |
| Auth | Google OAuth 2.0 + HTTP-only session cookies |
| Containerisation | Docker & Docker Compose |

---

## 🚀 Quick Start (Docker)

This is the recommended way to run meridian. You only need **Docker Desktop** and **Git**.

### 1 — Clone the repo

```bash
git clone https://github.com/your-username/meridian.git
cd meridian
```

### 2 — Create environment files

```powershell
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env
```

Open `backend/.env` and set the required values:

```dotenv
DATABASE_URL=postgresql+psycopg://meridian:meridian@db:5432/meridian

# Generate these — do not use the placeholder values
APP_SECRET=<random-secret>
TOKEN_ENCRYPTION_KEY=<fernet-key>

FRONTEND_URL=http://localhost:5173
BACKEND_URL=http://localhost:8000

# Enables one-click dev login without Google — disable in production
DEV_LOGIN_ENABLED=true
DEV_LOGIN_EMAIL=demo@meridian.local
SESSION_COOKIE_SECURE=false
```

Generate the secrets with Python (run once, paste the output above):

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

The `frontend/.env` only needs one line for local use:

```dotenv
VITE_API_BASE_URL=http://localhost:8000/api
```

### 3 — Start the stack

```bash
docker compose up -d --build
```

### 4 — Run migrations and seed sample data

```bash
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python -m app.seed
```

The seed command creates a **Sample Org** workspace pre-loaded with frameworks, controls, crosswalk mappings, risks, and example evidence so you can explore immediately.

### 5 — Open the app

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |

### 6 — Log in

Because `DEV_LOGIN_ENABLED=true`, just hit the **Dev Login** button on the login page — no Google account required for local exploration.

---

## 📁 Project Structure

```
meridian/
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── routers/      # API route handlers
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── schemas/      # Pydantic request/response schemas
│   │   ├── crud/         # Database operations
│   │   ├── services/     # Business logic
│   │   ├── seed.py       # Sample data seeder
│   │   └── main.py       # App entry point
│   ├── alembic/          # Database migrations
│   └── tests/            # pytest test suite
├── frontend/             # React + TypeScript SPA
│   └── src/
│       ├── pages/        # Route-level page components
│       ├── components/   # Shared UI components
│       ├── api/          # API client functions
│       └── types/        # TypeScript type definitions
├── docker-compose.yml
└── Makefile
```

---

## 🗺️ Application Routes

| Route | What you'll find there |
|---|---|
| `/` | Dashboard — posture summary and key metrics |
| `/controls` | Control library — create, edit, tag, map to frameworks |
| `/crosswalk` | Framework crosswalk matrix |
| `/coverage` | Coverage heatmap and gap drill-down |
| `/risks` | Risk register |
| `/risks/:id` | Risk detail — full traceability to controls and frameworks |
| `/risk-heatmap` | 5×5 inherent vs. residual heatmap |
| `/remediation` | Ranked remediation opportunities |
| `/evidence` | Evidence library — upload, link Drive, attach to controls |
| `/settings` | Scoring bands, labels, and remediation weights |
| `/import-export` | Excel import/export and Save to Drive |

---

## 🔑 Google Sign-in & Drive (Optional)

meridian works fully without Google. To enable Google sign-in and Google Drive evidence linking:

1. Create a Google Cloud project and enable the **Google Drive API**, **Google Picker API**, and optionally **Google Sheets API**.
2. Create an **OAuth 2.0 Web Application** credential:
   - Authorised JS origin: `http://localhost:5173`
   - Authorised redirect URI: `http://localhost:8000/api/auth/google/callback`
3. Add to `backend/.env`:
   ```dotenv
   GOOGLE_CLIENT_ID=<your-client-id>
   GOOGLE_CLIENT_SECRET=<your-client-secret>
   GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback
   ```
4. Add to `frontend/.env`:
   ```dotenv
   VITE_GOOGLE_CLIENT_ID=<your-client-id>
   VITE_GOOGLE_API_KEY=<your-picker-api-key>
   ```
5. Restart both containers: `docker compose restart backend frontend`

---

## 🧪 Running Tests

```bash
# All tests
docker compose run --rm backend pytest

# Backend only
docker compose run --rm backend pytest tests/

# Frontend only
docker compose run --rm frontend npm test
```

---

## 🛠️ Useful Commands

```bash
docker compose up -d --build     # Build and start everything
docker compose down              # Stop and remove containers
docker compose logs -f           # Follow logs
docker compose restart backend   # Restart a single service
docker compose run --rm backend alembic upgrade head   # Apply migrations
docker compose run --rm backend python -m app.seed     # Re-seed sample data
```

---

## ⚠️ Production Notes

- Set `DEV_LOGIN_ENABLED=false` — the dev login endpoint must never be live in production.
- Set `SESSION_COOKIE_SECURE=true` and serve over HTTPS.
- Store `APP_SECRET`, `TOKEN_ENCRYPTION_KEY`, and `GOOGLE_CLIENT_SECRET` in a secret manager — never commit them to Git.
- Set `FRONTEND_URL` to your exact production HTTPS origin; the backend derives its CORS allowlist from this value.

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.

---

<div align="center">
Built for security and compliance teams who are tired of spreadsheet chaos.
</div>
