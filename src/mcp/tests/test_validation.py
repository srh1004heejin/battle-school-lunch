from __future__ import annotations

from datetime import date

import pytest

from app.errors import McpServiceError
from app.validation import parse_date, validate_date_range, validate_search_query


def test_search_query_is_trimmed() -> None:
    assert validate_search_query("  한국중학교  ") == "한국중학교"


@pytest.mark.parametrize("query", ["", "   "])
def test_empty_search_query_is_rejected(query: str) -> None:
    with pytest.raises(McpServiceError, match="검색어"):
        validate_search_query(query)


def test_invalid_calendar_date_is_rejected() -> None:
    with pytest.raises(McpServiceError, match="실제 날짜"):
        parse_date("2026-02-30", "from_date")


def test_reversed_date_range_is_rejected() -> None:
    with pytest.raises(McpServiceError, match="늦을 수 없습니다"):
        validate_date_range(date(2026, 8, 2), date(2026, 8, 1), 31)
