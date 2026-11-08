"""
PragyanAI Video People Counting
YOLO26n + ExecuTorch + ByteTrack

FastAPI job management:
1. Upload video
2. Validate file and parameters
3. Save video to temporary storage
4. Create processing job
5. Run video processing in background
6. Update processing progress
7. Return analytics and download URLs
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid

from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    UploadFile,
    Request,
)
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from config import settings

from schemas.job_schema import JobCreated, JobStatus

from services.job_store import (
    create_job,
    get_job,
    update_job,
    subscribe_job,
    unsubscribe_job,
)

from services.video_processor import process_video

from utils.file_utils import safe_filename

from utils.video_utils import is_supported_video


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/jobs",
    tags=["jobs"],
)

UPLOAD_CHUNK_SIZE = 1024 * 1024


# ============================================================
# 1. PROGRESS UPDATE
# ============================================================

def _publish_progress(
    job_id: str,
    **updates: Any,
) -> None:

    update_job(
        job_id,
        **updates
    )


# ============================================================
# 2. BACKGROUND VIDEO PROCESSING
# ============================================================

def _run_job(
    job_id: str,
    input_path: str,
    confidence: float,
    frame_interval: int,
) -> None:

    logger.info(
        "Starting video processing job: %s",
        job_id,
    )

    update_job(
        job_id,
        status="processing",
        stage="starting_worker",
        activity_message="Processing worker started. Preparing video analysis.",
        progress=0,
        error=None,
    )

    try:

        result = process_video(

            job_id=job_id,

            input_path=input_path,

            confidence=confidence,

            frame_interval=frame_interval,

            update_callback=lambda **values: (
                _publish_progress(
                    job_id,
                    **values,
                )
            ),
        )

        if not isinstance(result, dict):

            raise TypeError(
                "process_video() must return a dictionary."
            )

        summary = result.get("summary")

        if not isinstance(summary, dict):

            raise ValueError(
                "Video processor did not return a valid summary."
            )

        update_job(

            job_id,

            status="completed",

            stage="completed",

            activity_message="Video analysis, tracking and downloadable analytics completed.",

            progress=100,

            result=result,

            analytics=summary,

            video_url=(
                f"/api/jobs/{job_id}/video"
            ),

            csv_url=(
                f"/api/jobs/{job_id}/csv"
            ),

            json_url=(
                f"/api/jobs/{job_id}/json"
            ),

            error=None,
        )

        logger.info(
            "Video job %s completed successfully",
            job_id,
        )

    except Exception as exc:

        logger.exception(
            "Video processing job failed: %s",
            job_id,
        )

        update_job(
            job_id,
            status="failed",
            stage="failed",
            activity_message=f"Processing failed: {exc}",
            error=str(exc),
        )

    finally:

        # Remove original uploaded video after processing.

        try:

            Path(input_path).unlink(
                missing_ok=True
            )

        except OSError:

            logger.warning(
                "Could not remove uploaded file: %s",
                input_path,
            )


# ============================================================
# 3. CREATE VIDEO PROCESSING JOB
# ============================================================

@router.post(
    "",
    response_model=JobCreated,
    status_code=202,
)
async def create_video_job(

    background_tasks: BackgroundTasks,

    file: UploadFile = File(...),

    confidence: float = Form(
        settings.default_confidence
    ),

    frame_interval: int = Form(
        settings.default_frame_interval
    ),

):

    """
    Upload a video and create a background processing job.

    API:
        POST /api/jobs

    Form fields:
        file
        confidence
        frame_interval
    """

    # --------------------------------------------------------
    # VALIDATE FILE
    # --------------------------------------------------------

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="A video filename is required.",
        )

    if not is_supported_video(file.filename):

        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported video format. "
                "Use MP4, AVI, MOV, MKV or WEBM."
            ),
        )

    # --------------------------------------------------------
    # VALIDATE PARAMETERS
    # --------------------------------------------------------

    if not 0.05 <= confidence <= 0.99:

        raise HTTPException(
            status_code=400,
            detail=(
                "Confidence must be between 0.05 and 0.99."
            ),
        )

    if not 1 <= frame_interval <= 30:

        raise HTTPException(
            status_code=400,
            detail=(
                "Frame interval must be between 1 and 30."
            ),
        )

    # --------------------------------------------------------
    # GENERATE JOB ID
    # --------------------------------------------------------

    job_id = uuid.uuid4().hex

    filename = safe_filename(
        file.filename
    )

    upload_path = (
        settings.upload_path
        / f"{job_id}_{filename}"
    )

    upload_size = 0

    # --------------------------------------------------------
    # SAVE UPLOADED VIDEO
    # --------------------------------------------------------

    try:

        with upload_path.open("wb") as destination:

            while True:

                chunk = await file.read(
                    UPLOAD_CHUNK_SIZE
                )

                if not chunk:
                    break

                upload_size += len(chunk)

                # Maximum upload size validation

                if upload_size > settings.max_upload_size:

                    raise HTTPException(
                        status_code=413,
                        detail=(
                            "Video exceeds the configured "
                            f"upload limit of "
                            f"{settings.max_upload_size} bytes."
                        ),
                    )

                destination.write(chunk)

    except HTTPException:

        upload_path.unlink(
            missing_ok=True
        )

        raise

    except OSError as exc:

        upload_path.unlink(
            missing_ok=True
        )

        logger.exception(
            "Could not save uploaded video"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "The server could not save the uploaded video."
            ),
        ) from exc

    finally:

        await file.close()

    # --------------------------------------------------------
    # CHECK EMPTY FILE
    # --------------------------------------------------------

    if upload_size == 0:

        upload_path.unlink(
            missing_ok=True
        )

        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty.",
        )

    # --------------------------------------------------------
    # INITIALIZE JOB DATA
    # --------------------------------------------------------

    job_data = {

        "job_id": job_id,

        "filename": filename,

        "status": "queued",

        "progress": 0,

        "stage": "queued",

        "activity_message": "Video uploaded; waiting for a processing worker.",

        "current_detections": [],

        "current_frame": 0,

        "total_frames": None,

        "frames_processed": 0,

        "current_people": 0,

        "current_objects": 0,

        "unique_people_so_far": 0,

        "elapsed_seconds": 0,

        "latest_frame": None,

        "recent_activity": [],

        "error": None,

        "result": None,

        "analytics": None,

        "video_url": None,

        "csv_url": None,

        "json_url": None,
    }

    create_job(
        job_id,
        job_data
    )

    # --------------------------------------------------------
    # START BACKGROUND PROCESSING
    # --------------------------------------------------------

    background_tasks.add_task(

        _run_job,

        job_id,

        str(upload_path),

        confidence,

        frame_interval,
    )

    logger.info(
        "Accepted video job %s (%s bytes, %s)",
        job_id,
        upload_size,
        filename,
    )

    return JobCreated(

        job_id=job_id,

        status="queued",

        message=(
            "Video uploaded successfully. "
            "Processing has been queued."
        ),
    )


# ============================================================
# 4. REAL-TIME JOB EVENTS (SERVER-SENT EVENTS)
# ============================================================

def _event_payload(job: dict[str, Any]) -> dict[str, Any]:
    """Expose progress fields only; never send local filesystem paths."""
    keys = (
        "job_id",
        "status",
        "progress",
        "stage",
        "activity_message",
        "current_frame",
        "total_frames",
        "frames_processed",
        "current_people",
        "current_objects",
        "unique_people_so_far",
        "elapsed_seconds",
        "latest_frame",
        "recent_activity",
        "current_detections",
        "error",
        "video_url",
        "csv_url",
        "json_url",
        "analytics",
        "_version",
    )
    return {key: job.get(key) for key in keys if key in job}


@router.get("/{job_id}/events")
async def stream_job_events(job_id: str, request: Request):
    """
    Stream progress updates as Server-Sent Events.

    The connection remains open for the full job; there is no per-status
    request timeout or repeated HTTP polling. The browser reconnects
    automatically if the network briefly drops.
    """
    channel, initial = subscribe_job(job_id)
    if channel is None or initial is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    async def event_generator():
        last_preview = object()
        try:
            current = initial
            while True:
                if await request.is_disconnected():
                    break

                payload = _event_payload(current)
                preview = payload.get("latest_frame")
                if preview == last_preview:
                    payload.pop("latest_frame", None)
                else:
                    last_preview = preview
                version = int(current.get("_version", 0))
                yield (
                    f"id: {version}\n"
                    f"event: progress\n"
                    f"data: {json.dumps(payload, separators=(',', ':'), default=str)}\n\n"
                )

                if current.get("status") in {"completed", "failed", "cancelled"}:
                    break

                try:
                    current = await asyncio.to_thread(channel.get, True, 10)
                except Exception:
                    # Send an SSE comment heartbeat to keep proxies alive.
                    yield ": keep-alive\n\n"
        finally:
            unsubscribe_job(job_id, channel)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================
# 5. GET JOB STATUS (SNAPSHOT / FALLBACK)
# ============================================================

@router.get(
    "/{job_id}",
    response_model=JobStatus,
)
def get_video_job_status(
    job_id: str,
):

    """
    Get current video processing status.

    API:
        GET /api/jobs/{job_id}
    """

    job = get_job(job_id)

    if not job:

        raise HTTPException(
            status_code=404,
            detail=(
                "Job not found. "
                "It may have expired after a server restart."
            ),
        )

    return JobStatus(**job)


# ============================================================
# 5. GET JOB ANALYTICS
# ============================================================

@router.get(
    "/{job_id}/analytics"
)
def get_video_job_analytics(
    job_id: str,
):

    """
    Get video processing analytics.

    API:
        GET /api/jobs/{job_id}/analytics
    """

    job = get_job(job_id)

    if not job:

        raise HTTPException(
            status_code=404,
            detail="Job not found.",
        )

    status = job.get("status")

    if status != "completed":

        return {

            "status": status,

            "analytics": None,

            "error": job.get("error"),
        }

    return {

        "status": "completed",

        "analytics": job.get("analytics"),
    }

