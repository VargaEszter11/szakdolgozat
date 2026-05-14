# Thesis: Travel Tracking and Planning Web Application

BSc in Computer Science Engineering

## What it is for

The application is for people who travel often and want to keep **visited places** and **planned trips** in one place: browse past trips on a map or in a list, add new places, plan future routes, and use optional AI-assisted planning.

## Main features

- **Visited places**: Table and map views; add locations with details.
- **Plan new trip**: Build a route from visited places, new destinations, or random suggestions; planning can use an LLM (see configuration below).
- **Planned trips**: List of saved plans; open a trip for details, or **edit** it in a modal (title, start city, trip dates, and per-stop fields). When you change dates on the **first** or **last** stop, the trip-level start and end dates update to stay consistent (first stop drives the trip start, last stop drives the trip end). Removing a stop re-chains following stops’ dates where applicable.
- **Authentication**: Login and registration (including Google OAuth when configured).
- **Profile**: Edit profile, session check, travel statistics.
- **Settings**: Theme and language.

## Technologies

| Layer    | Stack                          |
|----------|--------------------------------|
| Frontend | HTML, CSS, JavaScript          |
| Backend  | Python, FastAPI                |
| Database | PostgreSQL (via SQLAlchemy)    |

External integrations (optional, via environment variables) include geocoding (Nominatim), Amadeus travel APIs, LLM providers (e.g. DeepSeek or local Ollama), and Google sign-in. See `.env.example` for variable names and short comments.

## Prerequisites

- Python 3.10+ (recommended)
- PostgreSQL with a database created for the app (default name in `.env.example`: `szakdolgozat`)
- A copy of `.env` in the project root (copy from `.env.example` and fill in values you need)

## Installation

From the project root:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Create the database and user if needed, then set `DB_*` (and any other keys) in `.env`.

## Running the application

**Manual start** (from the `backend` folder, with dependencies installed and `PYTHONPATH`/working directory set so `main:app` resolves):

```bat
cd backend
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Then open `http://localhost:8000` in a browser.

## Project layout (short)

- `backend/` — FastAPI app (`main.py`), database models, trip planning logic
- `frontend/` — static pages, scripts, and styles served by the backend
- `requirements.txt` — Python dependencies
- `start.bat` — local launch helper for Windows
