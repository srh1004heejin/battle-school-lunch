from functools import cached_property
from urllib.parse import urlsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    neis_api_key: str = Field(min_length=1)
    neis_base_url: str = "https://open.neis.go.kr/hub"
    neis_timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    neis_connect_timeout_seconds: float = Field(default=3.0, gt=0, le=60)
    neis_max_retries: int = Field(default=2, ge=0, le=5)
    neis_page_size: int = Field(default=100, ge=1, le=1000)
    neis_max_pages: int = Field(default=100, ge=1, le=1000)
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    @field_validator("neis_api_key")
    @classmethod
    def api_key_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("NEIS_API_KEY must not be blank")
        return value

    @field_validator("neis_base_url")
    @classmethod
    def normalize_base_url(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("NEIS_BASE_URL must be an HTTP(S) URL")
        return value

    @cached_property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
