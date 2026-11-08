import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers.health import router as health_router
from routers.jobs import router as jobs_router
from routers.downloads import router as downloads_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("pragyanai")

app = FastAPI(
    title="PragyanAI Video People Counting API",
    version="1.0.0",
    description="YOLO26n ExecuTorch video object detection and people counting.",
)

origins = [origin.strip() for origin in settings.frontend_origin.split(",") if origin.strip()]
origins.extend(["http://localhost:5173", "http://127.0.0.1:5173"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(set(origins)),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(jobs_router)
app.include_router(downloads_router)


@app.get("/")
def root():
    return {
        "application": "PragyanAI Video People Counting",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }


@app.on_event("startup")
async def startup_message():
    logger.info("PragyanAI API started")
    logger.info("Configured model path: %s", settings.resolved_model_path)
    logger.info("Model loading is lazy; first model request initializes it.")
