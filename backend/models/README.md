# Model weights

Copy the actual Ultralytics export output into this directory:

```text
backend/models/yolo26n_executorch_model/
    model.pte
    metadata.yaml
```

Generate in Google Colab:

```python
from ultralytics import YOLO
model = YOLO("yolo26n.pt")
model.export(format="executorch", imgsz=640, batch=1, device="cpu")
```

Do not upload a placeholder file. Do not rename `yolo26n.pt` to `model.pte`.
If the `.pte` file is larger than GitHub's regular file limit, use Git LFS or external model/object storage and download it during deployment.
