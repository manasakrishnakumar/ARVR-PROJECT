from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ARVR_", env_file=".env", extra="ignore")

    app_name: str = "ARVR Adaptive Rehabilitation API"
    version: str = "0.1.0"
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'arvr.db').as_posix()}"
    exercises_dir: Path = BACKEND_DIR / "app" / "exercises" / "definitions"
    artifacts_dir: Path = BACKEND_DIR.parent / "artifacts"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    store_raw_video: bool = False  # privacy default: never persist camera footage


settings = Settings()

DISCLAIMER = (
    "Research prototype. Not a medical device and not clinically validated. "
    "Follow guidance from your qualified rehabilitation professional."
)
