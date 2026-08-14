from collections.abc import Callable
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def neis_payload(
    service: str, rows: list[dict[str, Any]], *, total: int | None = None
) -> dict[str, Any]:
    return {
        service: [
            {
                "head": [
                    {"list_total_count": len(rows) if total is None else total},
                    {"RESULT": {"CODE": "INFO-000", "MESSAGE": "정상 처리되었습니다."}},
                ]
            },
            {"row": rows},
        ]
    }


@pytest.fixture
def settings() -> Settings:
    return Settings(
        neis_api_key="test-key",
        neis_base_url="https://neis.test/hub",
        neis_timeout_seconds=0.1,
        neis_connect_timeout_seconds=0.1,
        neis_max_retries=0,
        neis_page_size=100,
    )


def make_client(
    settings: Settings, handler: Callable[[httpx.Request], httpx.Response]
) -> TestClient:
    transport = httpx.MockTransport(handler)
    return TestClient(create_app(settings, transport=transport))

