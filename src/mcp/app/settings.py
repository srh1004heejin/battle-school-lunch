from __future__ import annotations

import os
from collections.abc import Mapping

from pydantic import BaseModel, Field, ValidationError, field_validator


class Settings(BaseModel):
    neis_api_key: str
    neis_base_url: str = "https://open.neis.go.kr/hub"
    request_timeout_seconds: float = Field(default=10.0, gt=0)
    connect_timeout_seconds: float = Field(default=5.0, gt=0)
    neis_page_size: int = Field(default=1000, ge=1, le=1000)
    max_date_range_days: int = Field(default=31, ge=1, le=366)
    retry_attempts: int = Field(default=1, ge=0, le=3)

    @field_validator("neis_api_key")
    @classmethod
    def validate_api_key(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("NEIS_API_KEY must not be empty.")
        return normalized

    @field_validator("neis_base_url")
    @classmethod
    def normalize_base_url(cls, value: str) -> str:
        normalized = value.strip().rstrip("/")
        if not normalized:
            raise ValueError("NEIS_BASE_URL must not be empty.")
        return normalized

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "Settings":
        env = environ if environ is not None else os.environ
        api_key = env.get("NEIS_API_KEY")
        if api_key is None:
            raise RuntimeError("Missing required environment variable NEIS_API_KEY.")

        try:
            return cls.model_validate(
                {
                    "neis_api_key": api_key,
                    "neis_base_url": env.get("NEIS_BASE_URL", "https://open.neis.go.kr/hub"),
                    "request_timeout_seconds": env.get("REQUEST_TIMEOUT_SECONDS", "10"),
                    "connect_timeout_seconds": env.get("CONNECT_TIMEOUT_SECONDS", "5"),
                    "neis_page_size": env.get("NEIS_PAGE_SIZE", "1000"),
                    "max_date_range_days": env.get("MAX_DATE_RANGE_DAYS", "31"),
                    "retry_attempts": env.get("RETRY_ATTEMPTS", "1"),
                }
            )
        except ValidationError as exc:
            raise RuntimeError(f"Invalid MCP server configuration: {exc}") from exc
