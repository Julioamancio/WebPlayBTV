from functools import lru_cache
from pathlib import Path
from typing import List, Union

from pydantic import BaseSettings, Field, validator


class Settings(BaseSettings):
    """Application configuration loaded from environment variables or .env."""

    app_name: str = Field(default="WEBplayer JTV API", env="APP_NAME")
    database_url: str = Field(default="sqlite:///./webplay.db", env="DATABASE_URL")
    jwt_secret: str = Field(default="change-me-in-env", env="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    cors_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "file://",
        ],
        env="CORS_ORIGINS",
    )
    cookie_jar_max: int = Field(default=32, env="COOKIE_JAR_MAX")
    cookie_jar_ttl_seconds: int = Field(default=3600, env="COOKIE_JAR_TTL_SECONDS")
    frontend_directory: Path = Field(
        default=Path(__file__).resolve().parents[2] / "frontend",
        env="FRONTEND_DIRECTORY",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @validator("cors_origins", pre=True)
    def parse_cors_origins(
        cls, value: Union[str, List[str]]
    ) -> Union[str, List[str]]:
        if isinstance(value, str):
            if value.startswith("[") and value.endswith("]"):
                value = value.strip("[]")
                items = [item.strip().strip("'\"") for item in value.split(",")]
                return [item for item in items if item]
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @validator("frontend_directory", pre=True)
    def ensure_frontend_path(cls, value: Union[str, Path]) -> Path:
        path = Path(value)
        if not path.is_absolute():
            base = Path(__file__).resolve().parents[2]
            path = (base / path).resolve()
        return path


@lru_cache()
def get_settings() -> Settings:
    return Settings()

