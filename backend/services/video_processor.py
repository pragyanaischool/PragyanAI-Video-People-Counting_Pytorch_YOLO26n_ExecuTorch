"""
PragyanAI Video People Counting
YOLO26n + PyTorch + ExecuTorch + ByteTrack

Video processing pipeline:
1. Read uploaded video using OpenCV.
2. Extract video frames.
3. Run YOLO26n ExecuTorch inference.
4. Track detected objects using ByteTrack.
5. Count people and objects.
6. Draw bounding boxes and tracking IDs.
7. Generate annotated MP4 video.
8. Generate CSV and JSON analytics.
9. Send real-time processing updates to frontend.
"""

from __future__ import annotations

import base64
import logging
import math
import time

from pathlib import Path
from typing import Any, Callable

import cv2
import numpy as np

from config import settings

from services.inference import predict_frame
from services.tracker import (
    create_tracker,
    track_ultralytics_result,
)

from services.people_counter import (
    count_people_and_objects,
)

from services.analytics import (
    write_csv,
    write_json,
)

from utils.video_utils import open_video


logger = logging.getLogger(__name__)

ProgressCallback = Callable[..., None]


# ============================================================
# 1. GET CLASS NAME
# ============================================================

def _class_name(names: Any, class_id: int) -> str:

    if isinstance(names, dict):
        return str(names.get(class_id, class_id))

    if isinstance(names, (list, tuple)):

        if 0 <= class_id < len(names):
            return str(names[class_id])

    return str(class_id)


# ============================================================
# 2. DRAW DETECTIONS
# ============================================================

