import base64
import logging
import time
from pathlib import Path

import cv2
import numpy as np

from config import settings
from services.inference import predict_frame
from services.tracker import create_tracker, track_ultralytics_result
from services.people_counter import count_people_and_objects
from services.analytics import write_csv, write_json
from utils.video_utils import open_video

logger = logging.getLogger(__name__)


def _draw_detections(frame, detections, names):
    annotated = frame.copy()
    class_ids = detections.class_id
    tracker_ids = detections.tracker_id
    confidences = detections.confidence

    for index, xyxy in enumerate(detections.xyxy):
        x1, y1, x2, y2 = [int(v) for v in xyxy]
        class_id = int(class_ids[index]) if class_ids is not None else -1
        track_id = (
            int(tracker_ids[index])
            if tracker_ids is not None and tracker_ids[index] is not None
            else None
        )
        confidence = (
            float(confidences[index])
            if confidences is not None else 0.0
        )
        class_name = names.get(class_id, str(class_id)) if isinstance(names, dict) else str(class_id)
        label = f"{class_name} {confidence:.2f}"
        if track_id is not None:
            label = f"ID {track_id} | {label}"

        color = (40, 210, 90) if class_id == 0 else (40, 160, 245)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        cv2.rectangle(annotated, (x1, max(0, y1 - 24)), (x1 + min(300, 10 + len(label) * 9), y1), color, -1)
        cv2.putText(
            annotated, label, (x1 + 4, max(16, y1 - 7)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1, cv2.LINE_AA
        )

    return annotated


def _frame_preview_data_url(frame):
    h, w = frame.shape[:2]
    scale = min(480 / max(w, h), 1.0)
    if scale < 1:
        frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
    ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 55])
    if not ok:
        return None
    return "data:image/jpeg;base64," + base64.b64encode(encoded.tobytes()).decode("ascii")


def process_video(
    job_id: str,
    input_path: str,
    confidence: float,
    frame_interval: int,
    update_callback,
) -> dict:
    started = time.time()
    cap = open_video(input_path)

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames_raw = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if width <= 0 or height <= 0:
        cap.release()
        raise ValueError("Video has invalid dimensions.")

    output_dir = settings.output_path / job_id
    output_dir.mkdir(parents=True, exist_ok=True)
    video_path = output_dir / "annotated_video.mp4"
    csv_path = output_dir / "frame_analytics.csv"
    json_path = output_dir / "analytics.json"

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(video_path), fourcc, fps, (width, height))
    if not writer.isOpened():
        cap.release()
        raise RuntimeError("OpenCV could not initialize the MP4 video writer.")

    tracker = create_tracker()
    unique_person_ids: set[int] = set()
    rows = []
    recent_activity = []
    frame_number = 0
    frames_processed = 0
    current_people = 0
    current_objects = 0
    last_tracked = None
    last_names = {}
    frame_interval = max(1, int(frame_interval))

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            frame_number += 1

            # Run detection at the requested interval. Default is every frame.
            if (frame_number - 1) % frame_interval == 0 or last_tracked is None:
                result = predict_frame(
                    frame,
                    confidence=confidence,
                    image_size=settings.yolo_image_size,
                )
                _, last_tracked = track_ultralytics_result(result, tracker)
                last_names = result.names or {}
                current_people, current_objects, ids = count_people_and_objects(last_tracked)
                unique_person_ids.update(ids)
                frames_processed += 1

                activity = {
                    "frame_number": frame_number,
                    "people_count": current_people,
                    "objects_count": current_objects,
                    "unique_people": len(unique_person_ids),
                }
                recent_activity.append(activity)
                recent_activity = recent_activity[-20:]

            annotated = _draw_detections(frame, last_tracked, last_names)
            cv2.putText(
                annotated,
                f"People: {current_people} | Objects: {current_objects} | Unique IDs: {len(unique_person_ids)}",
                (16, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2, cv2.LINE_AA
            )
            writer.write(annotated)

            timestamp = (frame_number - 1) / fps
            track_ids = []
            if last_tracked is not None and last_tracked.tracker_id is not None:
                track_ids = [
                    int(x) for x in last_tracked.tracker_id if x is not None
                ]

            rows.append({
                "frame_number": frame_number,
                "timestamp_seconds": round(timestamp, 3),
                "people_count": current_people,
                "objects_count": current_objects,
                "unique_people_so_far": len(unique_person_ids),
                "track_ids": ",".join(map(str, track_ids)),
            })

            if frame_number % 5 == 0 or frame_number == 1:
                progress = (
                    round(frame_number / total_frames_raw * 100, 2)
                    if total_frames_raw > 0 else 0
                )
                update_callback(
                    status="processing",
                    progress=progress,
                    current_frame=frame_number,
                    total_frames=total_frames_raw or None,
                    frames_processed=frames_processed,
                    current_people=current_people,
                    current_objects=current_objects,
                    unique_people_so_far=len(unique_person_ids),
                    elapsed_seconds=round(time.time() - started, 2),
                    latest_frame=_frame_preview_data_url(annotated),
                    recent_activity=list(recent_activity),
                )

        if frame_number == 0:
            raise ValueError("The uploaded video contains no readable frames.")

    finally:
        cap.release()
        writer.release()

    write_csv(rows, csv_path)
    summary = {
        "job_id": job_id,
        "status": "completed",
        "total_frames": frame_number,
        "inference_frames": frames_processed,
        "frame_interval": frame_interval,
        "fps": fps,
        "width": width,
        "height": height,
        "duration_seconds": round(frame_number / fps, 3),
        "processing_seconds": round(time.time() - started, 2),
        "unique_people_tracked": len(unique_person_ids),
        "unique_person_track_ids": sorted(unique_person_ids),
        "last_frame_people_count": current_people,
        "last_frame_objects_count": current_objects,
        "csv_rows": len(rows),
    }
    write_json(summary, json_path)

    return {
        "summary": summary,
        "video_path": str(video_path),
        "csv_path": str(csv_path),
        "json_path": str(json_path),
    }
