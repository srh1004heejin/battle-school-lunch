from __future__ import annotations

import os
from collections.abc import Mapping

from pydantic import BaseModel, Field, ValidationError, field_validator


class Settings(BaseModel):
    app_name: str = "Battle School Lunch API"
    neis_api_key: str
    neis_base_url: str = "https://open.neis.go.kr/hub"
    backend_cors_origin: str | None = None
    request_timeout_seconds: float = Field(default=10.0, gt=0)
    connect_timeout_seconds: float = Field(default=5.0, gt=0)
    neis_page_size: int = Field(default=1000, ge=1, le=1000)
    max_date_range_days: int = Field(default=31, ge=1, le=366)
    retry_attempts: int = Field(default=1, ge=0, le=3)
    agent_mcp_url: str = "http://127.0.0.1:8001/mcp"
    github_copilot_model: str | None = None
    github_copilot_timeout_seconds: float = Field(default=180.0, gt=0, le=600)
    database_path: str = "data/analyses.db"

    @field_validator("neis_api_key")
    @classmethod
    def validate_api_key(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("NEIS_API_KEY must not be empty.")
        return value.strip()

    @field_validator("neis_base_url")
    @classmethod
    def normalize_base_url(cls, value: str) -> str:
        normalized = value.strip().rstrip("/")
        if not normalized:
            raise ValueError("NEIS_BASE_URL must not be empty.")
        return normalized

    @field_validator("backend_cors_origin")
    @classmethod
    def normalize_optional_origin(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().rstrip("/")
        return normalized or None

    @field_validator("agent_mcp_url")
    @classmethod
    def normalize_agent_mcp_url(cls, value: str) -> str:
        normalized = value.strip().rstrip("/")
        if not normalized:
            raise ValueError("AGENT_MCP_URL must not be empty.")
        return normalized

    @field_validator("github_copilot_model")
    @classmethod
    def normalize_optional_model(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("database_path")
    @classmethod
    def normalize_database_path(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("DATABASE_PATH must not be empty.")
        return normalized

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "Settings":
        env = environ if environ is not None else os.environ
        api_key = env.get("NEIS_API_KEY")
        if api_key is None:
            raise RuntimeError(
                "Missing required environment variable NEIS_API_KEY. "
                "Copy .env.example to .env and set a server-side API key."
            )

        raw_settings = {
            "app_name": env.get("APP_NAME", "Battle School Lunch API"),
            "neis_api_key": api_key,
            "neis_base_url": env.get("NEIS_BASE_URL", "https://open.neis.go.kr/hub"),
            "backend_cors_origin": env.get("BACKEND_CORS_ORIGIN"),
            "request_timeout_seconds": env.get("REQUEST_TIMEOUT_SECONDS", "10"),
            "connect_timeout_seconds": env.get("CONNECT_TIMEOUT_SECONDS", "5"),
            "neis_page_size": env.get("NEIS_PAGE_SIZE", "1000"),
            "max_date_range_days": env.get("MAX_DATE_RANGE_DAYS", "31"),
            "retry_attempts": env.get("RETRY_ATTEMPTS", "1"),
            "agent_mcp_url": env.get("AGENT_MCP_URL", "http://127.0.0.1:8001/mcp"),
            "github_copilot_model": env.get("GITHUB_COPILOT_MODEL"),
            "github_copilot_timeout_seconds": env.get("GITHUB_COPILOT_TIMEOUT_SECONDS", "180"),
            "database_path": env.get("DATABASE_PATH", "data/analyses.db"),
        }

        try:
            return cls.model_validate(raw_settings)
        except ValidationError as exc:
            raise RuntimeError(f"Invalid backend configuration: {exc}") from exc
