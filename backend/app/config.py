from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings
from pydantic import Field, validator

_DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]


class Settings(BaseSettings):
    llm_backend: str = Field(default="fallback", env="LLM_BACKEND")
    llm_model: str = Field(default="llama3", env="LLM_MODEL")
    api_token: Optional[str] = Field(default=None, env="API_TOKEN")
    task_db_path: Path = Field(default=Path("storage/tasks.db"), env="TASK_DB_PATH")
    cors_allow_origins: List[str] = Field(default_factory=lambda: _DEFAULT_CORS_ORIGINS, env="CORS_ALLOW_ORIGINS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @validator("cors_allow_origins", pre=True)
    def _split_origins(cls, value: object) -> List[str]:
        if value in (None, ""):
            return list(_DEFAULT_CORS_ORIGINS)
        if isinstance(value, str):
            items = [item.strip() for item in value.split(",")]
            cleaned = [item for item in items if item]
            return cleaned or list(_DEFAULT_CORS_ORIGINS)
        if isinstance(value, (list, tuple)):
            return [str(item) for item in value if str(item).strip()]
        raise ValueError("Invalid CORS_ALLOW_ORIGINS value")

    @validator("task_db_path", pre=True)
    def _coerce_path(cls, value: object) -> Path:
        if isinstance(value, Path):
            return value
        if value in (None, ""):
            return Path("storage/tasks.db")
        return Path(str(value))


@lru_cache()
def get_settings() -> Settings:
    return Settings()
