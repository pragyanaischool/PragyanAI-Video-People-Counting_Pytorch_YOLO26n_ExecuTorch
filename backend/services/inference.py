"""
YOLO26n ExecuTorch inference service for PragyanAI.

Expected model directory:
    backend/models/
        model.pte
        metadata.yaml

The model is loaded through the Ultralytics ExecuTorch integration.
"""

import logging
from pathlib import Path
from threading import Lock
from typing import Any

import numpy as np
from ultralytics import YOLO

from config import settings

logger = logging.getLogger(__name__)

# One model instance per backend process.
_model: YOLO | None = None

_model_lock = Lock()
_inference_lock = Lock()

_model_load_error: str | None = None


# ============================================================
# 1. CHECK MODEL FILES
# ============================================================

def model_directory_ready() -> bool:
    """Check whether the configured ExecuTorch model files exist."""

    model_dir = Path(settings.resolved_model_path)

    model_file = model_dir / "model.pte"
    metadata_file = model_dir / "metadata.yaml"

    return (
        model_dir.is_dir()
        and model_file.is_file()
        and metadata_file.is_file()
    )


# ============================================================
# 2. LOAD YOLO26N EXECUTORCH MODEL
# ============================================================

def get_model() -> YOLO:
    """
    Load YOLO26n ExecuTorch model once.

    Ultralytics reads model.pte and metadata.yaml
    from the configured model directory.
    """

    global _model, _model_load_error

    if _model is not None:
        return _model

    with _model_lock:

        if _model is not None:
            return _model

        model_dir = Path(settings.resolved_model_path)

        model_file = model_dir / "model.pte"
        metadata_file = model_dir / "metadata.yaml"

        if not model_dir.is_dir():

            message = (
                f"Model directory does not exist: {model_dir}"
            )

            _model_load_error = message

            raise FileNotFoundError(message)

        missing_files = [
            str(path)
            for path in (model_file, metadata_file)
            if not path.is_file()
        ]

        if missing_files:

            message = (
                "Required ExecuTorch model files are missing: "
                + ", ".join(missing_files)
                + ". Expected model.pte and metadata.yaml "
                  "in the model directory."
            )

            _model_load_error = message

            raise FileNotFoundError(message)

        try:

            logger.info(
                "Loading YOLO26n ExecuTorch model from: %s",
                model_dir,
            )

            logger.info(
                "Model size: %.2f MB",
                model_file.stat().st_size / (1024 * 1024),
            )

            # Load model using Ultralytics ExecuTorch integration.
            loaded_model = YOLO(str(model_dir))

            _model = loaded_model

            _model_load_error = None

            logger.info(
                "YOLO26n ExecuTorch model loaded successfully"
            )

            return _model

        except Exception as exc:

            _model_load_error = (
                f"{type(exc).__name__}: {exc}"
            )

            logger.exception(
                "Unable to load YOLO26n ExecuTorch model"
            )

            raise RuntimeError(
                "Failed to load YOLO26n ExecuTorch model. "
                "Check Ultralytics and ExecuTorch versions, "
                "model.pte, metadata.yaml and Render logs. "
                f"Original error: {exc}"
            ) from exc


# ============================================================
# 3. YOLO26N FRAME INFERENCE
# ============================================================

def predict_frame(
    frame: np.ndarray,
    confidence: float,
    image_size: int,
) -> Any:
    """
    Run YOLO26n inference on one OpenCV BGR frame.

    Args:
        frame:
            OpenCV image as NumPy array (H, W, 3).

        confidence:
            Detection confidence threshold (0.0–1.0).

        image_size:
            Model inference image size, normally 640.

    Returns:
        First Ultralytics Results object.
    """

    if not isinstance(frame, np.ndarray):

        raise TypeError(
            "frame must be a NumPy array"
        )

    if frame.size == 0:

        raise ValueError(
            "frame is empty"
        )

    if frame.ndim != 3 or frame.shape[2] != 3:

        raise ValueError(
            "frame must have shape (height, width, 3)"
        )

    confidence = float(confidence)

    if not 0.0 <= confidence <= 1.0:

        raise ValueError(
            "confidence must be between 0.0 and 1.0"
        )

    image_size = int(image_size)

    if image_size <= 0:

        raise ValueError(
            "image_size must be a positive integer"
        )

    model = get_model()

    # Serialize inference calls on the shared model.
    with _inference_lock:

        results = model.predict(

            source=frame,

            conf=confidence,

            imgsz=image_size,

            verbose=False,
        )

    if not results:

        raise RuntimeError(
            "YOLO inference returned no result"
        )

    return results[0]


# ============================================================
# 4. MODEL INFORMATION
# ============================================================

def model_info() -> dict[str, Any]:
    """
    Return model status and runtime information.

    Used by:
        GET /health
        GET /api/model-info
    """

    model_dir = Path(settings.resolved_model_path)

    model_file = model_dir / "model.pte"

    metadata_file = model_dir / "metadata.yaml"

    files_present = model_directory_ready()

    return {

        "model": "YOLO26n",

        "format": "ExecuTorch",

        "model_path": str(model_dir),

        "model_file": str(model_file),

        "metadata_file": str(metadata_file),

        "model_files_present": files_present,

        "loaded": _model is not None,

        "runtime": (
            "Ultralytics ExecuTorch integration"
        ),

        "model_load_error": _model_load_error,
    }
