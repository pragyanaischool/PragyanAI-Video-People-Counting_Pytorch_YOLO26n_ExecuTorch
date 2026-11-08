
import supervision as sv


def create_tracker():
    """
    Create a ByteTrack tracker for one video-processing job.
    Compatible with supervision 0.30.9.
    """
    return sv.ByteTrack(
        track_activation_threshold=0.25,
        lost_track_buffer=30,
        minimum_matching_threshold=0.8,
        frame_rate=30,
    )


def track_ultralytics_result(result, tracker):
    """
    Convert YOLO detections into Supervision format
    and assign tracking IDs using ByteTrack.
    """

    if result is None:
        return sv.Detections.empty(), sv.Detections.empty()

    detections = sv.Detections.from_ultralytics(result)

    tracked = tracker.update_with_detections(detections)

    return detections, tracked
