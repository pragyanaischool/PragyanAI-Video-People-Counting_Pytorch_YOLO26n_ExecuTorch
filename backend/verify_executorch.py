import argparse
from pathlib import Path
import cv2
import numpy as np
from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="models/yolo26n_executorch_model")
    parser.add_argument("--image", default="")
    args = parser.parse_args()

    model_dir = Path(args.model)
    pte = model_dir / "model.pte"
    metadata = model_dir / "metadata.yaml"

    if not pte.is_file():
        raise SystemExit(f"Missing model file: {pte}")
    if not metadata.is_file():
        raise SystemExit(f"Missing metadata file: {metadata}")

    print("Model directory:", model_dir.resolve())
    model = YOLO(str(model_dir))

    if args.image:
        image = cv2.imread(args.image)
        if image is None:
            raise SystemExit(f"Could not read image: {args.image}")
    else:
        image = np.zeros((640, 640, 3), dtype=np.uint8)

    results = model.predict(image, imgsz=640, conf=0.25, verbose=False)
    result = results[0]
    count = len(result.boxes) if result.boxes is not None else 0
    print("ExecuTorch model loaded and predict() returned successfully.")
    print("Detections on test image:", count)
    print("NOTE: A black-image smoke test verifies runtime execution, not model accuracy.")


if __name__ == "__main__":
    main()
