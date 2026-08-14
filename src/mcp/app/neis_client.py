from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from html import unescape
from json import JSONDecodeError
import re
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from .errors import McpServiceError
from .models import Meal, MealRow, School, SchoolRow
from .settings import Settings

T = TypeVar("T", bound=BaseModel)
_NO_DATA_CODES = {"200"}
_SUCCESS_CODES = {"000", "100"}
_RETRYABLE_CODES = {"500", "600"}
_BR_TAG = re.compile(r"(?i)<br\s*/?>")
_HTML_TAG = re.compile(r"<[^>]+>")


class _RetryableNeisError(Exception):
    pass


class NeisClient:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._settings = settings
        self._client = httpx.AsyncClient(
            base_url=settings.neis_base_url,
            timeout=httpx.Timeout(
                settings.request_timeout_seconds,
                connect=settings.connect_timeout_seconds,
            ),
            headers={"Accept": "application/json"},
            transport=transport,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def search_schools(self, query: str) -> list[School]:
        rows = await self._fetch_rows("/schoolInfo", "schoolInfo", SchoolRow, {"SCHUL_NM": query})
        schools = [
            School(
                educationOfficeCode=row.education_office_code,
                educationOfficeName=_clean_text(row.education_office_name),
                schoolCode=row.school_code,
                name=_clean_text(row.school_name),
                region=_clean_text(row.region) or None,
                address=_clean_text(row.address) or None,
            )
            for row in rows
        ]
        unique = {(school.educationOfficeCode, school.schoolCode): school for school in schools}
        return sorted(unique.values(), key=lambda school: (school.name, school.educationOfficeCode, school.schoolCode))

    async def get_lunch_meals(
        self,
        education_office_code: str,
        school_code: str,
        from_date: str,
        to_date: str,
    ) -> list[Meal]:
        rows = await self._fetch_rows(
            "/mealServiceDietInfo",
            "mealServiceDietInfo",
            MealRow,
            {
                "ATPT_OFCDC_SC_CODE": education_office_code,
                "SD_SCHUL_CODE": school_code,
                "MMEAL_SC_CODE": "2",
                "MLSV_FROM_YMD": from_date.replace("-", ""),
                "MLSV_TO_YMD": to_date.replace("-", ""),
            },
        )
        try:
            meals = [_normalize_meal(row) for row in rows if row.meal_code == "2"]
        except (ValueError, ValidationError) as exc:
            raise McpServiceError("NEIS_BAD_RESPONSE", "NEIS 급식 데이터 형식이 올바르지 않습니다.") from exc
        unique = {meal.model_dump_json(): meal for meal in meals}
        return sorted(unique.values(), key=lambda meal: meal.date)

    async def _fetch_rows(
        self,
        path: str,
        service_key: str,
        row_model: type[T],
        extra_params: dict[str, str],
    ) -> list[T]:
        page_index = 1
        rows: list[T] = []
        total_count: int | None = None
        base_params = {
            "Key": self._settings.neis_api_key,
            "Type": "json",
            "pSize": str(self._settings.neis_page_size),
            **extra_params,
        }
        while total_count is None or len(rows) < total_count:
            page_rows, total_count = await self._fetch_page(
                path,
                service_key,
                row_model,
                {**base_params, "pIndex": str(page_index)},
            )
            if not page_rows:
                break
            rows.extend(page_rows)
            page_index += 1
        return rows

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
                    raise McpServiceError("NEIS_BAD_RESPONSE", "NEIS 응답 본문이 올바르지 않습니다.")
                return self._parse_payload(payload, service_key, row_model)
            except httpx.TimeoutException as exc:
                if attempt < attempts:
                    continue
                raise McpServiceError("NEIS_TIMEOUT", "NEIS 응답 시간이 초과되었습니다.") from exc
            except (httpx.ConnectError, httpx.NetworkError, httpx.ReadError) as exc:
                if attempt < attempts:
                    continue
                raise McpServiceError("NEIS_UNAVAILABLE", "NEIS 서비스에 연결할 수 없습니다.") from exc
            except httpx.RequestError as exc:
                if attempt < attempts:
                    continue
                raise McpServiceError("NEIS_UNAVAILABLE", "NEIS 서비스 요청을 완료할 수 없습니다.") from exc
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code >= 500 and attempt < attempts:
                    continue
                raise McpServiceError("NEIS_UPSTREAM_ERROR", "NEIS 서비스가 오류 응답을 반환했습니다.") from exc
            except JSONDecodeError as exc:
                raise McpServiceError("NEIS_BAD_RESPONSE", "NEIS 응답 형식이 올바르지 않습니다.") from exc
            except _RetryableNeisError as exc:
                if attempt < attempts:
                    continue
                raise McpServiceError(
                    "NEIS_UPSTREAM_ERROR",
                    "NEIS 서비스가 일시적인 오류를 반환했습니다.",
                ) from exc
        raise McpServiceError("NEIS_UNAVAILABLE", "NEIS 서비스에 연결할 수 없습니다.")

    def _parse_payload(
        self,
        payload: dict[str, Any],
        service_key: str,
        row_model: type[T],
    ) -> tuple[list[T], int]:
        if "RESULT" in payload:
            self._check_result(payload["RESULT"])
            return [], 0
        service = payload.get(service_key)
        if not isinstance(service, list) or not service:
            raise McpServiceError("NEIS_BAD_RESPONSE", "NEIS 응답 본문이 계약과 다릅니다.")
        head_wrapper = service[0]
        if not isinstance(head_wrapper, dict) or not isinstance(head_wrapper.get("head"), list):
            raise McpServiceError("NEIS_BAD_RESPONSE", "NEIS 응답 헤더가 올바르지 않습니다.")
        total_count = 0
        result_found = False
        for item in head_wrapper["head"]:
            if not isinstance(item, dict):
                continue
            if "list_total_count" in item:
                if not isinstance(item["list_total_count"], int):
                    raise McpServiceError("NEIS_BAD_RESPONSE", "NEIS 결과 건수가 올바르지 않습니다.")
                total_count = item["list_total_count"]
            if "RESULT" in item:
                result_found = True
                self._check_result(item["RESULT"])
        if not result_found:
            raise McpServiceError("NEIS_BAD_RESPONSE", "NEIS 결과 코드가 누락되었습니다.")
        if total_count == 0:
            return [], 0
        if len(service) < 2 or not isinstance(service[1], dict):
            raise McpServiceError("NEIS_BAD_RESPONSE", "NEIS 데이터 행이 누락되었습니다.")
        raw_rows = service[1].get("row")
        if not isinstance(raw_rows, list):
            raise McpServiceError("NEIS_BAD_RESPONSE", "NEIS 데이터 목록이 올바르지 않습니다.")
        return self._validate_rows(raw_rows, row_model), total_count

    def _check_result(self, value: Any) -> None:
        if not isinstance(value, dict) or not isinstance(value.get("CODE"), str):
            raise McpServiceError("NEIS_BAD_RESPONSE", "NEIS 결과 코드가 올바르지 않습니다.")
        code = value["CODE"].split("-")[-1]
        if code in _SUCCESS_CODES | _NO_DATA_CODES:
            return
        if code in _RETRYABLE_CODES:
            raise _RetryableNeisError
        raise McpServiceError("NEIS_UPSTREAM_ERROR", "NEIS 서비스가 요청을 처리하지 못했습니다.")

    @staticmethod
    def _validate_rows(rows: Iterable[Any], row_model: type[T]) -> list[T]:
        try:
            return [row_model.model_validate(row) for row in rows]
        except ValidationError as exc:
            raise McpServiceError("NEIS_BAD_RESPONSE", "NEIS 데이터 형식이 계약과 다릅니다.") from exc


def _clean_text(value: str | None) -> str:
    if value is None:
        return ""
    text = _BR_TAG.sub("\n", unescape(value).replace("\xa0", " "))
    text = _HTML_TAG.sub("", text)
    return "\n".join(line.strip() for line in text.replace("\r", "").split("\n") if line.strip())


def _normalize_meal(row: MealRow) -> Meal:
    menu = _clean_text(row.dish_name).splitlines()
    nutrition: dict[str, str] = {}
    for line in _clean_text(row.nutrition_info).splitlines():
        separator = ":" if ":" in line else "：" if "：" in line else None
        if separator:
            key, value = line.split(separator, 1)
            if key.strip() and value.strip():
                nutrition[key.strip()] = value.strip()
    return Meal(
        date=datetime.strptime(row.meal_date, "%Y%m%d").date(),
        menu=menu,
        calories=_clean_text(row.calorie_info) or None,
        nutrition=nutrition or None,
        origin=_clean_text(row.origin_info) or None,
    )
