
"""
PragyanAI - People Detection & Counting API

Backend:
    FastAPI
    YOLO11 TFLite
    ByteTrack
    OpenCV

Features:
    1. Backend health check
    2. Model initialization
    3. Video upload and validation
    4. People detection and tracking
    5. Processed video generation
    6. CSV and JSON analytics
    7. Output file management
"""

import os
import json
import uuid
import logging
import time

from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    HTTPException,
)

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from starlette.concurrency import run_in_threadpool

from services.video_processor import VideoProcessor

from utils.video_utils import (
    ALLOWED_EXTENSIONS,
    VideoValidationError,
    validate_video,
)


# =========================================================
# 1. LOGGING
# =========================================================

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format=(
        "%(asctime)s | %(levelname)s | "
        "%(name)s | %(message)s"
    ),
)

logger = logging.getLogger("pragyanai")


# =========================================================
# 2. PROJECT DIRECTORIES
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = Path(
    os.getenv(
        "MODEL_PATH",
        str(BASE_DIR / "models" / "yolo11n.tflite"),
    )
)

if not MODEL_PATH.is_absolute():
    MODEL_PATH = BASE_DIR / MODEL_PATH

UPLOAD_DIR = Path(
    os.getenv(
        "UPLOAD_DIR",
        "/tmp/pragyanai_uploads",
    )
)

OUTPUT_DIR = Path(
    os.getenv(
        "OUTPUT_DIR",
        "/tmp/pragyanai_outputs",
    )
)

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =========================================================
# 3. ENVIRONMENT CONFIGURATION
# =========================================================

# Supports multiple frontend origins separated by commas.
DEFAULT_FRONTENDS = (
    "https://tflite-objectdetection-peopleanalysis.netlify.app,"
    "https://pragyan-yoloexecutorch.netlify.app,"
    "http://localhost:5173,"
    "http://127.0.0.1:5173"
)

FRONTEND_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv(
        "FRONTEND_ORIGIN",
        DEFAULT_FRONTENDS,
    ).split(",")
    if origin.strip()
]

PUBLIC_API_URL = os.getenv(
    "PUBLIC_API_URL",
    "https://pragyanai-yolo-tf-lite-object-detction.onrender.com",
).rstrip("/")

MAX_UPLOAD_SIZE = int(
    os.getenv(
        "MAX_UPLOAD_SIZE",
        str(500 * 1024 * 1024),
    )
)

CHUNK_SIZE = 1024 * 1024


# =========================================================
# 4. APPLICATION STATE
# =========================================================

processor = None
model_loaded = False
model_error = None


# =========================================================
# 5. MODEL INITIALIZATION
# =========================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    global processor
    global model_loaded
    global model_error

    startup_started = time.perf_counter()

    logger.info("=" * 65)
    logger.info("Starting PragyanAI People Detection Backend")
    logger.info("=" * 65)

    logger.info("Model path: %s", MODEL_PATH)
    logger.info("Model exists: %s", MODEL_PATH.is_file())
    logger.info("Upload directory: %s", UPLOAD_DIR)
    logger.info("Output directory: %s", OUTPUT_DIR)
    logger.info("Allowed frontend origins: %s", FRONTEND_ORIGINS)

    try:

        if not MODEL_PATH.is_file():
            raise FileNotFoundError(
                f"YOLO model not found: {MODEL_PATH}"
            )

        logger.info("Loading YOLO11 TFLite model...")

        model_started = time.perf_counter()

        processor = await run_in_threadpool(
            VideoProcessor,
            str(MODEL_PATH),
        )

        model_loaded = True
        model_error = None

        app.state.processor = processor

        logger.info(
            "Model loaded successfully in %.2f seconds",
            time.perf_counter() - model_started,
        )

    except Exception as exc:

        processor = None
        model_loaded = False
        model_error = str(exc)

        app.state.processor = None

        logger.exception(
            "Model initialization failed"
        )

    logger.info(
        "Backend startup completed in %.2f seconds. Model loaded: %s",
        time.perf_counter() - startup_started,
        model_loaded,
    )

    yield

    logger.info("Shutting down PragyanAI backend")

    processor = None
    model_loaded = False


# =========================================================
# 6. FASTAPI APPLICATION
# =========================================================

