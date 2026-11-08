from typing import Any, Optional
from pydantic import BaseModel, Field


class JobCreated(BaseModel):
    job_id: str
    status: str
    message: str


class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: float = 0
    current_frame: int = 0
    total_frames: Optional[int] = None
    frames_processed: int = 0
    current_people: int = 0
    current_objects: int = 0
    unique_people_so_far: int = 0
    elapsed_seconds: float = 0
    error: Optional[str] = None
    stage: Optional[str] = None
    activity_message: Optional[str] = None
    current_detections: list[dict[str, Any]] = Field(default_factory=list)
    latest_frame: Optional[str] = None
    recent_activity: list[dict[str, Any]] = Field(default_factory=list)
    video_url: Optional[str] = None
    csv_url: Optional[str] = None
    json_url: Optional[str] = None

