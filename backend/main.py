import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database.database import engine, Base
from routers import users, planned_trips, trip_stops, visited_places, auth, route_planner, trip_sharing, admin, feedback
from middleware.request_logging import RequestLoggingMiddleware
from utils.console_logging import attach_api_loggers_to_console


def startup_event():
    """Create database tables on application startup."""
    Base.metadata.create_all(bind=engine)
    # AirLabs route imports are intentionally manual. Do not call data importers here.
    from database.migrations import apply_startup_schema_patches

    apply_startup_schema_patches()
    from utils.place_image_upload import ensure_place_images_dir
    from utils.feedback_image_upload import ensure_feedback_images_dir

    ensure_place_images_dir()
    ensure_feedback_images_dir()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    startup_event()
    yield


app = FastAPI(
    title="Planventure API",
    description="API for travel planning and visited places tracking",
    version="1.0.0",
    lifespan=lifespan,
)

attach_api_loggers_to_console()

app.add_middleware(RequestLoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api", tags=["authentication"])
app.include_router(users.router, prefix="/api", tags=["users"])
app.include_router(planned_trips.router, prefix="/api", tags=["trips"])
app.include_router(trip_stops.router, prefix="/api", tags=["stops"])
app.include_router(visited_places.router, prefix="/api", tags=["places"])
app.include_router(route_planner.router, tags=["planner"])
app.include_router(trip_sharing.router, prefix="/api", tags=["sharing"])
app.include_router(admin.router, prefix="/api", tags=["admin"])
app.include_router(feedback.router, prefix="/api", tags=["feedback"])

_uploads_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads"))
os.makedirs(_uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=_uploads_dir), name="uploads")