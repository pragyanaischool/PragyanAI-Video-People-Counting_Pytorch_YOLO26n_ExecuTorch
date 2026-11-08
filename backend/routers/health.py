from fastapi import APIRouter
from config import settings
from services.inference import model_info

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    info = model_info()
    return {
        "status": "healthy" if info["model_files_present"] else "degraded",
        "backend_connected": True,
        "model_loaded": info["loaded"],
        "model_files_present": info["model_files_present"],
        "model": info["model"],
        "format": info["format"],
    }


@router.get("/api/model-info")
def get_model_info():
    return model_info()
