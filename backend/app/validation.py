from __future__ import annotations

from datetime import date
import re

from .errors import ApiError

_SCHOOL_IDENTIFIER_PATTERN = re.compile(r"^[A-Z0-9]+$")


def validate_search_query(query: str) -> str:
    normalized = query.strip()
    if not normalized:
        raise ApiError(400, "EMPTY_QUERY", "학교 이름을 입력한 후 다시 시도해 주세요.")
    if len(normalized) > 100:
        raise ApiError(422, "QUERY_TOO_LONG", "학교 검색어는 100자를 넘길 수 없습니다.")
    return normalized


def validate_school_identifier(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized or not _SCHOOL_IDENTIFIER_PATTERN.fullmatch(normalized):
        raise ApiError(400, "INVALID_SCHOOL_IDENTIFIER", f"{field_name} 값이 올바르지 않습니다.")
    return normalized


def parse_api_date(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ApiError(
            422,
            "INVALID_DATE",
            f"{field_name} 값은 YYYY-MM-DD 형식의 실제 날짜여야 합니다.",
        ) from exc


def validate_date_range(from_date: date, to_date: date, max_date_range_days: int) -> None:
    if from_date > to_date:
        raise ApiError(400, "INVALID_DATE_RANGE", "시작일은 종료일보다 늦을 수 없습니다.")

    span = (to_date - from_date).days + 1
    if span > max_date_range_days:
        raise ApiError(
            422,
            "DATE_RANGE_TOO_LARGE",
            f"조회 기간은 최대 {max_date_range_days}일까지 선택할 수 있습니다.",
        )
