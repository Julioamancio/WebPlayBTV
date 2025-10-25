from functools import lru_cache
from pathlib import Path
from typing import List, Union

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = "change-me-in-env"


class Settings(BaseSettings):
    """Application configuration loaded from environment variables or .env."""

    app_name: str = Field(default="WEBplayer JTV API", env="APP_NAME")
    database_url: str = Field(default="sqlite:///./webplay.db", env="DATABASE_URL")
    jwt_secret: str = Field(default=DEFAULT_JWT_SECRET, env="JWT_SECRET")
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
    allow_insecure_defaults: bool = Field(default=False, env="ALLOW_INSECURE_DEFAULTS")
    frontend_directory: Path = Field(
        default=Path(__file__).resolve().parents[3] / "frontend",
        env="FRONTEND_DIRECTORY",
    )
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
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

    @field_validator("frontend_directory", mode="before")
    @classmethod
    def ensure_frontend_path(cls, value: Union[str, Path]) -> Path:
        if isinstance(value, Path):
            path = value
        else:
            value_str = str(value).strip()
            if not value_str:
                value_str = "frontend"
            path = Path(value_str)
        if not path.is_absolute():
            base = Path(__file__).resolve().parents[3]
            path = (base / path).resolve()
        if not path.exists():
            fallback = (Path(__file__).resolve().parents[3] / "frontend").resolve()
            if fallback.exists():
                return fallback
            raise ValueError(
                f"Configured frontend directory '{path}' does not exist. "
                "Adjust FRONTEND_DIRECTORY in the environment or ensure the frontend assets are present."
            )
        return path

    @field_validator("database_url", mode="before")
    @classmethod
    def ensure_sqlite_path(cls, value: str) -> str:
        if value.startswith("sqlite:///"):
            raw_path = value.replace("sqlite:///", "", 1)
            db_path = Path(raw_path)
            if not db_path.is_absolute():
                base = Path(__file__).resolve().parents[2]
                db_path = (base / db_path).resolve()
            return f"sqlite:///{db_path.as_posix()}"
        return value

    @model_validator(mode="after")
    def validate_sensitive_defaults(self) -> "Settings":
        if not self.allow_insecure_defaults and self.jwt_secret == DEFAULT_JWT_SECRET:
            raise ValueError(
                "JWT_SECRET is using the placeholder value. Define a strong secret in your environment "
                "or set ALLOW_INSECURE_DEFAULTS=1 for local development only."
            )
        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()
