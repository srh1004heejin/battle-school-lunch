from __future__ import annotations

from pathlib import Path
import json

import httpx
import pytest

from app.main import create_app
from app.settings import Settings
from tests.mock_neis.app import create_mock_neis_app


def build_settings() -> Settings:
    return Settings.model_validate(
        {
            "neis_api_key": "test-api-key",
            "neis_base_url": "http://mock-neis.test/hub",
            "backend_cors_origin": "http://localhost:8080",
            "neis_page_size": 1,
        }
    )


@pytest.mark.asyncio
async def test_search_schools_returns_internal_shape() -> None:
    mock_neis_app = create_mock_neis_app()
    backend_app = create_app(
        settings=build_settings(),
        neis_transport=httpx.ASGITransport(app=mock_neis_app),
    )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=backend_app), base_url="http://backend.test") as client:
        response = await client.get("/api/schools", params={"query": "한국중학교"})

    assert response.status_code == 200
    assert response.json()["schools"][0]["name"] == "한국중학교"
    assert mock_neis_app.state.requests[0]["path"] == "/hub/schoolInfo"


@pytest.mark.asyncio
async def test_get_meals_returns_sorted_deduplicated_meals() -> None:
    mock_neis_app = create_mock_neis_app()
    backend_app = create_app(
        settings=build_settings(),
        neis_transport=httpx.ASGITransport(app=mock_neis_app),
    )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=backend_app), base_url="http://backend.test") as client:
        response = await client.get(
            "/api/schools/B10/7010570/meals",
            params={"from": "2026-08-01", "to": "2026-08-02", "mealType": "lunch"},
        )

    body = response.json()
    assert response.status_code == 200
    assert [meal["date"] for meal in body["meals"]] == ["2026-08-01", "2026-08-02"]
    assert "calories" not in body["meals"][0]
    assert "nutrition" not in body["meals"][0]
    assert "origin" not in body["meals"][0]
    assert body["meals"][1]["menu"] == ["잡곡밥 (5.6.)", "된장찌개 (5.6.)"]
    assert sum(1 for request in mock_neis_app.state.requests if request["path"] == "/hub/mealServiceDietInfo") == 3


@pytest.mark.asyncio
async def test_invalid_date_range_returns_400_without_calling_neis() -> None:
    mock_neis_app = create_mock_neis_app()
    backend_app = create_app(
        settings=build_settings(),
        neis_transport=httpx.ASGITransport(app=mock_neis_app),
    )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=backend_app), base_url="http://backend.test") as client:
        response = await client.get(
            "/api/schools/B10/7010570/meals",
            params={"from": "2026-08-03", "to": "2026-08-01", "mealType": "lunch"},
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_DATE_RANGE"
    assert mock_neis_app.state.requests == []


@pytest.mark.asyncio
async def test_school_not_found_returns_404() -> None:
    mock_neis_app = create_mock_neis_app()
    backend_app = create_app(
        settings=build_settings(),
        neis_transport=httpx.ASGITransport(app=mock_neis_app),
    )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=backend_app), base_url="http://backend.test") as client:
        response = await client.get(
            "/api/schools/Z10/1234567/meals",
            params={"from": "2026-08-01", "to": "2026-08-02", "mealType": "lunch"},
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SCHOOL_NOT_FOUND"


@pytest.mark.asyncio
async def test_empty_search_and_empty_meals_return_200_with_empty_arrays() -> None:
    mock_neis_app = create_mock_neis_app()
    backend_app = create_app(
        settings=build_settings(),
        neis_transport=httpx.ASGITransport(app=mock_neis_app),
    )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=backend_app), base_url="http://backend.test") as client:
        search_response = await client.get("/api/schools", params={"query": "없는학교"})
        meals_response = await client.get(
            "/api/schools/G10/0000000/meals",
            params={"from": "2026-08-01", "to": "2026-08-02", "mealType": "lunch"},
        )

    assert search_response.status_code == 200
    assert search_response.json() == {"schools": []}
    assert meals_response.status_code == 200
    assert meals_response.json()["meals"] == []


@pytest.mark.asyncio
async def test_bad_neis_payload_maps_to_502() -> None:
    mock_neis_app = create_mock_neis_app()
    backend_app = create_app(
        settings=build_settings(),
        neis_transport=httpx.ASGITransport(app=mock_neis_app),
    )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=backend_app), base_url="http://backend.test") as client:
        response = await client.get(
            "/api/schools/D10/8888888/meals",
            params={"from": "2026-08-01", "to": "2026-08-02", "mealType": "lunch"},
        )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "NEIS_BAD_RESPONSE"


def test_app_openapi_matches_internal_contract() -> None:
    backend_app = create_app(settings=build_settings(), neis_transport=httpx.MockTransport(lambda request: httpx.Response(200, json={})))
    contract_path = Path(__file__).resolve().parents[3] / "src" / "openapi.json"
    expected_contract = json.loads(contract_path.read_text(encoding="utf-8"))

    assert backend_app.openapi() == expected_contract