def _draw_detections(
    frame: np.ndarray,
    detections: Any,
    names: Any,
    people_count: int,
    objects_count: int,
    unique_people_count: int,
) -> np.ndarray:

    annotated = frame.copy()

    boxes = getattr(detections, "xyxy", None)

    class_ids = getattr(detections, "class_id", None)

    tracker_ids = getattr(detections, "tracker_id", None)

    confidences = getattr(detections, "confidence", None)

    if boxes is not None:

        for index, box in enumerate(boxes):

            x1, y1, x2, y2 = [
                int(round(float(value)))
                for value in box
            ]

            class_id = (
                int(class_ids[index])
                if class_ids is not None
                else -1
            )

            track_id = None

            if tracker_ids is not None:

                raw_track_id = tracker_ids[index]

                if raw_track_id is not None:

                    try:

                        if not (
                            isinstance(
                                raw_track_id,
                                (float, np.floating)
                            )
                            and math.isnan(float(raw_track_id))
                        ):

                            track_id = int(raw_track_id)

                    except (
                        TypeError,
                        ValueError,
                        OverflowError,
                    ):

                        track_id = None

            confidence = 0.0

            if confidences is not None:

                try:
                    confidence = float(confidences[index])

                except (
                    TypeError,
                    ValueError,
                    IndexError,
                ):
                    pass

            label = (
                f"{_class_name(names, class_id)} "
                f"{confidence:.2f}"
            )

            if track_id is not None:

                label = f"ID {track_id} | {label}"

            # Person = COCO class ID 0

            color = (
                (40, 210, 90)
                if class_id == 0
                else (40, 160, 245)
            )

            x1 = max(
                0,
                min(x1, frame.shape[1] - 1)
            )

            x2 = max(
                0,
                min(x2, frame.shape[1] - 1)
            )

            y1 = max(
                0,
                min(y1, frame.shape[0] - 1)
            )

            y2 = max(
                0,
                min(y2, frame.shape[0] - 1)
            )

            # Bounding box

            cv2.rectangle(
                annotated,
                (x1, y1),
                (x2, y2),
                color,
                2,
            )

            # Label background

            text_y = max(18, y1 - 7)

            text_width = min(
                320,
                12 + len(label) * 9
            )

            cv2.rectangle(
                annotated,
                (x1, max(0, y1 - 25)),
                (
                    min(
                        frame.shape[1] - 1,
                        x1 + text_width
                    ),
                    y1,
                ),
                color,
                -1,
            )

            cv2.putText(
                annotated,
                label,
                (x1 + 4, text_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.48,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )

    # Overall counting information

    overlay = (
        f"People: {people_count} | "
        f"Objects: {objects_count} | "
        f"Unique IDs: {unique_people_count}"
    )

    cv2.rectangle(
        annotated,
        (8, 8),
        (min(frame.shape[1] - 8, 650), 48),
        (20, 20, 20),
        -1,
    )

    cv2.putText(
        annotated,
        overlay,
        (16, 36),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.72,
        (0, 255, 255),
        2,
        cv2.LINE_AA,
    )

    return annotated


# ============================================================
# 3. GENERATE FRAME PREVIEW
# ============================================================

def _frame_preview_data_url(
    frame: np.ndarray,
) -> str | None:

    height, width = frame.shape[:2]

    longest_side = max(width, height)

    if longest_side <= 0:
        return None

    scale = min(
        480.0 / longest_side,
        1.0,
    )

    preview = frame

    if scale < 1.0:

        preview = cv2.resize(
            frame,
            (
                max(1, int(width * scale)),
                max(1, int(height * scale)),
            ),
            interpolation=cv2.INTER_AREA,
        )

    success, encoded = cv2.imencode(
        ".jpg",
        preview,
        [
            cv2.IMWRITE_JPEG_QUALITY,
            55,
        ],
    )

    if not success:
        return None

    payload = base64.b64encode(
        encoded.tobytes()
    ).decode("ascii")

    return (
        f"data:image/jpeg;base64,{payload}"
    )


# ============================================================
# 4. SAFE PROGRESS UPDATE
# ============================================================

def _safe_progress_update(
    callback: ProgressCallback,
    **payload: Any,
) -> None:

    try:

        callback(**payload)

    except Exception:

        logger.exception(
            "Could not publish video processing progress update"
        )


def _serialize_detections(
    detections: Any,
    names: Any,
) -> list[dict[str, Any]]:
    """Convert Supervision detections to compact JSON-safe frame telemetry."""
    if detections is None:
        return []

    boxes = getattr(detections, "xyxy", None)
    class_ids = getattr(detections, "class_id", None)
    tracker_ids = getattr(detections, "tracker_id", None)
    confidences = getattr(detections, "confidence", None)

    if boxes is None:
        return []

    output: list[dict[str, Any]] = []
    for index, box in enumerate(boxes):
        try:
            class_id = int(class_ids[index]) if class_ids is not None else -1
            bbox = [round(float(value), 1) for value in box]
            confidence = (
                round(float(confidences[index]), 4)
                if confidences is not None else None
            )
            track_id = None
            if tracker_ids is not None:
                raw_id = tracker_ids[index]
                if raw_id is not None:
                    try:
                        numeric_id = float(raw_id)
                        if math.isfinite(numeric_id):
                            track_id = int(numeric_id)
                    except (TypeError, ValueError, OverflowError):
                        pass

            output.append({
                "class_id": class_id,
                "class_name": _class_name(names, class_id),
                "track_id": track_id,
                "confidence": confidence,
                "bbox": bbox,
                "is_person": class_id == 0,
            })
        except (TypeError, ValueError, IndexError, OverflowError):
            logger.debug("Skipping malformed detection at index %s", index)
    return output


# ============================================================
# 5. MAIN VIDEO PROCESSING FUNCTION
# ============================================================

def process_video(
    job_id: str,
    input_path: str,
    confidence: float,
    frame_interval: int,
    update_callback: ProgressCallback,
) -> dict[str, Any]:

    """
    Process an uploaded video.

    Parameters
    ----------
    job_id:
        Unique video processing job ID.

    input_path:
        Uploaded video file path.

    confidence:
        YOLO detection confidence threshold.

    frame_interval:
        Run inference on every Nth frame.

    update_callback:
        Function to update frontend processing progress.

    Returns
    -------
    dict:
        summary
        video_path
        csv_path
        json_path
    """

    started = time.time()

    input_file = Path(input_path)

    if not input_file.is_file():

        raise FileNotFoundError(
            f"Input video not found: {input_file}"
        )

    confidence = float(confidence)

    if not 0.0 <= confidence <= 1.0:

        raise ValueError(
            "confidence must be between 0.0 and 1.0"
        )

    frame_interval = max(
        1,
        int(frame_interval)
    )

    cap = open_video(str(input_file))

    writer = None

    try:

        # ----------------------------------------------------
        # VIDEO INFORMATION
        # ----------------------------------------------------

        fps = float(
            cap.get(cv2.CAP_PROP_FPS) or 0.0
        )

        if not math.isfinite(fps) or fps <= 0:
            fps = 25.0

        total_frames_raw = int(
            cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        )

        width = int(
            cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0
        )

        height = int(
            cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0
        )

        if width <= 0 or height <= 0:

            raise ValueError(
                "Uploaded video has invalid width or height."
            )

        # ----------------------------------------------------
        # OUTPUT DIRECTORIES
        # ----------------------------------------------------

        output_dir = (
            settings.output_path / job_id
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        video_path = (
            output_dir / "annotated_video.mp4"
        )

        csv_path = (
            output_dir / "frame_analytics.csv"
        )

        json_path = (
            output_dir / "analytics.json"
        )

        # ----------------------------------------------------
        # INITIALIZE VIDEO WRITER
        # ----------------------------------------------------

        fourcc = cv2.VideoWriter_fourcc(
            *"mp4v"
        )

        writer = cv2.VideoWriter(
            str(video_path),
            fourcc,
            fps,
            (width, height),
        )

        if not writer.isOpened():

            raise RuntimeError(
                "OpenCV could not initialize the MP4 writer. "
                "Check the Render OpenCV build and available codecs."
            )

        # ----------------------------------------------------
        # INITIALIZE TRACKER
        # ----------------------------------------------------

        _safe_progress_update(
            update_callback,
            status="processing",
            stage="initializing_tracker",
            activity_message="Video opened. Initializing ByteTrack and frame analytics.",
            progress=0,
            current_frame=0,
            total_frames=total_frames_raw or None,
            frames_processed=0,
            current_people=0,
            current_objects=0,
            unique_people_so_far=0,
            elapsed_seconds=round(time.time() - started, 2),
            current_detections=[],
            recent_activity=[],
        )

        tracker = create_tracker()

        unique_person_ids: set[int] = set()

        rows: list[dict[str, Any]] = []

        recent_activity: list[dict[str, Any]] = []

        frame_number = 0

        frames_processed = 0

        current_people = 0

        current_objects = 0

        last_tracked = None

        last_names: Any = {}

        logger.info(
            "Starting video job %s: %s (%sx%s, %.2f FPS, %s frames)",
            job_id,
            input_file.name,
            width,
            height,
            fps,
            total_frames_raw if total_frames_raw > 0 else "unknown",
        )

        # ====================================================
        # 6. FRAME EXTRACTION AND INFERENCE LOOP
        # ====================================================

        while True:

            ok, frame = cap.read()

            if not ok:
                break

            frame_number += 1

            # ------------------------------------------------
            # RUN INFERENCE AT FRAME INTERVAL
            # ------------------------------------------------

            should_infer = (
                (frame_number - 1) % frame_interval == 0
                or last_tracked is None
            )

            if should_infer:

                result = predict_frame(

                    frame,

                    confidence=confidence,

                    image_size=settings.yolo_image_size,
                )

                # ByteTrack object tracking

                _, last_tracked = (
                    track_ultralytics_result(
                        result,
                        tracker,
                    )
                )

                last_names = (
                    getattr(result, "names", {})
                    or {}
                )

                # ------------------------------------------------
                # PEOPLE AND OBJECT COUNTING
                # ------------------------------------------------

                (
                    current_people,
                    current_objects,
                    observed_person_ids,
                ) = count_people_and_objects(
                    last_tracked
                )

                unique_person_ids.update(
                    observed_person_ids
                )

                frames_processed += 1

            # ------------------------------------------------
            # ANNOTATE FRAME
            # ------------------------------------------------

            annotated = _draw_detections(

                frame=frame,

                detections=last_tracked,

                names=last_names,

                people_count=current_people,

                objects_count=current_objects,

                unique_people_count=len(
                    unique_person_ids
                ),
            )

            writer.write(annotated)

            # ------------------------------------------------
            # TRACKING IDS
            # ------------------------------------------------

            timestamp = (
                frame_number - 1
            ) / fps

            track_ids: list[int] = []

            if (
                last_tracked is not None
                and last_tracked.tracker_id is not None
            ):

                for value in last_tracked.tracker_id:

                    if value is None:
                        continue

                    try:

                        if (
                            isinstance(
                                value,
                                (float, np.floating)
                            )
                            and math.isnan(float(value))
                        ):
                            continue

                        track_ids.append(
                            int(value)
                        )

                    except (
                        TypeError,
                        ValueError,
                        OverflowError,
                    ):
                        continue

            # ------------------------------------------------
            # FRAME ANALYTICS
            # ------------------------------------------------

            rows.append({

                "frame_number": frame_number,

                "timestamp_seconds": round(
                    timestamp,
                    3
                ),

                "people_count": current_people,

                "objects_count": current_objects,

                "unique_people_so_far": len(
                    unique_person_ids
                ),

                "track_ids": ",".join(
                    map(str, track_ids)
                ),

            })

            # =================================================
            # 7. PER-FRAME LIVE TELEMETRY
            # =================================================

            detections_payload = _serialize_detections(
                last_tracked,
                last_names,
            )

            # Record every frame, including frames where inference is
            # intentionally skipped by frame_interval. For interval > 1,
            # detections are the latest tracked result carried forward.
            activity_item = {
                "frame_number": frame_number,
                "people_count": current_people,
                "objects_count": current_objects,
                "unique_people": len(unique_person_ids),
                "detection_count": len(detections_payload),
                "inference_performed": bool(should_infer),
                "timestamp_seconds": round(timestamp, 3),
            }
            recent_activity.append(activity_item)
            recent_activity = recent_activity[-30:]

            progress = (
                round(min(99.0, frame_number / total_frames_raw * 100.0), 2)
                if total_frames_raw > 0
                else 0.0
            )

            progress_payload = {
                "status": "processing",
                "stage": "detecting_and_tracking" if should_infer else "tracking_latest_detections",
                "activity_message": (
                    f"Frame {frame_number}: "
                    f"{current_people} people, {current_objects} objects, "
                    f"{len(detections_payload)} detections, "
                    f"{len(unique_person_ids)} unique people tracked."
                ),
                "progress": progress,
                "current_frame": frame_number,
                "total_frames": total_frames_raw or None,
                "frames_processed": frames_processed,
                "current_people": current_people,
                "current_objects": current_objects,
                "unique_people_so_far": len(unique_person_ids),
                "elapsed_seconds": round(time.time() - started, 2),
                "current_detections": detections_payload,
                "recent_activity": list(recent_activity),
            }

            # JPEG preview is relatively large; refresh it every 5 frames
            # while compact detection telemetry is published on every frame.
            if frame_number == 1 or frame_number % 5 == 0:
                progress_payload["latest_frame"] = _frame_preview_data_url(
                    annotated
                )

            _safe_progress_update(
                update_callback,
                **progress_payload,
            )

        # ====================================================
        # 8. CHECK VIDEO
        # ====================================================

        if frame_number == 0:

            raise ValueError(
                "The uploaded video contains no readable frames."
            )

        _safe_progress_update(
            update_callback,
            status="processing",
            stage="generating_analytics",
            activity_message="All video frames processed. Writing CSV and JSON analytics.",
            progress=99,
            current_frame=frame_number,
            total_frames=total_frames_raw or frame_number,
            frames_processed=frames_processed,
            current_people=current_people,
            current_objects=current_objects,
            unique_people_so_far=len(unique_person_ids),
            elapsed_seconds=round(time.time() - started, 2),
        )

        # ====================================================
        # 9. SAVE CSV ANALYTICS
        # ====================================================

        write_csv(
            rows,
            csv_path
        )

        # ====================================================
        # 10. GENERATE SUMMARY
        # ====================================================

        processing_seconds = round(
            time.time() - started,
            2
        )

        summary = {

            "job_id": job_id,

            "status": "completed",

            "total_frames": frame_number,

            "inference_frames": frames_processed,

            "frame_interval": frame_interval,

            "fps": round(fps, 3),

            "width": width,

            "height": height,

            "duration_seconds": round(
                frame_number / fps,
                3
            ),

            "processing_seconds": processing_seconds,

            "unique_people_tracked": len(
                unique_person_ids
            ),

            "unique_person_track_ids": sorted(
                unique_person_ids
            ),

            "last_frame_people_count": current_people,

            "last_frame_objects_count": current_objects,

            "csv_rows": len(rows),

        }

        # ====================================================
        # 11. SAVE JSON ANALYTICS
        # ====================================================

        write_json(
            summary,
            json_path
        )

        logger.info(
            "Completed video job %s: %s frames, %s inference frames, %.2f seconds",
            job_id,
            frame_number,
            frames_processed,
            processing_seconds,
        )

        # ====================================================
        # 12. RETURN OUTPUT FILES
        # ====================================================

        return {

            "summary": summary,

            "video_path": str(video_path),

            "csv_path": str(csv_path),

            "json_path": str(json_path),

        }

    finally:

        cap.release()

        if writer is not None:
            writer.release()

