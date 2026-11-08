import logging
import uuid
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from config import settings
from schemas.job_schema import JobCreated, JobStatus
from services.job_store import create_job, get_job, update_job
from services.video_processor import process_video
from utils.file_utils import safe_filename
from utils.video_utils import is_supported_video

router = APIRouter(prefix="/api/jobs", tags=["jobs"])
logger = logging.getLogger(__name__)


def _update(job_id: str, **kwargs):
    update_job(job_id, **kwargs)


def _run_job(job_id: str, input_path: str, confidence: float, frame_interval: int):
    update_job(job_id, status="processing", progress=0)
    try:
        result = process_video(
            job_id=job_id,
            input_path=input_path,
            confidence=confidence,
            frame_interval=frame_interval,
            update_callback=lambda **kw: _update(job_id, **kw),
        )
        update_job(
            job_id,
            status="completed",
            progress=100,
            result=result,
            analytics=result["summary"],
            video_url=f"/api/jobs/{job_id}/video",
            csv_url=f"/api/jobs/{job_id}/csv",
            json_url=f"/api/jobs/{job_id}/json",
            error=None,
        )
    except Exception as exc:
        logger.exception("Video job %s failed", job_id)
        update_job(job_id, status="failed", error=str(exc))
    finally:
        try:
            Path(input_path).unlink(missing_ok=True)
        except OSError:
            logger.warning("Could not remove upload %s", input_path)


@router.post("", response_model=JobCreated)
async def create_video_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    confidence: float = Form(settings.default_confidence),
    frame_interval: int = Form(settings.default_frame_interval),
):
    if not file.filename or not is_supported_video(file.filename):
        raise HTTPException(400, "Unsupported video format. Use MP4, AVI, MOV, MKV or WEBM.")
    if not 0.05 <= confidence <= 0.99:
        raise HTTPException(400, "Confidence must be between 0.05 and 0.99.")
    if not 1 <= frame_interval <= 30:
        raise HTTPException(400, "Frame interval must be between 1 and 30.")

    job_id = uuid.uuid4().hex
    safe_name = safe_filename(file.filename)
    upload_path = settings.upload_path / f"{job_id}_{safe_name}"
    size = 0

    try:
        with upload_path.open("wb") as destination:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > settings.max_upload_size:
                    destination.close()
                    upload_path.unlink(missing_ok=True)
                    raise HTTPException(413, "Video exceeds the configured upload limit.")
                destination.write(chunk)
    finally:
        await file.close()

    if size == 0:
        upload_path.unlink(missing_ok=True)
        raise HTTPException(400, "Uploaded file is empty.")

    create_job(job_id, {
        "job_id": job_id,
        "filename": safe_name,
        "status": "queued",
        "progress": 0,
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
    })

    background_tasks.add_task(
        _run_job, job_id, str(upload_path), confidence, frame_interval
    )
    return JobCreated(
        job_id=job_id,
        status="queued",
        message="Video uploaded. Processing job has been queued.",
    )


@router.get("/{job_id}", response_model=JobStatus)
def job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found. It may have expired after a server restart.")
    # This route only returns the in-memory snapshot. It does not read video files or run inference.
    return JobStatus(**{
        key: job.get(key) for key in JobStatus.model_fields.keys()
    })


@router.get("/{job_id}/analytics")
def job_analytics(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    if job.get("status") != "completed":
        return {"status": job.get("status"), "analytics": None}
    return {"status": "completed", "analytics": job.get("analytics")}
