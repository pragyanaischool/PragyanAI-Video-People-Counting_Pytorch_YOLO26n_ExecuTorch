from copy import deepcopy
from threading import RLock
from typing import Any

_lock = RLock()
_jobs: dict[str, dict[str, Any]] = {}


def create_job(job_id: str, payload: dict[str, Any]) -> None:
    with _lock:
        _jobs[job_id] = payload


def update_job(job_id: str, **updates) -> None:
    with _lock:
        if job_id in _jobs:
            _jobs[job_id].update(updates)


def get_job(job_id: str):
    with _lock:
        job = _jobs.get(job_id)
        return deepcopy(job) if job else None


def delete_job(job_id: str):
    with _lock:
        return _jobs.pop(job_id, None)