app = FastAPI(
    title="PragyanAI People Detection & Counting API",
    description=(
        "YOLO11 TFLite based people detection, "
        "ByteTrack tracking and video analytics."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# =========================================================
# 7. CORS CONFIGURATION
# =========================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=FRONTEND_ORIGINS,

    allow_credentials=False,

    allow_methods=["*"],

    allow_headers=["*"],
)


# =========================================================
# 8. HTTP REQUEST LOGGING
# =========================================================

@app.middleware("http")
async def request_logging_middleware(request, call_next):

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


# =========================================================
# 9. STATIC OUTPUT DIRECTORY
# =========================================================

app.mount(
    "/outputs",
    StaticFiles(directory=str(OUTPUT_DIR)),
    name="outputs",
)


# =========================================================
# 10. HELPER FUNCTIONS
# =========================================================

def get_public_url(file_path):

    filename = Path(file_path).name

    return f"{PUBLIC_API_URL}/outputs/{filename}"


def get_current_processor():

    current_processor = getattr(
        app.state,
        "processor",
        None,
    )

    if current_processor is None:

        raise HTTPException(
            status_code=503,
            detail={
                "message": "YOLO model is not ready.",
                "model_loaded": False,
                "model_error": model_error,
            },
        )

    return current_processor


def cleanup_file(file_path):

    if not file_path:
        return

    try:

        path = Path(file_path)

        if path.exists() and path.is_file():
            path.unlink()

    except Exception:

        logger.exception(
            "Unable to delete temporary file: %s",
            file_path,
        )


def safe_filename(filename):

    original_name = Path(
        filename or "uploaded_video.mp4"
    ).name

    extension = Path(
        original_name
    ).suffix.lower()

    return f"{uuid.uuid4().hex}{extension}"


# =========================================================
# 11. ROOT ENDPOINT
# =========================================================

@app.get("/")
async def root():

    return {
        "application": "PragyanAI People Detection & Counting",
        "status": "running",
        "version": "1.0.0",
        "backend": "FastAPI",
        "detection_engine": "YOLO11 TFLite",
        "tracking_engine": "ByteTrack",
        "video_processing": "OpenCV",
        "model_loaded": model_loaded,
        "model_error": model_error,
        "docs": "/docs",
        "health": "/health",
    }


# =========================================================
# 12. HEALTH CHECK
# =========================================================

@app.get("/health")
async def health_check():

    return {
        "success": True,
        "status": (
            "healthy"
            if model_loaded
            else "degraded"
        ),
        "api": "running",
        "backend_connected": True,
        "model_loaded": model_loaded,
        "model_status": (
            "ready"
            if model_loaded
            else "not_ready"
        ),
        "model_name": "YOLO11 TFLite",
        "model_exists": MODEL_PATH.is_file(),
        "model_path": str(MODEL_PATH),
        "model_error": model_error,
        "tracking_engine": "ByteTrack",
        "video_processing": "OpenCV",
    }


# =========================================================
# 13. MODEL INFORMATION
# =========================================================

@app.get("/api/model-info")
async def model_info():

    return {
        "success": True,
        "model_name": "YOLO11n TFLite",
        "model_type": "Object Detection",
        "model_format": "TensorFlow Lite",
        "model_exists": MODEL_PATH.is_file(),
        "model_loaded": model_loaded,
        "model_status": (
            "ready"
            if model_loaded
            else "not_ready"
        ),
        "model_error": model_error,
        "classes": ["person"],
        "class_ids": [0],
        "tracking_engine": "ByteTrack",
        "video_processing": "OpenCV",
    }


# =========================================================
# 14. API INFORMATION
# =========================================================

@app.get("/api")
async def api_root():

    return {
        "success": True,
        "message": "PragyanAI People Detection API",
        "available_endpoints": [
            "/",
            "/health",
            "/api/model-info",
            "/api/process",
            "/api/outputs",
            "/outputs/{filename}",
        ],
    }


# =========================================================
# 15. VIDEO PROCESSING ENDPOINT
# =========================================================

@app.post("/api/process")
async def process_video(
    file: UploadFile = File(...),
    confidence: float = Form(0.35),
    frame_interval: int = Form(1),
):

    request_started = time.perf_counter()

    input_path = None
    job_id = uuid.uuid4().hex

    logger.info(
        "Video processing request received: %s",
        file.filename,
    )

    try:

        # ---------------------------------------------
        # A. CHECK MODEL
        # ---------------------------------------------

        current_processor = get_current_processor()

        # ---------------------------------------------
        # B. VALIDATE PARAMETERS
        # ---------------------------------------------

        if not 0 <= confidence <= 1:

            raise HTTPException(
                status_code=400,
                detail="Confidence must be between 0 and 1.",
            )

        if frame_interval < 1:

            raise HTTPException(
                status_code=400,
                detail="Frame interval must be at least 1.",
            )

        # ---------------------------------------------
        # C. VALIDATE FILE EXTENSION
        # ---------------------------------------------

        original_filename = (
            file.filename or "uploaded_video.mp4"
        )

        extension = Path(
            original_filename
        ).suffix.lower()

        if extension not in ALLOWED_EXTENSIONS:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Unsupported video format. "
                    "Supported formats: MP4, AVI, MOV, MKV, WEBM."
                ),
            )

        # ---------------------------------------------
        # D. GENERATE FILE PATHS
        # ---------------------------------------------

        input_filename = safe_filename(
            original_filename
        )

        input_path = UPLOAD_DIR / input_filename

        output_path = OUTPUT_DIR / f"{job_id}_processed.mp4"

        csv_path = OUTPUT_DIR / f"{job_id}_analytics.csv"

        json_path = OUTPUT_DIR / f"{job_id}_analytics.json"

        # ---------------------------------------------
        # E. SAVE UPLOADED VIDEO
        # ---------------------------------------------

        uploaded_size = 0

        with open(input_path, "wb") as destination:

            while True:

                chunk = await file.read(CHUNK_SIZE)

                if not chunk:
                    break

                uploaded_size += len(chunk)

                if uploaded_size > MAX_UPLOAD_SIZE:

                    raise HTTPException(
                        status_code=413,
                        detail="Video exceeds the maximum upload size.",
                    )

                destination.write(chunk)

        if uploaded_size == 0:

            raise HTTPException(
                status_code=400,
                detail="Uploaded video is empty.",
            )

        logger.info(
            "Video uploaded: %.2f MB",
            uploaded_size / (1024 * 1024),
        )

        # ---------------------------------------------
        # F. VALIDATE VIDEO
        # ---------------------------------------------

        try:

            video_info = await run_in_threadpool(
                validate_video,
                str(input_path),
            )

        except VideoValidationError as exc:

            raise HTTPException(
                status_code=400,
                detail=str(exc),
            )

        # ---------------------------------------------
        # G. PROCESS VIDEO
        # ---------------------------------------------

        logger.info(
            "Starting YOLO inference and ByteTrack tracking"
        )

        analytics_result = await run_in_threadpool(
            current_processor.process,
            str(input_path),
            str(output_path),
            confidence,
            frame_interval,
            str(csv_path),
        )

        # ---------------------------------------------
        # H. VERIFY OUTPUT
        # ---------------------------------------------

        if not output_path.is_file():

            raise RuntimeError(
                "Video processor did not generate output video."
            )

        if output_path.stat().st_size == 0:

            raise RuntimeError(
                "Generated output video is empty."
            )

        # ---------------------------------------------
        # I. PREPARE ANALYTICS JSON
        # ---------------------------------------------

        if not isinstance(analytics_result, dict):

            analytics_result = {
                "result": analytics_result
            }

        analytics_result["job_id"] = job_id

        analytics_result["video_info"] = video_info

        analytics_result["processing_settings"] = {
            "confidence": confidence,
            "frame_interval": frame_interval,
            "model": "YOLO11 TFLite",
            "tracker": "ByteTrack",
        }

        with open(
            json_path,
            "w",
            encoding="utf-8",
        ) as json_file:

            json.dump(
                analytics_result,
                json_file,
                indent=4,
                default=str,
            )

        # ---------------------------------------------
        # J. GENERATE OUTPUT URLS
        # ---------------------------------------------

        video_url = get_public_url(output_path)

        csv_url = (
            get_public_url(csv_path)
            if csv_path.is_file()
            else None
        )

        json_url = get_public_url(json_path)

        # ---------------------------------------------
        # K. BUILD RESPONSE
        # ---------------------------------------------

        response = {
            "success": True,

            "message": (
                "People detection and tracking completed successfully."
            ),

            "job_id": job_id,

            "video_url": video_url,

            "csv_url": csv_url,

            "json_url": json_url,

            "analytics": analytics_result,

            "summary": analytics_result,

            "video_info": video_info,

            "processing_settings": {
                "confidence": confidence,
                "frame_interval": frame_interval,
                "detection_engine": "YOLO11 TFLite",
                "tracking_engine": "ByteTrack",
            },

            "processing_time_seconds": round(
                time.perf_counter() - request_started,
                2,
            ),
        }

        logger.info(
            "Processing completed successfully. Job ID: %s",
            job_id,
        )

        return response

    except HTTPException:

        raise

    except VideoValidationError as exc:

        logger.exception("Video validation failed")

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:

        logger.exception(
            "Video processing failed. Job ID: %s",
            job_id,
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Video processing failed.",
                "error": str(exc),
            },
        )

    finally:

        cleanup_file(input_path)

        try:
            await file.close()
        except Exception:
            logger.exception("Unable to close uploaded file")


# =========================================================
# 16. LIST GENERATED OUTPUT FILES
# =========================================================

@app.get("/api/outputs")
async def list_outputs():

    files = []

    for path in OUTPUT_DIR.iterdir():

        if path.is_file():

            files.append({
                "filename": path.name,
                "size_bytes": path.stat().st_size,
                "url": get_public_url(path),
            })

    return {
        "success": True,
        "total_files": len(files),
        "files": files,
    }


# =========================================================
# 17. DELETE GENERATED OUTPUT
# =========================================================

@app.delete("/api/outputs/{filename}")
async def delete_output(filename: str):

    safe_name = Path(filename).name

    if safe_name != filename:

        raise HTTPException(
            status_code=400,
            detail="Invalid filename.",
        )

    target_path = OUTPUT_DIR / safe_name

    if not target_path.is_file():

        raise HTTPException(
            status_code=404,
            detail="Output file not found.",
        )

    try:

        target_path.unlink()

        return {
            "success": True,
            "message": "Output file deleted.",
            "filename": safe_name,
        }

    except Exception as exc:

        logger.exception("Unable to delete output file")

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# =========================================================
# 18. LOCAL DEVELOPMENT
# =========================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True,
    )
