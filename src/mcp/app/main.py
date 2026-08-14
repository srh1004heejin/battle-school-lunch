from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.types import Receive, Scope, Send

from .errors import McpServiceError
from .neis_client import NeisClient
from .settings import Settings
from .validation import (
    parse_date,
    validate_date_range,
    validate_school_identifier,
    validate_search_query,
)


def create_mcp_server(client: NeisClient, max_date_range_days: int) -> Server[None]:
    server: Server[None] = Server(
        "battle-school-lunch-mcp",
        version="0.1.0",
        instructions="NEIS에서 학교를 검색하고 날짜 범위의 중식 정보를 조회합니다.",
    )

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="search_schools",
                description="학교 이름 일부로 후보 학교와 교육청·학교 식별 정보를 조회합니다.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "검색할 학교 이름의 일부",
                            "minLength": 1,
                            "maxLength": 100,
                        }
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
            ),
            types.Tool(
                name="get_lunch_meals",
                description="선택한 학교의 날짜별 중식 메뉴를 조회합니다.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "education_office_code": {"type": "string", "description": "교육청 코드"},
                        "school_code": {"type": "string", "description": "표준학교 코드"},
                        "from_date": {"type": "string", "format": "date", "description": "조회 시작일"},
                        "to_date": {"type": "string", "format": "date", "description": "조회 종료일"},
                    },
                    "required": ["education_office_code", "school_code", "from_date", "to_date"],
                    "additionalProperties": False,
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> types.CallToolResult:
        try:
            if name == "search_schools":
                query = _required_string(arguments, "query")
                schools = await client.search_schools(validate_search_query(query))
                if not schools:
                    raise McpServiceError("SCHOOL_NOT_FOUND", "검색 조건에 맞는 학교가 없습니다.")
                payload = {"schools": [school.model_dump(mode="json", exclude_none=True) for school in schools]}
                return _success_result(payload)

            if name == "get_lunch_meals":
                education_office_code = validate_school_identifier(
                    _required_string(arguments, "education_office_code"),
                    "education_office_code",
                )
                school_code = validate_school_identifier(
                    _required_string(arguments, "school_code"),
                    "school_code",
                )
                from_date = parse_date(_required_string(arguments, "from_date"), "from_date")
                to_date = parse_date(_required_string(arguments, "to_date"), "to_date")
                validate_date_range(from_date, to_date, max_date_range_days)
                meals = await client.get_lunch_meals(
                    education_office_code,
                    school_code,
                    from_date.isoformat(),
                    to_date.isoformat(),
                )
                if not meals:
                    raise McpServiceError("MEALS_NOT_FOUND", "조회 기간에 중식 정보가 없습니다.")
                payload = {
                    "educationOfficeCode": education_office_code,
                    "schoolCode": school_code,
                    "from": from_date.isoformat(),
                    "to": to_date.isoformat(),
                    "meals": [meal.model_dump(mode="json", exclude_none=True) for meal in meals],
                }
                return _success_result(payload)

            raise McpServiceError("TOOL_NOT_FOUND", f"지원하지 않는 도구입니다: {name}")
        except McpServiceError as exc:
            return _error_result(exc.code, exc.message)

    return server


def create_app(
    settings: Settings | None = None,
    neis_transport: httpx.AsyncBaseTransport | None = None,
) -> Starlette:
    config = settings or Settings.from_env()
    client = NeisClient(config, transport=neis_transport)
    mcp_server = create_mcp_server(client, config.max_date_range_days)
    session_manager = StreamableHTTPSessionManager(
        app=mcp_server,
        json_response=True,
        stateless=True,
    )

    @asynccontextmanager
    async def lifespan(_: Starlette) -> AsyncIterator[None]:
        async with session_manager.run():
            try:
                yield
            finally:
                await client.aclose()

    return Starlette(
        routes=[
            Route("/health", endpoint=health),
            Route("/mcp", endpoint=StreamableHttpEndpoint(session_manager), methods=["GET", "POST", "DELETE"]),
        ],
        lifespan=lifespan,
    )


async def health(_: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


class StreamableHttpEndpoint:
    def __init__(self, session_manager: StreamableHTTPSessionManager) -> None:
        self._session_manager = session_manager

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self._session_manager.handle_request(scope, receive, send)


def _required_string(arguments: dict[str, Any], field_name: str) -> str:
    value = arguments.get(field_name)
    if not isinstance(value, str):
        raise McpServiceError("INVALID_INPUT", f"{field_name}은 문자열이어야 합니다.")
    return value


def _success_result(payload: dict[str, Any]) -> types.CallToolResult:
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))],
        structuredContent=payload,
    )


def _error_result(code: str, message: str) -> types.CallToolResult:
    payload = {"code": code, "message": message}
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))],
        structuredContent=payload,
        isError=True,
    )


app = create_app()
