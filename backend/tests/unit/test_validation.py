from __future__ import annotations

from datetime import date

import pytest

from app.errors import ApiError
from app.validation import parse_api_date, validate_date_range, validate_school_identifier, validate_search_query


def test_validate_search_query_trims_whitespace() -> None:
    assert validate_search_query("  한국중학교  ") == "한국중학교"


def test_validate_search_query_rejects_empty_string() -> None:
    with pytest.raises(ApiError) as error:
        validate_search_query("   ")

    assert error.value.status_code == 400
    assert error.value.code == "EMPTY_QUERY"


def test_validate_school_identifier_rejects_invalid_characters() -> None:
    with pytest.raises(ApiError) as error:
        validate_school_identifier("B10-01", "educationOfficeCode")

    assert error.value.status_code == 400
    assert error.value.code == "INVALID_SCHOOL_IDENTIFIER"


def test_parse_api_date_rejects_impossible_calendar_dates() -> None:
    with pytest.raises(ApiError) as error:
        parse_api_date("2026-02-31", "from")

    assert error.value.status_code == 422
    assert error.value.code == "INVALID_DATE"


def test_validate_date_range_rejects_ranges_that_are_too_large() -> None:
    with pytest.raises(ApiError) as error:
        validate_date_range(date(2026, 8, 1), date(2026, 9, 15), 31)

    assert error.value.status_code == 422
    assert error.value.code == "DATE_RANGE_TOO_LARGE"
