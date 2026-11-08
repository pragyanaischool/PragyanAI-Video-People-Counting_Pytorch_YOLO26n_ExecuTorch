"""
PragyanAI Video People Counting
YOLO26n + ExecuTorch + ByteTrack

Download and job cleanup API.
"""

from pathlib import Path
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from config import settings
from services.job_store import get_job, delete_job


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/jobs",
    tags=["downloads"],
)


# ============================================================
# 1. OUTPUT CONFIGURATION
# ============================================================

OUTPUTS = {
    "video": {
        "result_key": "video_path",
        "media_type": "video/mp4",
        "filename": "annotated_video.mp4",
    },
    "csv": {
        "result_key": "csv_path",
        "media_type": "text/csv; charset=utf-8",
        "filename": "frame_analytics.csv",
    },
    "json": {
        "result_key": "json_path",
        "media_type": "application/json",
        "filename": "analytics.json",
    },
}


# ============================================================
# 2. GET COMPLETED JOB
# ============================================================

def get_completed_job(job_id: str) -> dict[str, Any]:

    job = get_job(job_id)

    if not job:

        raise HTTPException(
            status_code=404,
            detail="Job not found.",
        )

    if job.get("status") != "completed":

        raise HTTPException(
            status_code=409,
            detail=(
                "Video processing is not completed. "
                f"Current status: {job.get('status')}."
            ),
        )

    return job


# ============================================================
# 3. RESOLVE OUTPUT FILE
# ============================================================

def resolve_output_path(
    job: dict[str, Any],
    result_key: str,
) -> Path:

    result = job.get("result") or {}

    raw_path = result.get(result_key)

    if not raw_path:

        raise HTTPException(
            status_code=404,
            detail="Output file is not available.",
        )

    path = Path(raw_path).resolve()

    output_root = Path(
        settings.output_path
    ).resolve()

    # Prevent access outside configured output directory.

    try:

        path.relative_to(output_root)

    except ValueError:

        raise HTTPException(
            status_code=403,
            detail="Invalid output file path.",
        )

    if not path.is_file():

        raise HTTPException(
            status_code=404,
            detail=(
                "Output file is unavailable. "
                "It may have expired after a server restart."
            ),
        )

    return path


# ============================================================
# 4. DOWNLOAD HELPER
# ============================================================

def download_output(
    job_id: str,
    output_type: str,
) -> FileResponse:

    job = get_completed_job(job_id)

    config = OUTPUTS[output_type]

    path = resolve_output_path(
        job,
        config["result_key"],
    )

    return FileResponse(
        path=str(path),
        media_type=config["media_type"],
        filename=config["filename"],
    )


# ============================================================
# 5. DOWNLOAD ANNOTATED VIDEO
# ============================================================

@router.get("/{job_id}/video")
def download_video(job_id: str):

    """
    Download processed MP4 video.

    GET /api/jobs/{job_id}/video
    """

    return download_output(
        job_id,
        "video",
    )


# ============================================================
# 6. DOWNLOAD CSV ANALYTICS
# ============================================================

@router.get("/{job_id}/csv")
def download_csv(job_id: str):

    """
    Download frame-by-frame CSV analytics.

    GET /api/jobs/{job_id}/csv
    """

    return download_output(
        job_id,
        "csv",
    )


# ============================================================
# 7. DOWNLOAD JSON ANALYTICS
# ============================================================

@router.get("/{job_id}/json")
def download_json(job_id: str):

    """
    Download JSON processing summary.

    GET /api/jobs/{job_id}/json
    """

    return download_output(
        job_id,
        "json",
    )


# ============================================================
# 8. DELETE JOB AND OUTPUT FILES
# ============================================================

@router.delete("/{job_id}")
def remove_job(job_id: str):

    """
    Delete job record and generated files.

    DELETE /api/jobs/{job_id}
    """

    job = get_job(job_id)

    if not job:

        raise HTTPException(
            status_code=404,
            detail="Job not found.",
        )

    deleted_job = delete_job(job_id)

    if not deleted_job:

        raise HTTPException(
            status_code=404,
            detail="Job not found.",
        )

    result = deleted_job.get("result") or {}

    deleted_files = []

    cleanup_errors = []

    output_root = Path(
        settings.output_path
    ).resolve()

    # Remove generated files.

    for key in (
        "video_path",
        "csv_path",
        "json_path",
    ):

        raw_path = result.get(key)

        if not raw_path:
            continue

        path = Path(raw_path).resolve()

        try:

            path.relative_to(output_root)

        except ValueError:

            cleanup_errors.append(key)
            continue

        try:

            if path.is_file():

                path.unlink()

                deleted_files.append(
                    path.name
                )

        except OSError:

            logger.exception(
                "Unable to delete file: %s",
                path,
            )

            cleanup_errors.append(key)

    # Remove empty job directory.

    job_directory = (
        output_root / job_id
    ).resolve()

    try:

        job_directory.relative_to(
            output_root
        )

        if job_directory.is_dir():

            job_directory.rmdir()

    except (ValueError, OSError):

        pass

    return {

        "deleted": True,

        "job_id": job_id,

        "deleted_files": deleted_files,

        "cleanup_errors": cleanup_errors,

    }
