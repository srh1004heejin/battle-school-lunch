from datetime import date
from typing import Any

import httpx
import pytest
from pydantic import ValidationError

from app.config import Settings

from conftest import make_client, neis_payload


def school_row(
    name: str = "테스트고등학교",
    office: str = "B10",
    code: str = "7010001",
) -> dict[str, str]:
    return {
        "ATPT_OFCDC_SC_CODE": office,
        "ATPT_OFCDC_SC_NM": "서울특별시교육청",
        "SD_SCHUL_CODE": code,
        "SCHUL_NM": name,
        "LCTN_SC_NM": "서울특별시",
        "ORG_RDNMA": "서울특별시 중구 테스트로 1",
    }


def meal_row(
    service_date: str,
    dishes: str,
    *,
    office: str = "B10",
    code: str = "7010001",
) -> dict[str, str]:
    return {
        "ATPT_OFCDC_SC_CODE": office,
        "SD_SCHUL_CODE": code,
        "SCHUL_NM": "테스트고등학교",
        "MMEAL_SC_CODE": "2",
        "MMEAL_SC_NM": "중식",
        "MLSV_YMD": service_date,
        "DDISH_NM": dishes,
        "CAL_INFO": "700 Kcal",
        "NTR_INFO": "단백질(g) : 25.0<br/>탄수화물(g) : 90.0",
        "ORPLC_INFO": "쌀 : 국내산<br/>돼지고기 : 국내산",
    }


def test_school_search_trims_paginates_sorts_and_deduplicates(
    settings: Settings,
) -> None:
    paged_settings = settings.model_copy(update={"neis_page_size": 2})
    seen_pages: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/hub/schoolInfo"
        assert request.url.params["KEY"] == "test-key"
        assert request.url.params["SCHUL_NM"] == "테스트"
        page = int(request.url.params["pIndex"])
        seen_pages.append(page)
        rows = (
            [school_row("나학교", code="7010002"), school_row("가학교")]
            if page == 1
            else [school_row("가학교")]
        )
        return httpx.Response(200, json=neis_payload("schoolInfo", rows, total=3))

    with make_client(paged_settings, handler) as client:
        response = client.get("/api/schools", params={"query": "  테스트  "})

    assert response.status_code == 200
    assert seen_pages == [1, 2]
    assert [item["name"] for item in response.json()["schools"]] == [
        "가학교",
        "나학교",
    ]
    assert response.json()["schools"][0]["educationOfficeCode"] == "B10"
    assert response.headers["X-Request-ID"]


