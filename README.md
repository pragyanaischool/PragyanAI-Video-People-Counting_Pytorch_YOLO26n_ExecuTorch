# Export YOLO26n for this backend

In Google Colab:

```bash
pip install ultralytics
```

```python
from ultralytics import YOLO
model = YOLO("yolo26n.pt")
model.export(format="executorch", imgsz=640, batch=1, device="cpu")
```

Test the export:

```python
from ultralytics import YOLO
model = YOLO("yolo26n_executorch_model")
results = model("https://ultralytics.com/images/bus.jpg")
print(results[0].boxes)
```

Copy `yolo26n_executorch_model/` into `backend/models/`.
