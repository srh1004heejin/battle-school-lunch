import asyncio
import logging
import math
from collections.abc import Mapping
from datetime import date, datetime
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.config import Settings
from app.errors import UpstreamBadResponse, UpstreamTimeout, UpstreamUnavailable
from app.models import Meal, NeisMealRow, NeisResult, NeisSchoolRow, School
from app.text import parse_menu, parse_nutrition, parse_optional_text

logger = logging.getLogger(__name__)
RowModel = TypeVar("RowModel", bound=BaseModel)
NO_DATA_CODE = "INFO-200"
SUCCESS_CODES = {"INFO-000", "INFO-100"}


class NeisClient:
    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        timeout = httpx.Timeout(
            settings.neis_timeout_seconds,
            connect=settings.neis_connect_timeout_seconds,
        )
        self._client = httpx.AsyncClient(
            base_url=settings.neis_base_url,
            timeout=timeout,
            transport=transport,
            headers={"Accept": "application/json"},
        )
        self._api_key = settings.neis_api_key
        self._page_size = settings.neis_page_size
        self._max_pages = settings.neis_max_pages
        self._retries = settings.neis_max_retries

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _request(self, path: str, params: Mapping[str, str | int]) -> dict:
        request_params: dict[str, str | int] = {
            "KEY": self._api_key,
            "Type": "json",
            **params,
        }
        for attempt in range(self._retries + 1):
            try:
                response = await self._client.get(path, params=request_params)
            except httpx.TimeoutException:
                if attempt < self._retries:
                    await asyncio.sleep(0.05 * (2**attempt))
                    continue
                raise UpstreamTimeout() from None
            except httpx.NetworkError:
                if attempt < self._retries:
                    await asyncio.sleep(0.05 * (2**attempt))
                    continue
                raise UpstreamUnavailable() from None

            if response.status_code >= 500:
                if attempt < self._retries:
                    await asyncio.sleep(0.05 * (2**attempt))
                    continue
                raise UpstreamUnavailable()
            if response.status_code < 200 or response.status_code >= 300:
                raise UpstreamBadResponse("NEIS 요청이 거부되었습니다.")
            try:
                payload = response.json()
            except ValueError:
                raise UpstreamBadResponse() from None
            if not isinstance(payload, dict):
                raise UpstreamBadResponse()
            return payload
        raise UpstreamUnavailable()

    @staticmethod
    def _result_code(value: object) -> str | None:
        try:
            if isinstance(value, dict):
                return NeisResult.model_validate(value).code
        except ValidationError:
            raise UpstreamBadResponse() from None
        return None

    def _extract_page(
        self,
        payload: dict,
        service: str,
        row_model: type[RowModel],
    ) -> tuple[list[RowModel], int]:
        global_code = self._result_code(payload.get("RESULT"))
        if global_code == NO_DATA_CODE:
            return [], 0
        if global_code is not None and global_code not in SUCCESS_CODES:
            raise UpstreamBadResponse("NEIS가 요청 처리 오류를 반환했습니다.")

        sections = payload.get(service)
        if not isinstance(sections, list):
            raise UpstreamBadResponse()
        rows: object = None
        total: int | None = None
        result_code: str | None = None
        for section in sections:
            if not isinstance(section, dict):
                raise UpstreamBadResponse()
            head = section.get("head")
            if head is not None:
                if not isinstance(head, list):
                    raise UpstreamBadResponse()
                for item in head:
                    if not isinstance(item, dict):
                        raise UpstreamBadResponse()
                    if "list_total_count" in item:
                        count = item["list_total_count"]
                        if not isinstance(count, int) or count < 0:
                            raise UpstreamBadResponse()
                        total = count
                    if "RESULT" in item:
                        result_code = self._result_code(item["RESULT"])
            if "row" in section:
                rows = section["row"]

        if result_code == NO_DATA_CODE:
            return [], 0
        if result_code not in SUCCESS_CODES:
            raise UpstreamBadResponse("NEIS가 요청 처리 오류를 반환했습니다.")
        if rows is None:
            rows = []
        if not isinstance(rows, list) or total is None:
            raise UpstreamBadResponse()
        try:
            validated = [row_model.model_validate(row) for row in rows]
        except ValidationError:
            raise UpstreamBadResponse() from None
        return validated, total

    async def _all_rows(
        self,
        path: str,
        service: str,
        row_model: type[RowModel],
        params: Mapping[str, str],
    ) -> list[RowModel]:
        first_payload = await self._request(
            path, {**params, "pIndex": 1, "pSize": self._page_size}
        )
        first_rows, total = self._extract_page(first_payload, service, row_model)
        page_count = math.ceil(total / self._page_size) if total else 0
        if page_count > self._max_pages:
            raise UpstreamBadResponse("NEIS 결과가 서버의 페이지 제한을 초과했습니다.")
        rows = list(first_rows)
        for page in range(2, page_count + 1):
            payload = await self._request(
                path, {**params, "pIndex": page, "pSize": self._page_size}
            )
            page_rows, page_total = self._extract_page(payload, service, row_model)
            if page_total != total:
                raise UpstreamBadResponse("NEIS 페이지 정보가 일관되지 않습니다.")
            rows.extend(page_rows)
        return rows

    async def search_schools(self, query: str) -> list[School]:
        rows = await self._all_rows(
            "/schoolInfo",
            "schoolInfo",
            NeisSchoolRow,
            {"SCHUL_NM": query},
        )
        schools: dict[tuple[str, str], School] = {}
        for row in rows:
            key = (row.education_office_code, row.school_code)
            if key in schools:
                continue
            address_parts = [
                part.strip()
                for part in (row.road_address, row.address_detail)
                if part and part.strip()
            ]
            schools[key] = School(
                education_office_code=row.education_office_code,
                school_code=row.school_code,
                name=row.name.strip(),
                region=(
                    row.location or row.jurisdiction or row.education_office_name
                    or ""
                ),
                address=" ".join(address_parts),
            )
        return sorted(
            schools.values(),
            key=lambda school: (
                school.name,
                school.region or "",
                school.address or "",
                school.education_office_code,
                school.school_code,
            ),
        )

    async def get_school(
        self, education_office_code: str, school_code: str
    ) -> School | None:
        rows = await self._all_rows(
            "/schoolInfo",
            "schoolInfo",
            NeisSchoolRow,
            {
                "ATPT_OFCDC_SC_CODE": education_office_code,
                "SD_SCHUL_CODE": school_code,
            },
        )
        for row in rows:
            if (
                row.education_office_code == education_office_code
                and row.school_code == school_code
            ):
                address = " ".join(
                    part.strip()
                    for part in (row.road_address, row.address_detail)
                    if part and part.strip()
                )
                return School(
                    education_office_code=row.education_office_code,
                    school_code=row.school_code,
                    name=row.name.strip(),
                    region=row.location
                    or row.jurisdiction
                    or row.education_office_name
                    or "",
                    address=address,
                )
        return None

    async def get_meals(
        self,
        education_office_code: str,
        school_code: str,
        from_date: date,
        to_date: date,
    ) -> list[Meal]:
        rows = await self._all_rows(
            "/mealServiceDietInfo",
            "mealServiceDietInfo",
            NeisMealRow,
            {
                "ATPT_OFCDC_SC_CODE": education_office_code,
                "SD_SCHUL_CODE": school_code,
                "MMEAL_SC_CODE": "2",
                "MLSV_FROM_YMD": from_date.strftime("%Y%m%d"),
                "MLSV_TO_YMD": to_date.strftime("%Y%m%d"),
            },
        )
        meals: dict[date, Meal] = {}
        for row in rows:
            if (
                row.education_office_code != education_office_code
                or row.school_code != school_code
                or row.meal_code != "2"
            ):
                continue
            try:
                meal_date = datetime.strptime(row.service_date, "%Y%m%d").date()
            except ValueError:
                raise UpstreamBadResponse() from None
            if meal_date < from_date or meal_date > to_date or meal_date in meals:
                continue
            meals[meal_date] = Meal(
                date=meal_date,
                menu=parse_menu(row.dishes),
                calories=parse_optional_text(row.calories),
                nutrition=parse_nutrition(row.nutrition),
                origin=parse_optional_text(row.origin),
            )
        return [meals[key] for key in sorted(meals)]
