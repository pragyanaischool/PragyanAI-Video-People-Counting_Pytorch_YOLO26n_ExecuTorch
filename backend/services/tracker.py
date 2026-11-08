import supervision as sv


def create_tracker():
    """Create a fresh ByteTrack instance for each video job."""
    return sv.ByteTrack()


def track_ultralytics_result(result, tracker):
    """Convert Ultralytics result to Supervision detections and update ByteTrack."""
    detections = sv.Detections.from_ultralytics(result)
    if detections.class_id is None:
        return detections, tracker.update_with_detections(detections)
    tracked = tracker.update_with_detections(detections)
    return detections, tracked
