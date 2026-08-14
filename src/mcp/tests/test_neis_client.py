from __future__ import annotations

import httpx
import pytest

from app.errors import McpServiceError
from app.neis_client import NeisClient
from app.settings import Settings


def _settings() -> Settings:
    return Settings(neis_api_key="secret", neis_base_url="https://neis.test/hub", retry_attempts=0)


@pytest.mark.asyncio
async def test_search_schools_maps_identifiers_without_exposing_key() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["Key"] == "secret"
        assert request.url.params["SCHUL_NM"] == "한국"
        return httpx.Response(
            200,
            json={
                "schoolInfo": [
                    {
                        "head": [
                            {"list_total_count": 1},
                            {"RESULT": {"CODE": "INFO-000", "MESSAGE": "정상"}},
                        ]
                    },
                    {
                        "row": [
                            {
                                "ATPT_OFCDC_SC_CODE": "B10",
                                "ATPT_OFCDC_SC_NM": "서울특별시교육청",
                                "SD_SCHUL_CODE": "7010570",
                                "SCHUL_NM": "한국중학교",
                                "LCTN_SC_NM": "서울",
                                "ORG_RDNMA": "서울특별시 중구",
                            }
                        ]
                    },
                ]
            },
        )

    client = NeisClient(_settings(), transport=httpx.MockTransport(handler))
    try:
        schools = await client.search_schools("한국")
    finally:
        await client.aclose()

    assert schools[0].educationOfficeCode == "B10"
    assert schools[0].schoolCode == "7010570"
    assert "secret" not in schools[0].model_dump_json()


@pytest.mark.asyncio
async def test_lunch_request_uses_neis_contract_and_normalizes_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/hub/mealServiceDietInfo"
        assert request.url.params["MMEAL_SC_CODE"] == "2"
        assert request.url.params["MLSV_FROM_YMD"] == "20260801"
        assert request.url.params["MLSV_TO_YMD"] == "20260802"
        return httpx.Response(
            200,
            json={
                "mealServiceDietInfo": [
                    {
                        "head": [
                            {"list_total_count": 1},
                            {"RESULT": {"CODE": "INFO-000", "MESSAGE": "정상"}},
                        ]
                    },
                    {
                        "row": [
                            {
                                "MMEAL_SC_CODE": "2",
                                "MLSV_YMD": "20260801",
                                "DDISH_NM": "현미밥<br/>된장찌개 (5.6.)",
                                "CAL_INFO": "700 Kcal",
                                "NTR_INFO": "단백질: 25g",
                                "ORPLC_INFO": "쌀: 국내산",
                            }
                        ]
                    },
                ]
            },
        )

    client = NeisClient(_settings(), transport=httpx.MockTransport(handler))
    try:
        meals = await client.get_lunch_meals("B10", "7010570", "2026-08-01", "2026-08-02")
    finally:
        await client.aclose()

    assert meals[0].menu == ["현미밥", "된장찌개 (5.6.)"]
    assert meals[0].nutrition == {"단백질": "25g"}


@pytest.mark.asyncio
async def test_timeout_becomes_safe_service_error() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("secret upstream detail")

    client = NeisClient(_settings(), transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(McpServiceError) as exc_info:
            await client.search_schools("한국")
    finally:
        await client.aclose()

    assert exc_info.value.code == "NEIS_TIMEOUT"
    assert "secret upstream detail" not in exc_info.value.message


@pytest.mark.asyncio
async def test_protocol_error_becomes_safe_service_error() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.RemoteProtocolError("secret protocol detail")

    client = NeisClient(_settings(), transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(McpServiceError) as exc_info:
            await client.search_schools("한국")
    finally:
        await client.aclose()

    assert exc_info.value.code == "NEIS_UNAVAILABLE"
    assert "secret protocol detail" not in exc_info.value.message


@pytest.mark.asyncio
async def test_retryable_neis_error_is_retried() -> None:
    attempts = 0

    async def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(200, json={"RESULT": {"CODE": "ERROR-500", "MESSAGE": "internal"}})
        return httpx.Response(200, json={"RESULT": {"CODE": "INFO-200", "MESSAGE": "없음"}})

    settings = Settings(
        neis_api_key="secret",
        neis_base_url="https://neis.test/hub",
        retry_attempts=1,
    )
    client = NeisClient(settings, transport=httpx.MockTransport(handler))
    try:
        schools = await client.search_schools("한국")
    finally:
        await client.aclose()

    assert schools == []
    assert attempts == 2
