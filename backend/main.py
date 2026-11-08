"""
PragyanAI Video People Counting API

Backend:
    FastAPI
    YOLO26n ExecuTorch
    OpenCV
    ByteTrack

Frontend:
    https://pragyan-yoloexecutorch.netlify.app

Backend:
    https://pragyanai-video-people-counting-pytorch.onrender.com
"""

import logging
import os
import time

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from config import settings

from routers.health import router as health_router
from routers.jobs import router as jobs_router
from routers.downloads import router as downloads_router

from services.inference import get_model, model_info


# ============================================================
# 1. LOGGING
# ============================================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("pragyanai.api")


# ============================================================
# 2. DEPLOYMENT URLS
# ============================================================

FRONTEND_URL = (
    "https://pragyan-yoloexecutorch.netlify.app"
)

BACKEND_URL = (
    "https://pragyanai-video-people-counting-pytorch.onrender.com"
)


# ============================================================
# 3. CORS CONFIGURATION
# ============================================================

DEFAULT_ORIGINS = [
    FRONTEND_URL,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

raw_origins = os.getenv("FRONTEND_ORIGIN", "")

if raw_origins.strip():

    allowed_origins = [
        origin.strip().rstrip("/")
        for origin in raw_origins.split(",")
        if origin.strip()
    ]

else:

    allowed_origins = DEFAULT_ORIGINS


# ============================================================
# 4. APPLICATION LIFECYCLE
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("=" * 70)

    logger.info(
        "Starting PragyanAI YOLO26n ExecuTorch Backend"
    )

    logger.info("=" * 70)

    logger.info(
        "Backend URL: %s",
        BACKEND_URL
    )

    logger.info(
        "Frontend URL: %s",
        FRONTEND_URL
    )

    logger.info(
        "Model directory: %s",
        settings.resolved_model_path
    )

    logger.info(
        "Upload directory: %s",
        settings.upload_path
    )

    logger.info(
        "Output directory: %s",
        settings.output_path
    )

    logger.info(
        "Allowed origins: %s",
        allowed_origins
    )

    # Create required directories

    settings.upload_path.mkdir(
        parents=True,
        exist_ok=True
    )

    settings.output_path.mkdir(
        parents=True,
        exist_ok=True
    )

    app.state.model_ready = False
    app.state.model_error = None

    # --------------------------------------------------------
    # LOAD YOLO26N EXECUTORCH MODEL
    # --------------------------------------------------------

    started = time.perf_counter()

    try:

        logger.info(
            "Loading YOLO26n ExecuTorch model..."
        )

        await run_in_threadpool(get_model)

        app.state.model_ready = True
        app.state.model_error = None

        logger.info(
            "YOLO26n model loaded successfully"
        )

    except Exception as exc:

        app.state.model_ready = False
        app.state.model_error = str(exc)

        logger.exception(
            "YOLO26n model initialization failed"
        )

        # Keep API running so /health and /docs remain available.

    elapsed = time.perf_counter() - started

    logger.info(
        "Model initialization completed in %.2f seconds",
        elapsed
    )

    logger.info(
        "Model ready: %s",
        app.state.model_ready
    )

    yield

    logger.info(
        "Shutting down PragyanAI backend"
    )


# ============================================================
# 5. FASTAPI APPLICATION
# ============================================================

app = FastAPI(

    title="PragyanAI Video People Counting API",

    description=(
        "YOLO26n ExecuTorch based video object detection, "
        "people counting, ByteTrack tracking and analytics."
    ),

    version="2.0.0",

    docs_url="/docs",

    redoc_url="/redoc",

    openapi_url="/openapi.json",

    lifespan=lifespan,
)


# ============================================================
# 6. CORS MIDDLEWARE
# ============================================================

app.add_middleware(

    CORSMiddleware,

    allow_origins=allowed_origins,

    allow_credentials=False,

    allow_methods=[
        "GET",
        "POST",
        "DELETE",
        "OPTIONS",
    ],

    allow_headers=["*"],

    expose_headers=[
        "Content-Disposition",
        "Content-Length",
    ],

    max_age=600,
)


# ============================================================
# 7. REQUEST LOGGING
# ============================================================

@app.middleware("http")
async def request_logging_middleware(
    request: Request,
    call_next
):

    started = time.perf_counter()

    try:

        response = await call_next(request)

        elapsed = time.perf_counter() - started

        logger.info(
            "%s %s -> %s (%.3fs)",

            request.method,

            request.url.path,

            response.status_code,

            elapsed,
        )

        return response

    except Exception:

        logger.exception(
            "Request failed: %s %s",

            request.method,

            request.url.path,
        )

        raise


# ============================================================
# 8. REGISTER API ROUTERS
# ============================================================

# Health:
# GET /health
# GET /api/model-info

app.include_router(
    health_router
)


# Video processing:
# POST /api/jobs
# GET /api/jobs/{job_id}
# GET /api/jobs/{job_id}/analytics

app.include_router(
    jobs_router
)


# Downloads:
# GET /api/jobs/{job_id}/video
# GET /api/jobs/{job_id}/csv
# GET /api/jobs/{job_id}/json
# DELETE /api/jobs/{job_id}

app.include_router(
    downloads_router
)


# ============================================================
# 9. ROOT ENDPOINT
# ============================================================

@app.get("/", tags=["system"])
async def root() -> dict[str, Any]:

    info = model_info()

    return {

        "service": (
            "PragyanAI Video People Counting API"
        ),

        "status": "running",

        "backend_url": BACKEND_URL,

        "frontend_url": FRONTEND_URL,

        "model": info.get(
            "model",
            "YOLO26n"
        ),

        "format": info.get(
            "format",
            "ExecuTorch"
        ),

        "model_files_present": info.get(
            "model_files_present",
            False
        ),

        "model_loaded": info.get(
            "loaded",
            False
        ),

        "docs": "/docs",

        "health": "/health",

        "model_info": "/api/model-info",

        "create_job": "POST /api/jobs",

        "job_status": "GET /api/jobs/{job_id}",

        "job_analytics": (
            "GET /api/jobs/{job_id}/analytics"
        ),

        "download_video": (
            "GET /api/jobs/{job_id}/video"
        ),

        "download_csv": (
            "GET /api/jobs/{job_id}/csv"
        ),

        "download_json": (
            "GET /api/jobs/{job_id}/json"
        ),
    }


# ============================================================
# 10. API INFORMATION
# ============================================================

@app.get("/api", tags=["system"])
async def api_root():

    return {

        "message": (
            "PragyanAI YOLO26n ExecuTorch API"
        ),

        "docs": "/docs",

        "health": "/health",

        "endpoints": [

            "GET /health",

            "GET /api/health",

            "GET /api/model-info",

            "POST /api/jobs",

            "GET /api/jobs/{job_id}",

            "GET /api/jobs/{job_id}/analytics",

            "GET /api/jobs/{job_id}/video",

            "GET /api/jobs/{job_id}/csv",

            "GET /api/jobs/{job_id}/json",

            "DELETE /api/jobs/{job_id}",
        ],
    }


# ============================================================
# 11. FRONTEND HEALTH-CHECK COMPATIBILITY
# ============================================================

# Your current frontend api.js calls /api/health.
# The health router exposes /health.
# This endpoint provides the required compatibility alias.

@app.get("/api/health", tags=["health"])
async def api_health_alias():

    info = model_info()

    ready = bool(
        info.get("loaded")
    )

    return {

        "status": (
            "healthy"
            if ready
            else "degraded"
        ),

        "backend_connected": True,

        "model_loaded": ready,

        "model_files_present": info.get(
            "model_files_present",
            False
        ),

        "model": info.get(
            "model",
            "YOLO26n"
        ),

        "format": info.get(
            "format",
            "ExecuTorch"
        ),

        "model_path": info.get(
            "model_path"
        ),

        "runtime": info.get(
            "runtime"
        ),

        "model_error": getattr(
            app.state,
            "model_error",
            None
        ),
    }


# ============================================================
# 12. GLOBAL ERROR HANDLER
# ============================================================

@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception
):

    logger.exception(
        "Unhandled application exception: %s",
        request.url.path
    )

    return JSONResponse(

        status_code=500,

        content={

            "detail": (
                "An unexpected backend error occurred."
            ),

            "path": request.url.path,
        }
    )


# ============================================================
# 13. LOCAL DEVELOPMENT
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(

        "main:app",

        host="0.0.0.0",

        port=int(
            os.getenv("PORT", "8000")
        ),

        reload=False,
    )
