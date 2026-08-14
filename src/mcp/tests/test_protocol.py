from __future__ import annotations

import httpx
from starlette.testclient import TestClient

from app.main import create_app
from app.settings import Settings


def test_streamable_http_initializes_lists_and_calls_tools() -> None:
    async def neis_handler(request: httpx.Request) -> httpx.Response:
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
                            }
                        ]
                    },
                ]
            },
        )

    app = create_app(
        Settings(neis_api_key="test-api-key"),
        neis_transport=httpx.MockTransport(neis_handler),
    )
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }

    with TestClient(app) as client:
        initialize_response = client.post(
            "/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1.0"},
                },
            },
        )
        tools_response = client.post(
            "/mcp",
            headers=headers,
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
        call_response = client.post(
            "/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "search_schools", "arguments": {"query": "한국"}},
            },
        )

    assert initialize_response.status_code == 200
    assert initialize_response.json()["result"]["serverInfo"]["name"] == "battle-school-lunch-mcp"
    assert tools_response.status_code == 200
    assert {tool["name"] for tool in tools_response.json()["result"]["tools"]} == {
        "search_schools",
        "get_lunch_meals",
    }
    assert call_response.status_code == 200
    result = call_response.json()["result"]
    assert result["isError"] is False
    assert result["structuredContent"]["schools"][0]["schoolCode"] == "7010570"
