from __future__ import annotations

from collections import defaultdict

import httpx
import pytest

from app.errors import ApiError
from app.neis_client import NeisClient
from app.settings import Settings


def build_settings() -> Settings:
    return Settings.model_validate(
        {
            "neis_api_key": "test-api-key",
            "neis_base_url": "https://mock-neis.test/hub",
            "retry_attempts": 1,
            "neis_page_size": 1,
        }
    )


@pytest.mark.asyncio
async def test_search_schools_collects_multiple_pages() -> None:
    request_counts: defaultdict[str, int] = defaultdict(int)

    def handler(request: httpx.Request) -> httpx.Response:
        request_counts[request.url.params["pIndex"]] += 1
        page_index = int(request.url.params["pIndex"])
        payload = {
            "schoolInfo": [
                {
                    "head": [
                        {"list_total_count": 2},
                        {"RESULT": {"CODE": "INFO-000", "MESSAGE": "정상 처리되었습니다."}},
                    ]
                },
                {
                    "row": [
                        {
                            "ATPT_OFCDC_SC_CODE": f"B1{page_index}",
                            "ATPT_OFCDC_SC_NM": "서울특별시교육청",
                            "SD_SCHUL_CODE": f"701000{page_index}",
                            "SCHUL_NM": "테스트학교",
                            "LCTN_SC_NM": "서울",
                            "ORG_RDNMA": f"서울특별시 예시로 {page_index}",
                        }
                    ]
                },
            ]
        }
        return httpx.Response(200, json=payload)

    client = NeisClient(build_settings(), transport=httpx.MockTransport(handler))
    try:
        schools = await client.search_schools("테스트")
    finally:
        await client.aclose()

    assert [school.schoolCode for school in schools] == ["7010001", "7010002"]
    assert request_counts == {"1": 1, "2": 1}


@pytest.mark.asyncio
async def test_client_retries_retryable_neis_result_codes_before_failing() -> None:
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(200, json={"RESULT": {"CODE": "ERROR-500", "MESSAGE": "서버 오류입니다."}})

    client = NeisClient(build_settings(), transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(ApiError) as error:
            await client.search_schools("장애학교")
    finally:
        await client.aclose()

    assert attempts == 2
    assert error.value.status_code == 502
    assert error.value.code == "NEIS_UPSTREAM_ERROR"


@pytest.mark.asyncio
async def test_client_maps_timeout_to_504() -> None:
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ReadTimeout("timed out")

    client = NeisClient(build_settings(), transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(ApiError) as error:
            await client.search_schools("시간초과학교")
    finally:
        await client.aclose()

    assert error.value.status_code == 504
    assert error.value.code == "NEIS_TIMEOUT"
    assert attempts == 2


@pytest.mark.asyncio
async def test_client_maps_connection_errors_to_503() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    client = NeisClient(build_settings(), transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(ApiError) as error:
            await client.search_schools("오프라인학교")
    finally:
        await client.aclose()

    assert error.value.status_code == 503
    assert error.value.code == "NEIS_UNAVAILABLE"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        [],
        {
            "mealServiceDietInfo": [
                {
                    "head": [
                        {"list_total_count": 1},
                        {"RESULT": {"CODE": "INFO-000", "MESSAGE": "정상 처리되었습니다."}},
                    ]
                },
                {
                    "row": [
                        {
                            "ATPT_OFCDC_SC_CODE": "B10",
                            "SD_SCHUL_CODE": "7010001",
                            "SCHUL_NM": "테스트학교",
                            "MMEAL_SC_CODE": "2",
                            "MLSV_YMD": "20260230",
                            "DDISH_NM": " ",
                        }
                    ]
                },
            ]
        },
    ],
)
async def test_client_rejects_malformed_neis_meal_payloads(payload: object) -> None:
    client = NeisClient(
        build_settings(),
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload)),
    )
    try:
        with pytest.raises(ApiError) as error:
            await client.get_lunch_meals("B10", "7010001", "2026-02-01", "2026-02-28")
    finally:
        await client.aclose()

    assert error.value.status_code == 502
    assert error.value.code == "NEIS_BAD_RESPONSE"
