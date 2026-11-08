def count_people_and_objects(tracked_detections):
    """COCO class 0 is person. Count tracked boxes and return observed IDs."""
    class_ids = tracked_detections.class_id
    tracker_ids = tracked_detections.tracker_id

    if class_ids is None:
        return 0, len(tracked_detections), set()

    people_mask = class_ids == 0
    people_count = int(people_mask.sum())
    object_count = len(tracked_detections)

    person_ids = set()
    if tracker_ids is not None:
        for class_id, tracker_id in zip(class_ids, tracker_ids):
            if int(class_id) == 0 and tracker_id is not None:
                person_ids.add(int(tracker_id))

    return people_count, object_count, person_ids
