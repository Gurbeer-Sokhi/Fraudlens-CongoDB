"""FraudLens API — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from app.config import settings
from app.database import close_driver, verify_connection
from app.models.schemas import HealthResponse
from app.routes.api import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: verify DB. Shutdown: close pool."""
    db_ok = verify_connection()
    if not db_ok:
        logger.warning("CognoDB not reachable — API will return errors until connected")
    yield
    close_driver()


app = FastAPI(
    title="FraudLens API",
    description="Fraud detection system powered by CognoDB graph database",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/health", response_model=HealthResponse)
def health_check():
    db_status = "connected" if verify_connection() else "disconnected"
    return HealthResponse(
        status="ok" if db_status == "connected" else "degraded",
        database=db_status,
    )


@app.exception_handler(ServiceUnavailable)
@app.exception_handler(Neo4jError)
async def neo4j_exception_handler(request, exc):
    logger.error("Database error: %s", exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "Database unavailable. Check COGNO_URI and credentials."},
    )


# A deployment image includes the built React application, allowing one web
# service to serve both the UI and API. This mount is deliberately last so the
# API and health routes above retain precedence.
frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
