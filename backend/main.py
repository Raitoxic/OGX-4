from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from backend.api import analytics, artifacts, auth, checkpoints, evaluation, ml, steps, stream, tasks
from backend.core.config import settings
from backend.database.init_db import init_db
from backend.execution.runner import recover_orphaned_running_tasks
from backend.streaming.broker import sse_broker
from ml.inference.predictor import supervision_predictor


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.validate_production_config()
    sse_broker.set_loop(asyncio.get_running_loop())
    init_db()
    recover_orphaned_running_tasks()
    supervision_predictor.reload()
    yield


app = FastAPI(
    title="VYRO-X API",
    description="Human Intelligence. Agent Evolution. Stateful, transparent, interruptible collaborative agent platform.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(_request: Request, _exc: SQLAlchemyError):
    return JSONResponse(
        status_code=500,
        content={"detail": "A database error occurred while processing your request. Please retry."},
    )


app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(steps.router)
app.include_router(checkpoints.router)
app.include_router(artifacts.router)
app.include_router(stream.router)
app.include_router(analytics.router)
app.include_router(evaluation.router)
app.include_router(ml.router)


@app.get("/api/health", tags=["System"])
def health_check() -> dict:
    mode, provider_name = settings.active_provider_info
    return {
        "status": "ok",
        "product": "VYRO-X",
        "tagline": "Human Intelligence. Agent Evolution.",
        "provider_mode": mode,
        "provider_name": provider_name,
        "ml_model_loaded": supervision_predictor.get_latest_report() is not None,
    }
