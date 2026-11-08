# PragyanAI Video People Counting

Full-stack video object detection and people-counting application.

- Model: Ultralytics YOLO26n exported to ExecuTorch (`.pte`)
- Runtime: Ultralytics ExecuTorch integration
- Tracking: Supervision ByteTrack
- Video: OpenCV
- Backend: FastAPI
- Frontend: React + Vite
- Backend hosting: Render
- Frontend hosting: Netlify

## 1. Repository layout

```text
backend/     FastAPI API, inference, tracking, video processing
frontend/    React + Vite dashboard
render.yaml  Render backend service
netlify.toml Netlify frontend configuration
```

## 2. Model files required

The repository intentionally does not contain a fabricated or placeholder model binary.
Export the real model in Google Colab:

```python
from ultralytics import YOLO

model = YOLO("yolo26n.pt")
model.export(format="executorch", imgsz=640, batch=1, device="cpu")
```

Ultralytics creates:

```text
yolo26n_executorch_model/
    model.pte
    metadata.yaml
```

Copy the entire directory into:

```text
backend/models/yolo26n_executorch_model/
```

Set `MODEL_PATH=models/yolo26n_executorch_model` on Render. The backend loads the directory using the documented Ultralytics YOLO interface.

**Important:** The `.pt` file is the PyTorch source model. Render needs the exported `.pte` plus metadata directory. Do not rename a `.pt` file to `.pte`.

## 3. Run backend locally

Use Python 3.11.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install --index-url https://download.pytorch.org/whl/cpu torch==2.9.1 torchvision==0.24.1
pip install -r requirements.txt
```

Add the exported model directory, then:

```bash
cp .env.example .env
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs

## 4. Run frontend locally

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open http://localhost:5173.

Set `VITE_API_BASE_URL=http://localhost:8000` in `frontend/.env`.

## 5. Render deployment

This repository includes `render.yaml`. Connect the repository to Render and create the web service from the Blueprint. If configuring manually:

- Root directory: `backend`
- Build command: install CPU PyTorch first, then `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

Environment variables:
- `MODEL_PATH=models/yolo26n_executorch_model`
- `FRONTEND_ORIGIN=https://YOUR-NETLIFY-SITE.netlify.app`
- `UPLOAD_DIR=/tmp/pragyanai_uploads`
- `OUTPUT_DIR=/tmp/pragyanai_outputs`
- `MAX_UPLOAD_SIZE=524288000`
- `DEFAULT_FRAME_INTERVAL=1`
- `YOLO_IMAGE_SIZE=640`

The included Render build command uses CPU PyTorch wheels. Confirm the exact wheel availability for the selected Render Python/runtime before production rollout.

## 6. Netlify deployment

Import the same GitHub repository into Netlify:

- Base directory: `frontend`
- Build command: `npm run build`
- Publish directory: `dist`

Set:
`VITE_API_BASE_URL=https://YOUR-RENDER-SERVICE.onrender.com`

Redeploy after changing Vite environment variables.

## 7. API endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Backend and model readiness |
| GET | `/api/model-info` | Model details |
| POST | `/api/jobs` | Upload video and create processing job |
| GET | `/api/jobs/{job_id}` | Lightweight live job status |
| GET | `/api/jobs/{job_id}/analytics` | Job analytics |
| GET | `/api/jobs/{job_id}/video` | Download annotated MP4 |
| GET | `/api/jobs/{job_id}/csv` | Download frame CSV |
| GET | `/api/jobs/{job_id}/json` | Download JSON report |
| DELETE | `/api/jobs/{job_id}` | Delete job and its files |

## 8. Notes and limitations

- Job metadata is held in process memory. A Render restart clears active jobs.
- `/tmp` is ephemeral. Use persistent/object storage for outputs that must survive restarts.
- Start with short videos and benchmark the actual Render instance.
- `frame_interval=1` processes every frame. Larger values reduce inference calls but can reduce tracking continuity.
- Unique people means distinct ByteTrack IDs observed in this video, not guaranteed real-world identity deduplication. Occlusion and re-entry can cause ID switches.
- This implementation tracks all detected classes and counts class `person` (COCO class ID 0).
- The app uses an in-process background task. For high traffic or long-running production workloads, move jobs to a durable queue/worker and shared database/storage.
- Verify model export and real-video inference in Colab before deploying.

## 9. License

Review Ultralytics licensing and model terms before commercial deployment. This repository's application code is provided separately from model weights and third-party dependencies.