def test_meal_lookup_verifies_school_and_returns_sorted_unique_meals(
    settings: Settings,
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/hub/schoolInfo":
            return httpx.Response(
                200, json=neis_payload("schoolInfo", [school_row()])
            )
        assert request.url.path == "/hub/mealServiceDietInfo"
        assert request.url.params["MMEAL_SC_CODE"] == "2"
        assert request.url.params["MLSV_FROM_YMD"] == "20260301"
        assert request.url.params["MLSV_TO_YMD"] == "20260303"
        rows = [
            meal_row("20260303", "밥<br/>김치 (1.2.5.6.)"),
            meal_row("20260301", "국수"),
            meal_row("20260303", "중복 메뉴"),
        ]
        return httpx.Response(
            200, json=neis_payload("mealServiceDietInfo", rows)
        )

    with make_client(settings, handler) as client:
        response = client.get(
            "/api/schools/B10/7010001/meals",
            params={
                "from": "2026-03-01",
                "to": "2026-03-03",
                "mealType": "lunch",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["from"] == "2026-03-01"
    assert [meal["date"] for meal in body["meals"]] == [
        "2026-03-01",
        "2026-03-03",
    ]
    assert body["meals"][1]["menu"] == ["밥", "김치 (1.2.5.6.)"]
    assert body["meals"][0]["nutrition"]["단백질(g)"] == "25.0"
    assert len(requests) == 2


def test_no_data_is_a_successful_empty_search(settings: Settings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"RESULT": {"CODE": "INFO-200", "MESSAGE": "데이터가 없습니다."}},
        )

    with make_client(settings, handler) as client:
        response = client.get("/api/schools", params={"query": "없는학교"})

    assert response.status_code == 200
    assert response.json() == {"schools": []}


@pytest.mark.parametrize(
    ("params", "status", "code"),
    [
        ({"query": "   "}, 400, "EMPTY_QUERY"),
        ({"query": "x" * 101}, 422, "INPUT_VALIDATION_ERROR"),
    ],
)
def test_search_validation_blocks_upstream(
    settings: Settings,
    params: dict[str, str],
    status: int,
    code: str,
) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500)

    with make_client(settings, handler) as client:
        response = client.get("/api/schools", params=params)

    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert response.json()["error"]["requestId"]
    assert calls == 0


@pytest.mark.parametrize(
    ("path", "params", "status", "code"),
    [
        (
            "/api/schools/bad!/7010001/meals",
            {
                "from": "2026-01-01",
                "to": "2026-01-02",
                "mealType": "lunch",
            },
            400,
            "INVALID_SCHOOL_CODE",
        ),
        (
            "/api/schools/B10/7010001/meals",
            {
                "from": "2026-02-30",
                "to": "2026-03-01",
                "mealType": "lunch",
            },
            422,
            "INVALID_DATE",
        ),
        (
            "/api/schools/B10/7010001/meals",
            {
                "from": "2026-03-02",
                "to": "2026-03-01",
                "mealType": "lunch",
            },
            400,
            "INVALID_DATE_RANGE",
        ),
        (
            "/api/schools/B10/7010001/meals",
            {
                "from": "2026-01-01",
                "to": "2027-01-02",
                "mealType": "lunch",
            },
            422,
            "DATE_RANGE_TOO_LARGE",
        ),
        (
            "/api/schools/B10/7010001/meals",
            {"from": "2026-01-01", "to": "2026-01-02"},
            422,
            "INPUT_VALIDATION_ERROR",
        ),
        (
            "/api/schools/B10/7010001/meals",
            {
                "from": "2026-01-01",
                "to": "2026-01-02",
                "mealType": "dinner",
            },
            422,
            "INPUT_VALIDATION_ERROR",
        ),
    ],
)
def test_meal_input_validation_blocks_upstream(
    settings: Settings,
    path: str,
    params: dict[str, str],
    status: int,
    code: str,
) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500)

    with make_client(settings, handler) as client:
        response = client.get(path, params=params)

    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert calls == 0


def test_unknown_school_returns_404(settings: Settings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"RESULT": {"CODE": "INFO-200", "MESSAGE": "데이터가 없습니다."}},
        )

    with make_client(settings, handler) as client:
        response = client.get(
            "/api/schools/B10/7010001/meals",
            params={
                "from": "2026-01-01",
                "to": "2026-01-02",
                "mealType": "lunch",
            },
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SCHOOL_NOT_FOUND"


@pytest.mark.parametrize(
    ("outcome", "status", "code"),
    [
        ("timeout", 504, "NEIS_TIMEOUT"),
        ("network", 503, "NEIS_UNAVAILABLE"),
        ("server", 503, "NEIS_UNAVAILABLE"),
        ("invalid-json", 502, "NEIS_BAD_RESPONSE"),
        ("neis-error", 502, "NEIS_BAD_RESPONSE"),
    ],
)
def test_upstream_failures_have_stable_mapping(
    settings: Settings, outcome: str, status: int, code: str
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if outcome == "timeout":
            raise httpx.ReadTimeout("slow", request=request)
        if outcome == "network":
            raise httpx.ConnectError("offline", request=request)
        if outcome == "server":
            return httpx.Response(500)
        if outcome == "invalid-json":
            return httpx.Response(200, content=b"not-json")
        return httpx.Response(
            200,
            json={"RESULT": {"CODE": "ERROR-290", "MESSAGE": "invalid key"}},
        )

    with make_client(settings, handler) as client:
        response = client.get("/api/schools", params={"query": "학교"})

    assert response.status_code == status
    assert response.json()["error"]["code"] == code


def test_transient_server_failure_is_retried(settings: Settings) -> None:
    retry_settings = settings.model_copy(update={"neis_max_retries": 2})
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls < 3:
            return httpx.Response(503)
        return httpx.Response(
            200, json=neis_payload("schoolInfo", [school_row()])
        )

    with make_client(retry_settings, handler) as client:
        response = client.get("/api/schools", params={"query": "학교"})

    assert response.status_code == 200
    assert calls == 3


def test_health_does_not_call_neis(settings: Settings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("health must not call NEIS")

    with make_client(settings, handler) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_key_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NEIS_API_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
