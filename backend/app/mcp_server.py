from __future__ import annotations

import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

from .validation import parse_api_date, validate_school_identifier

mcp = FastMCP(
    "battle-school-lunch",
    stateless_http=True,
    host=os.getenv("MCP_HOST", "127.0.0.1"),
    port=int(os.getenv("MCP_SERVER_PORT", "8001")),
)


@mcp.tool()
async def get_lunch_meal(
    education_office_code: str,
    school_code: str,
    meal_date: str,
) -> dict[str, Any]:
    """기존 급식 백엔드에서 학교의 특정 날짜 중식 정보를 조회합니다."""
    normalized_office_code = validate_school_identifier(education_office_code, "educationOfficeCode")
    normalized_school_code = validate_school_identifier(school_code, "schoolCode")
    normalized_date = parse_api_date(meal_date, "mealDate").isoformat()
    backend_url = os.getenv("BACKEND_INTERNAL_URL", "http://127.0.0.1:8000").rstrip("/")
    path = f"/api/schools/{normalized_office_code}/{normalized_school_code}/meals"
    async with httpx.AsyncClient(base_url=backend_url, timeout=15.0) as client:
        response = await client.get(
            path,
            params={"from": normalized_date, "to": normalized_date, "mealType": "lunch"},
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
    return payload


def main() -> None:
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
