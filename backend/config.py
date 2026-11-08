from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    model_path: str = "models/yolo26n_executorch_model"
    frontend_origin: str = "http://localhost:5173"
    upload_dir: str = "/tmp/pragyanai_uploads"
    output_dir: str = "/tmp/pragyanai_outputs"
    max_upload_size: int = 524_288_000
    default_frame_interval: int = 1
    yolo_image_size: int = 640
    default_confidence: float = 0.35

    @property
    def backend_dir(self) -> Path:
        return Path(__file__).resolve().parent

    @property
    def resolved_model_path(self) -> Path:
        path = Path(self.model_path)
        return path if path.is_absolute() else self.backend_dir / path

    @property
    def upload_path(self) -> Path:
        return Path(self.upload_dir)

    @property
    def output_path(self) -> Path:
        return Path(self.output_dir)


settings = Settings()
settings.upload_path.mkdir(parents=True, exist_ok=True)
settings.output_path.mkdir(parents=True, exist_ok=True)
