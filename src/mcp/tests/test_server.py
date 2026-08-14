from __future__ import annotations

import json

import httpx
import mcp.types as types
import pytest

from app.main import create_mcp_server
from app.neis_client import NeisClient
from app.settings import Settings


def _result_payload(result: object) -> dict[str, object]:
    structured_content = getattr(result, "structuredContent")
    assert isinstance(structured_content, dict)
    return structured_content


@pytest.mark.asyncio
async def test_mcp_server_lists_and_calls_tools() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/schoolInfo"):
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
        raise AssertionError(f"Unexpected request: {request.url}")

    client = NeisClient(
        Settings(neis_api_key="secret", neis_base_url="https://neis.test/hub", retry_attempts=0),
        transport=httpx.MockTransport(handler),
    )
    server = create_mcp_server(client, 31)
    try:
        tools = await server.request_handlers[types.ListToolsRequest](
            types.ListToolsRequest(method="tools/list")
        )
        call_result = await server.request_handlers[types.CallToolRequest](
            types.CallToolRequest(
                method="tools/call",
                params=types.CallToolRequestParams(name="search_schools", arguments={"query": "한국"}),
            )
        )
    finally:
        await client.aclose()

    tool_names = {tool.name for tool in tools.root.tools}
    assert tool_names == {"search_schools", "get_lunch_meals"}
    payload = _result_payload(call_result.root)
    assert payload["schools"][0]["schoolCode"] == "7010570"
    assert "secret" not in json.dumps(payload)


@pytest.mark.asyncio
async def test_empty_school_result_is_mcp_tool_error() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"RESULT": {"CODE": "INFO-200", "MESSAGE": "없음"}})

    client = NeisClient(
        Settings(neis_api_key="secret", neis_base_url="https://neis.test/hub", retry_attempts=0),
        transport=httpx.MockTransport(handler),
    )
    server = create_mcp_server(client, 31)
    try:
        result = await server.request_handlers[types.CallToolRequest](
            types.CallToolRequest(
                method="tools/call",
                params=types.CallToolRequestParams(name="search_schools", arguments={"query": "없음"}),
            )
        )
    finally:
        await client.aclose()

    assert result.root.isError is True
    assert _result_payload(result.root)["code"] == "SCHOOL_NOT_FOUND"
