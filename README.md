# Thesis: Travel Tracking and Planning Web Application

BSc in Computer Science Engineering

## What it is

A web app for frequent travellers to keep **visited places** and **planned trips** in one place: log past trips (list + map), plan future routes (optionally with an LLM), and share itineraries.

## Features

- **Visited places** — list and map views; add places with details and optional photos
- **Plan new trip** — routes from visited places, unvisited destinations, or random suggestions; LLM via DeepSeek
- **Planned trips** — saved plans with detail/edit modals, booking status, stop management, and date consistency when editing first/last stops
- **Trip sharing** — public read-only link (`/share`) and in-app invitations to other users
- **Auth** — register/login, Google OAuth (optional), password reset by email
- **Profile & settings** — profile editing, travel stats, theme (light/dark/auto), language (EN / HU / DE)
- **Admin** — protected data export/import between environments (optional `ADMIN_SECRET`)

## Stack

| Layer    | Stack |
|----------|--------|
| Frontend | HTML, CSS, JavaScript (static; nginx in Docker) |
| Backend  | Python 3.12, FastAPI, SQLAlchemy |
| Database | PostgreSQL |
| Deploy   | Docker Compose (`db` + `backend` + `frontend`) |

Optional integrations (see `.env.example`): Nominatim geocoding, DeepSeek, Google OAuth, AirLabs, SMTP.

## Quick start (Docker)

**Prerequisites:** Docker Desktop (or Docker Engine + Compose), and a `.env` file in the project root.

```bat
copy .env.example .env
docker compose up --build -d
```

Open **http://localhost** (frontend on port 80; API proxied to the backend).

Pretty URLs (via nginx): `/`, `/places`, `/places/map`, `/places/new`, `/trips`, `/trips/new`, `/share`, `/settings`, `/settings/profile`, `/profile`, `/login`, `/register`, `/reset-password`, `/admin`, `/admin/feedback`.

Local Compose overrides (`docker-compose.override.yaml`) also publish Postgres on host port **5433**.

Stop:

```bat
docker compose down
```

Set `PUBLIC_BASE_URL` in `.env` when the app is behind a reverse proxy so email links (password reset) use your public domain.

## Local development (without Docker frontend)

**Prerequisites:** Python 3.10+, a running PostgreSQL database, `.env` configured (`DB_*`, etc.).

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Start the API (serves/uploads; for full UI prefer Docker frontend, or open static files carefully with API base URL set):

```bat
cd backend
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## Configuration

Copy `.env.example` → `.env` and fill what you need. Important groups:

| Area | Variables |
|------|-----------|
| Database | `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME` |
| Google login | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` |
| Trip LLM | `DEEPSEEK_API_KEY`, optional `DEEPSEEK_API_BASE`, `DEEPSEEK_MODEL` |
| Geocoding | `NOMINATIM_USER_AGENT` (required by OSM policy) |
| Password reset email | `SMTP_*`, optionally `PUBLIC_BASE_URL` |
| Admin tools | `ADMIN_SECRET` |

## Tests

```bat
python -m pytest unit_tests --cov=backend --cov-report=term-missing
```

CI runs the same suite on push/PR via `.github/workflows/tests.yml`.

## Project layout

```
backend/           FastAPI app (routers, models, planners, scrapers)
frontend/          Static pages, scripts, styles
docker/            nginx config for the frontend container
unit_tests/        Backend unit tests
integration_tests/ Backend workflow tests
uploads/           User uploads (place images; volume in Docker)
docker-compose.yaml
.env.example
requirements.txt
```

## API overview

Routers are mounted under `/api` (auth, users, places, trips, stops, sharing, admin). Trip generation also uses `/generate_travel_plans/…`. Interactive docs when the backend is up: `/docs`.
