"""
PragyanAI Video People Counting
YOLO26n + PyTorch + ExecuTorch

Backend configuration
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # YOLO26n ExecuTorch model directory
    model_path: str = "models"

    # Frontend URL
    frontend_origin: str = (
        "https://pragyan-yoloexecutorch.netlify.app"
    )

    # Video upload directory
    upload_dir: str = "/tmp/pragyanai_uploads"

    # Processed video and analytics directory
    output_dir: str = "/tmp/pragyanai_outputs"

    # Maximum upload size: 500 MB
    max_upload_size: int = 524_288_000

    # Process every Nth frame
    default_frame_interval: int = 1

    # YOLO input image size
    yolo_image_size: int = 640

    # Detection confidence threshold
    default_confidence: float = 0.35

    @property
    def backend_dir(self) -> Path:

        return Path(__file__).resolve().parent

    @property
    def resolved_model_path(self) -> Path:

        path = Path(self.model_path).expanduser()

        if not path.is_absolute():
            path = self.backend_dir / path

        return path.resolve()

    @property
    def model_file_path(self) -> Path:

        return self.resolved_model_path / "model.pte"

    @property
    def metadata_file_path(self) -> Path:

        return self.resolved_model_path / "metadata.yaml"

    @property
    def upload_path(self) -> Path:

        return Path(self.upload_dir).expanduser().resolve()

    @property
    def output_path(self) -> Path:

        return Path(self.output_dir).expanduser().resolve()

    def create_storage_directories(self):

        self.upload_path.mkdir(
            parents=True,
            exist_ok=True
        )

        self.output_path.mkdir(
            parents=True,
            exist_ok=True
        )


settings = Settings()

settings.create_storage_directories()
