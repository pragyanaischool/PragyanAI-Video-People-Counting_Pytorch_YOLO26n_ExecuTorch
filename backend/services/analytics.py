import csv
import json
from pathlib import Path
from typing import Any


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fields = [
        "frame_number", "timestamp_seconds", "people_count",
        "objects_count", "unique_people_so_far", "track_ids"
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
