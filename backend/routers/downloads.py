from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from services.job_store import get_job, delete_job

router = APIRouter(prefix="/api/jobs", tags=["downloads"])


def _output(job_id: str, key: str, media_type: str, filename: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    if job.get("status") != "completed":
        raise HTTPException(409, "Job has not completed.")
    result = job.get("result") or {}
    path = result.get(key)
    if not path or not Path(path).is_file():
        raise HTTPException(404, "Output file is unavailable. It may have expired.")
    return FileResponse(path, media_type=media_type, filename=filename)


@router.get("/{job_id}/video")
def download_video(job_id: str):
    return _output(job_id, "video_path", "video/mp4", "annotated_video.mp4")


@router.get("/{job_id}/csv")
def download_csv(job_id: str):
    return _output(job_id, "csv_path", "text/csv", "frame_analytics.csv")


@router.get("/{job_id}/json")
def download_json(job_id: str):
    return _output(job_id, "json_path", "application/json", "analytics.json")


@router.delete("/{job_id}")
def remove_job(job_id: str):
    job = delete_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    result = job.get("result") or {}
    for key in ("video_path", "csv_path", "json_path"):
        path = result.get(key)
        if path:
            try:
                Path(path).unlink(missing_ok=True)
            except OSError:
                pass
    return {"deleted": True, "job_id": job_id}
