from __future__ import annotations

from collections.abc import Iterable
from json import JSONDecodeError
import secrets
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from .errors import ApiError, NeisUpstreamResponseError
from .models import MealRecord, SchoolSummary, SelectedSchool
from .neis_schemas import MealServiceDietInfoRow, NeisResultStatus, SchoolInfoRow
from .normalization import (
    dedupe_and_sort_meals,
    dedupe_and_sort_schools,
    normalize_meal,
    normalize_school,
    normalize_selected_school,
)
from .settings import Settings

T = TypeVar("T", bound=BaseModel)

_SUCCESS_CODES = {"000", "100"}
_NO_DATA_CODES = {"200"}
_RETRYABLE_NEIS_CODES = {"500", "600"}


class NeisClient:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> None:
        timeout = httpx.Timeout(
            settings.request_timeout_seconds,
            connect=settings.connect_timeout_seconds,
        )
        self._settings = settings
        self._client = httpx.AsyncClient(
            base_url=settings.neis_base_url,
            timeout=timeout,
            transport=transport,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def search_schools(self, query: str) -> list[SchoolSummary]:
        rows = await self._fetch_paginated_rows(
            "/schoolInfo",
            "schoolInfo",
            SchoolInfoRow,
            {"SCHUL_NM": query},
        )
        return dedupe_and_sort_schools([normalize_school(row) for row in rows])

    async def get_random_schools(self, limit: int = 10) -> list[SchoolSummary]:
        params = {
            "Key": self._settings.neis_api_key,
            "Type": "json",
            "pSize": str(limit),
            "pIndex": "1",
        }
        first_rows, total_count = await self._fetch_page(
            path="/schoolInfo",
            service_key="schoolInfo",
            row_model=SchoolInfoRow,
            params=params,
        )
        full_page_count = total_count // limit
        if full_page_count <= 1:
            rows = first_rows
        else:
            selected_page = secrets.randbelow(full_page_count) + 1
            if selected_page == 1:
                rows = first_rows
            else:
                rows, _ = await self._fetch_page(
                    path="/schoolInfo",
                    service_key="schoolInfo",
                    row_model=SchoolInfoRow,
                    params={**params, "pIndex": str(selected_page)},
                )
        schools = dedupe_and_sort_schools([normalize_school(row) for row in rows])
        if len(schools) < limit:
            raise ApiError(502, "NEIS_BAD_RESPONSE", "무작위 학교 후보를 충분히 가져오지 못했습니다.")
        return schools[:limit]

    async def get_school(self, education_office_code: str, school_code: str) -> SelectedSchool | None:
        rows = await self._fetch_paginated_rows(
            "/schoolInfo",
            "schoolInfo",
            SchoolInfoRow,
            {
                "ATPT_OFCDC_SC_CODE": education_office_code,
                "SD_SCHUL_CODE": school_code,
            },
        )
        if not rows:
            return None
        return normalize_selected_school(rows[0])

    async def get_lunch_meals(
        self,
        education_office_code: str,
        school_code: str,
        from_date: str,
        to_date: str,
    ) -> list[MealRecord]:
        rows = await self._fetch_paginated_rows(
            "/mealServiceDietInfo",
            "mealServiceDietInfo",
            MealServiceDietInfoRow,
            {
                "ATPT_OFCDC_SC_CODE": education_office_code,
                "SD_SCHUL_CODE": school_code,
                "MMEAL_SC_CODE": "2",
                "MLSV_FROM_YMD": from_date.replace("-", ""),
                "MLSV_TO_YMD": to_date.replace("-", ""),
            },
        )
        try:
            meals = [normalize_meal(row) for row in rows if row.meal_code == "2"]
        except (ValueError, ValidationError) as exc:
            raise ApiError(
                502,
                "NEIS_BAD_RESPONSE",
                "급식 외부 서비스 데이터 형식이 계약과 다릅니다.",
            ) from exc
        return dedupe_and_sort_meals(meals)

    async def _fetch_paginated_rows(
        self,
        path: str,
        service_key: str,
        row_model: type[T],
        extra_params: dict[str, str],
    ) -> list[T]:
        params = {
            "Key": self._settings.neis_api_key,
            "Type": "json",
            "pSize": str(self._settings.neis_page_size),
            **extra_params,
        }
        page_index = 1
        collected_rows: list[T] = []
        total_count: int | None = None

        while total_count is None or len(collected_rows) < total_count:
            page_rows, total_count = await self._fetch_page(
                path=path,
                service_key=service_key,
                row_model=row_model,
                params={**params, "pIndex": str(page_index)},
            )
            if not page_rows:
                break

            collected_rows.extend(page_rows)
            page_index += 1

        return collected_rows

    async def _fetch_page(
        self,
        path: str,
        service_key: str,
        row_model: type[T],
        params: dict[str, str],
    ) -> tuple[list[T], int]:
        attempts = self._settings.retry_attempts + 1

        for attempt in range(1, attempts + 1):
            try:
                response = await self._client.get(path, params=params)
                response.raise_for_status()
                payload: Any = response.json()
                if not isinstance(payload, dict):
                    raise ApiError(
                        502,
                        "NEIS_BAD_RESPONSE",
                        "급식 외부 서비스 응답 본문이 계약과 다릅니다.",
                    )
                return self._parse_service_payload(payload, service_key, row_model)
            except httpx.TimeoutException as exc:
                if attempt < attempts:
                    continue
                raise ApiError(504, "NEIS_TIMEOUT", "급식 외부 서비스 응답 시간이 초과되었습니다.") from exc
            except (httpx.ConnectError, httpx.NetworkError, httpx.ReadError) as exc:
                if attempt < attempts:
                    continue
                raise ApiError(503, "NEIS_UNAVAILABLE", "급식 외부 서비스에 연결할 수 없습니다.") from exc
            except httpx.HTTPStatusError as exc:
                if 500 <= exc.response.status_code < 600 and attempt < attempts:
                    continue
                raise ApiError(
                    502,
                    "NEIS_UPSTREAM_ERROR",
                    "급식 외부 서비스가 오류 응답을 반환했습니다.",
                ) from exc
            except JSONDecodeError as exc:
                raise ApiError(502, "NEIS_BAD_RESPONSE", "급식 외부 서비스 응답 형식이 올바르지 않습니다.") from exc
            except NeisUpstreamResponseError as exc:
                if exc.retryable and attempt < attempts:
                    continue
                raise ApiError(502, "NEIS_UPSTREAM_ERROR", exc.message) from exc

        raise ApiError(503, "NEIS_UNAVAILABLE", "급식 외부 서비스에 연결할 수 없습니다.")

    def _parse_service_payload(
        self,
        payload: dict[str, Any],
        service_key: str,
        row_model: type[T],
    ) -> tuple[list[T], int]:
        if "RESULT" in payload:
            result = self._parse_result_status(payload["RESULT"])
            self._raise_if_unsuccessful(result)
            return [], 0

        service_payload = payload.get(service_key)
        if not isinstance(service_payload, list) or not service_payload:
            raise ApiError(502, "NEIS_BAD_RESPONSE", "급식 외부 서비스 응답 본문이 계약과 다릅니다.")

        head_wrapper = service_payload[0]
        if not isinstance(head_wrapper, dict):
            raise ApiError(502, "NEIS_BAD_RESPONSE", "급식 외부 서비스 응답 헤더가 올바르지 않습니다.")

        head_items = head_wrapper.get("head")
        if not isinstance(head_items, list) or not head_items:
            raise ApiError(502, "NEIS_BAD_RESPONSE", "급식 외부 서비스 응답 결과 헤더가 누락되었습니다.")

        total_count = 0
        result_status: NeisResultStatus | None = None

        for item in head_items:
            if not isinstance(item, dict):
                continue
            if "list_total_count" in item:
                count = item["list_total_count"]
                if not isinstance(count, int):
                    raise ApiError(502, "NEIS_BAD_RESPONSE", "급식 외부 서비스 건수 값이 올바르지 않습니다.")
                total_count = count
            if "RESULT" in item:
                result_status = self._parse_result_status(item["RESULT"])

        if result_status is None:
            raise ApiError(502, "NEIS_BAD_RESPONSE", "급식 외부 서비스 결과 코드가 누락되었습니다.")

        normalized_code = _normalize_neis_code(result_status.code)
        if normalized_code in _NO_DATA_CODES:
            return [], 0
        self._raise_if_unsuccessful(result_status)

        if len(service_payload) < 2:
            raise ApiError(502, "NEIS_BAD_RESPONSE", "급식 외부 서비스 데이터 행이 누락되었습니다.")

        rows_wrapper = service_payload[1]
        if not isinstance(rows_wrapper, dict):
            raise ApiError(502, "NEIS_BAD_RESPONSE", "급식 외부 서비스 데이터 행 형식이 올바르지 않습니다.")

        row_items = rows_wrapper.get("row")
        if not isinstance(row_items, list):
            raise ApiError(502, "NEIS_BAD_RESPONSE", "급식 외부 서비스 데이터 목록이 누락되었습니다.")

        return self._validate_rows(row_items, row_model), total_count

    def _validate_rows(self, rows: Iterable[dict[str, Any]], row_model: type[T]) -> list[T]:
        validated_rows: list[T] = []
        for row in rows:
            try:
                validated_rows.append(row_model.model_validate(row))
            except ValidationError as exc:
                raise ApiError(
                    502,
                    "NEIS_BAD_RESPONSE",
                    "급식 외부 서비스 데이터 형식이 계약과 다릅니다.",
                ) from exc
        return validated_rows

    def _parse_result_status(self, value: Any) -> NeisResultStatus:
        try:
            return NeisResultStatus.model_validate(value)
        except ValidationError as exc:
            raise ApiError(502, "NEIS_BAD_RESPONSE", "급식 외부 서비스 결과 코드 형식이 올바르지 않습니다.") from exc

    def _raise_if_unsuccessful(self, result: NeisResultStatus) -> None:
        normalized_code = _normalize_neis_code(result.code)
        if normalized_code in _SUCCESS_CODES | _NO_DATA_CODES:
            return

        raise NeisUpstreamResponseError(
            code=result.code,
            message=result.message,
            retryable=normalized_code in _RETRYABLE_NEIS_CODES,
        )


def _normalize_neis_code(code: str) -> str:
    return code.split("-")[-1]
