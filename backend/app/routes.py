import re
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query, Request

from app.errors import AppError, invalid_input
from app.models import MealsResponse, SchoolSearchResponse, SchoolSummary
from app.neis import NeisClient

router = APIRouter()
CODE_PATTERN = re.compile(r"^[A-Z0-9]{2,20}$")
MAX_DATE_RANGE_DAYS = 366


def _client(request: Request) -> NeisClient:
    return request.app.state.neis_client


def _validate_code(value: str, field: str) -> str:
    value = value.strip().upper()
    if not CODE_PATTERN.fullmatch(value):
        raise invalid_input("INVALID_SCHOOL_CODE", f"{field} 형식이 올바르지 않습니다.")
    return value


def _parse_date(value: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise invalid_input(
            "INVALID_DATE",
            f"{field}은 YYYY-MM-DD 형식의 실제 날짜여야 합니다.",
            status_code=422,
        ) from None


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get(
    "/api/schools",
    response_model=SchoolSearchResponse,
    response_model_exclude_none=True,
)
async def search_schools(
    request: Request,
    query: Annotated[str, Query(max_length=100)],
) -> SchoolSearchResponse:
    normalized = query.strip()
    if not normalized:
        raise invalid_input("EMPTY_QUERY", "학교 이름을 입력해 주세요.")
    return SchoolSearchResponse(schools=await _client(request).search_schools(normalized))


@router.get(
    "/api/schools/{educationOfficeCode}/{schoolCode}/meals",
    response_model=MealsResponse,
    response_model_exclude_none=True,
)
async def get_meals(
    request: Request,
    education_office_code: Annotated[str, Path(alias="educationOfficeCode")],
    school_code: Annotated[str, Path(alias="schoolCode")],
    from_value: Annotated[str, Query(alias="from")],
    to_value: Annotated[str, Query(alias="to")],
    meal_type: Annotated[Literal["lunch"], Query(alias="mealType")],
) -> MealsResponse:
    del meal_type
    office_code = _validate_code(education_office_code, "교육청 코드")
    normalized_school_code = _validate_code(school_code, "학교 코드")
    from_date = _parse_date(from_value, "시작일")
    to_date = _parse_date(to_value, "종료일")
    if from_date > to_date:
        raise invalid_input(
            "INVALID_DATE_RANGE", "시작일은 종료일보다 늦을 수 없습니다."
        )
    if (to_date - from_date).days + 1 > MAX_DATE_RANGE_DAYS:
        raise invalid_input(
            "DATE_RANGE_TOO_LARGE",
            f"조회 기간은 최대 {MAX_DATE_RANGE_DAYS}일입니다.",
            status_code=422,
        )

    client = _client(request)
    school = await client.get_school(office_code, normalized_school_code)
    if school is None:
        raise AppError(404, "SCHOOL_NOT_FOUND", "학교를 찾을 수 없습니다.")
    meals = await client.get_meals(
        office_code, normalized_school_code, from_date, to_date
    )
    return MealsResponse(
        school=SchoolSummary(
            education_office_code=school.education_office_code,
            school_code=school.school_code,
            name=school.name,
        ),
        from_date=from_date,
        to_date=to_date,
        meals=meals,
    )
