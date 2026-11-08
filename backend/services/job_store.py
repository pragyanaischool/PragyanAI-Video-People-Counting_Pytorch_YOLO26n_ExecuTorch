
from copy import deepcopy
from queue import Queue, Empty
from threading import RLock
from typing import Any

_lock = RLock()
_jobs: dict[str, dict[str, Any]] = {}
_subscribers: dict[str, set[Queue]] = {}


def _publish_locked(
    job_id: str,
    snapshot: dict[str, Any],
    include_preview: bool = False,
) -> None:
    """Publish compact snapshots; large JPEG previews are sent only when refreshed."""
    event_keys = {
        "job_id", "status", "progress", "stage", "activity_message",
        "current_frame", "total_frames", "frames_processed",
        "current_people", "current_objects", "unique_people_so_far",
        "elapsed_seconds", "recent_activity", "current_detections",
        "error", "video_url", "csv_url", "json_url", "analytics", "_version",
    }

    if include_preview:
        event_keys.add("latest_frame")

    event = {
        key: deepcopy(value)
        for key, value in snapshot.items()
        if key in event_keys
    }

    for subscriber in tuple(_subscribers.get(job_id, set())):
        try:
            subscriber.put_nowait(event)
        except Exception:
            # A slow client must not block video inference.
            # Keep the newest telemetry instead of allowing an
            # unbounded queue to consume RAM.
            try:
                subscriber.get_nowait()
                subscriber.put_nowait(event)
            except Exception:
                pass


def create_job(job_id: str, payload: dict[str, Any]) -> None:
    with _lock:
        job = deepcopy(payload)
        job["_version"] = 1
        _jobs[job_id] = job
        _publish_locked(job_id, job)


def update_job(job_id: str, **updates) -> None:
    with _lock:
        if job_id not in _jobs:
            return

        _jobs[job_id].update(updates)
        _jobs[job_id]["_version"] = (
            int(_jobs[job_id].get("_version", 0)) + 1
        )

        _publish_locked(
            job_id,
            _jobs[job_id],
            include_preview=("latest_frame" in updates),
        )


def get_job(job_id: str):
    with _lock:
        job = _jobs.get(job_id)
        return deepcopy(job) if job else None


def subscribe_job(job_id: str):
    """
    Atomically subscribe and return the current snapshot
    to avoid missing updates between subscription and snapshot retrieval.
    """
    with _lock:
        job = _jobs.get(job_id)

        if job is None:
            return None, None

        channel = Queue(maxsize=1000)
        _subscribers.setdefault(job_id, set()).add(channel)

        return channel, deepcopy(job)


def unsubscribe_job(job_id: str, channel: Queue) -> None:
    with _lock:
        subscribers = _subscribers.get(job_id)

        if subscribers is not None:
            subscribers.discard(channel)

            if not subscribers:
                _subscribers.pop(job_id, None)


def delete_job(job_id: str):
    with _lock:
        _subscribers.pop(job_id, None)
        return _jobs.pop(job_id, None)
