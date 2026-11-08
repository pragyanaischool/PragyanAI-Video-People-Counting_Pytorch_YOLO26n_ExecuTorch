import logging
from threading import Lock
from pathlib import Path

import numpy as np
from ultralytics import YOLO

from config import settings

logger = logging.getLogger(__name__)
_model = None
_model_lock = Lock()
_inference_lock = Lock()


def model_directory_ready() -> bool:
    path = settings.resolved_model_path
    return path.is_dir() and (path / "model.pte").is_file()


def get_model():
    """Load the exported ExecuTorch model once, using Ultralytics' integration."""
    global _model
    if _model is not None:
        return _model

    with _model_lock:
        if _model is not None:
            return _model

        model_path = settings.resolved_model_path
        if not model_directory_ready():
            raise FileNotFoundError(
                f"ExecuTorch model not found at {model_path}. "
                "Copy model.pte and metadata.yaml into the configured model directory."
            )

        logger.info("Loading YOLO26 ExecuTorch model from %s", model_path)
        _model = YOLO(str(model_path))
        logger.info("YOLO26 ExecuTorch model loaded")
        return _model


def predict_frame(frame: np.ndarray, confidence: float, image_size: int):
    """Run one frame through Ultralytics' ExecuTorch prediction path."""
    model = get_model()
    # Ultralytics model inference is guarded because the app runs CPU jobs in a worker.
    with _inference_lock:
        results = model.predict(
            source=frame,
            conf=confidence,
            imgsz=image_size,
            verbose=False,
        )
    return results[0]


def model_info() -> dict:
    return {
        "model": "YOLO26n",
        "format": "ExecuTorch",
        "model_path": str(settings.resolved_model_path),
        "model_files_present": model_directory_ready(),
        "loaded": _model is not None,
        "runtime": "Ultralytics ExecuTorch integration",
    }
