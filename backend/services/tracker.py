
import supervision as sv


def create_tracker():
    """
    Create a fresh ByteTrack instance for each video-processing job.

    ByteTrack maintains object identities across consecutive frames,
    allowing the system to track people even when they move.
    """
    return sv.ByteTrack()


def track_ultralytics_result(result, tracker):
    """
    Convert Ultralytics YOLO detections into Supervision detections
    and update the ByteTrack tracker.

    Args:
        result:
            Ultralytics YOLO prediction result for a single frame.

        tracker:
            ByteTrack instance created using create_tracker().

    Returns:
        tuple:
            detections: Original Supervision detections.
            tracked: Detections with tracking IDs assigned by ByteTrack.
    """

    # Convert YOLO result into Supervision Detections format
    detections = sv.Detections.from_ultralytics(result)

    # Update ByteTrack and assign tracking IDs
    tracked = tracker.update_with_detections(detections)

    return detections, tracked
