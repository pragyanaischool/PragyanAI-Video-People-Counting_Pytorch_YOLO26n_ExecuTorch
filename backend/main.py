
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings

from routers.health import router as health_router
from routers.jobs import router as jobs_router
from routers.downloads import router as downloads_router


# --------------------------------------------------
# LOGGING CONFIGURATION
# --------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("pragyanai")


# --------------------------------------------------
# CORS CONFIGURATION
# --------------------------------------------------

# Netlify production frontend
PRODUCTION_FRONTEND = "https://pragyan-yoloexecutorch.netlify.app"

# Local development frontend
LOCAL_FRONTENDS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# Read additional frontend URLs from Render environment variable.
# Example:
# FRONTEND_ORIGIN=https://pragyan-yoloexecutorch.netlify.app,https://example.netlify.app

ENV_FRONTENDS = [
    origin.strip().rstrip("/")
    for origin in settings.frontend_origin.split(",")
    if origin.strip()
]

ALLOWED_ORIGINS = list(
    set(
        [
            PRODUCTION_FRONTEND,
            *LOCAL_FRONTENDS,
            *ENV_FRONTENDS,
        ]
    )
)


# --------------------------------------------------
# APPLICATION LIFECYCLE
# --------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("------------------------------------------")
    logger.info("PragyanAI Video People Counting API")
    logger.info("------------------------------------------")

    logger.info("API startup successful")

    logger.info(
        "Configured model path: %s",
        settings.resolved_model_path,
    )

    logger.info(
        "Model exists: %s",
        settings.resolved_model_path.exists(),
    )

    logger.info(
        "Upload directory: %s",
        settings.upload_path,
    )

    logger.info(
        "Output directory: %s",
        settings.output_path,
    )

    logger.info(
        "Allowed frontend origins: %s",
        ALLOWED_ORIGINS,
    )

    logger.info(
        "YOLO model will be initialized lazily during inference."
    )

    yield

    logger.info("PragyanAI API shutting down")


# --------------------------------------------------
# FASTAPI APPLICATION
# --------------------------------------------------

app = FastAPI(
    title="PragyanAI Video People Counting API",
    description=(
        "YOLO26n ExecuTorch based video object detection, "
        "people tracking, counting and analytics."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# --------------------------------------------------
# CORS MIDDLEWARE
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# API ROUTERS
# --------------------------------------------------

app.include_router(health_router)

app.include_router(jobs_router)

app.include_router(downloads_router)


# --------------------------------------------------
# ROOT ENDPOINT
# --------------------------------------------------

@app.get("/")
async def root():

    return {
        "application": "PragyanAI Video People Counting",
        "version": "1.0.0",
        "status": "running",
        "technology": [
            "YOLO26n",
            "ExecuTorch",
            "ByteTrack",
            "OpenCV",
            "FastAPI",
            "React",
        ],
        "frontend": PRODUCTION_FRONTEND,
        "api_documentation": "/docs",
        "health_check": "/health",
        "model_info": "/api/model-info",
    }


# --------------------------------------------------
# APPLICATION STATUS
# --------------------------------------------------

@app.get("/api/status")
async def application_status():

    model_path = settings.resolved_model_path

    model_file = model_path / "model.pte"
    metadata_file = model_path / "metadata.yaml"

    return {
        "application": "PragyanAI Video People Counting",
        "api_status": "online",
        "model_directory": str(model_path),
        "model_directory_exists": model_path.exists(),
        "model_file_exists": model_file.exists(),
        "metadata_file_exists": metadata_file.exists(),
        "upload_directory": str(settings.upload_path),
        "output_directory": str(settings.output_path),
        "frontend_origin": PRODUCTION_FRONTEND,
    }
