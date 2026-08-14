from __future__ import annotations

from datetime import date
import re

from .errors import McpServiceError

_SCHOOL_IDENTIFIER = re.compile(r"^[A-Za-z0-9]+$")


def validate_search_query(query: str) -> str:
    normalized = query.strip()
    if not normalized:
        raise McpServiceError("INVALID_QUERY", "학교 검색어를 입력해 주세요.")
    if len(normalized) > 100:
        raise McpServiceError("INVALID_QUERY", "학교 검색어는 100자 이하여야 합니다.")
    return normalized


def validate_school_identifier(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized or not _SCHOOL_IDENTIFIER.fullmatch(normalized):
        raise McpServiceError("INVALID_SCHOOL_IDENTIFIER", f"{field_name} 형식이 올바르지 않습니다.")
    return normalized


def parse_date(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise McpServiceError("INVALID_DATE", f"{field_name}은 YYYY-MM-DD 형식의 실제 날짜여야 합니다.") from exc


def validate_date_range(from_date: date, to_date: date, maximum_days: int) -> None:
    if from_date > to_date:
        raise McpServiceError("INVALID_DATE_RANGE", "시작일은 종료일보다 늦을 수 없습니다.")
    if (to_date - from_date).days + 1 > maximum_days:
        raise McpServiceError("INVALID_DATE_RANGE", f"조회 기간은 최대 {maximum_days}일입니다.")
