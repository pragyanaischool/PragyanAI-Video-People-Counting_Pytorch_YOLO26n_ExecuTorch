"""Run in Google Colab or a compatible Linux environment."""
from ultralytics import YOLO

MODEL = "yolo26n.pt"
IMAGE_SIZE = 640

model = YOLO(MODEL)
exported = model.export(
    format="executorch",
    imgsz=IMAGE_SIZE,
    batch=1,
    device="cpu",
)
print("Export output:", exported)
print("Copy the generated yolo26n_executorch_model directory to backend/models/")
