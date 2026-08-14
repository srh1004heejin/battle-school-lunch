from __future__ import annotations

from datetime import datetime
from html import unescape
import json
import re

from .models import MealRecord, SchoolSummary, SelectedSchool
from .neis_schemas import MealServiceDietInfoRow, SchoolInfoRow

_BR_TAG_PATTERN = re.compile(r"(?i)<br\s*/?>")
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


def _clean_text(value: str | None) -> str:
    if value is None:
        return ""

    text = unescape(value).replace("\xa0", " ")
    text = _BR_TAG_PATTERN.sub("\n", text)
    text = _HTML_TAG_PATTERN.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n")]

    return "\n".join(line for line in lines if line)


def normalize_school(row: SchoolInfoRow) -> SchoolSummary:
    region = next(
        (
            value
            for value in (
                _clean_text(row.location_name),
                _clean_text(row.education_office_name),
                _clean_text(row.jurisdiction_name),
            )
            if value
        ),
        "지역 정보 없음",
    )
    address_parts = [_clean_text(row.road_address), _clean_text(row.road_address_detail)]
    address = " ".join(part for part in address_parts if part).strip() or "주소 정보 없음"

    return SchoolSummary(
        educationOfficeCode=row.education_office_code,
        schoolCode=row.school_code,
        name=_clean_text(row.school_name),
        region=region,
        address=address,
    )


def normalize_selected_school(row: SchoolInfoRow) -> SelectedSchool:
    return SelectedSchool(
        educationOfficeCode=row.education_office_code,
        schoolCode=row.school_code,
        name=_clean_text(row.school_name),
    )


def _parse_menu_lines(value: str) -> list[str]:
    return [line for line in _clean_text(value).split("\n") if line]


def _parse_nutrition(value: str | None) -> dict[str, str] | None:
    if not value:
        return None

    nutrition: dict[str, str] = {}
    for line in _clean_text(value).split("\n"):
        if not line:
            continue
        if ":" not in line:
            if "：" in line:
                label, parsed_value = line.split("：", 1)
            else:
                continue
        else:
            label, parsed_value = line.split(":", 1)

        normalized_label = label.strip()
        normalized_value = parsed_value.strip()
        if normalized_label and normalized_value:
            nutrition[normalized_label] = normalized_value

    return nutrition or None


def normalize_meal(row: MealServiceDietInfoRow) -> MealRecord:
    menu = _parse_menu_lines(row.dish_name)
    meal_date = datetime.strptime(row.meal_date, "%Y%m%d").date()

    return MealRecord(
        date=meal_date,
        mealType="lunch",
        menu=menu,
        calories=_clean_text(row.calorie_info) or None,
        nutrition=_parse_nutrition(row.nutrition_info),
        origin=_clean_text(row.origin_info) or None,
    )


def dedupe_and_sort_schools(schools: list[SchoolSummary]) -> list[SchoolSummary]:
    unique: dict[tuple[str, str], SchoolSummary] = {}
    for school in schools:
        unique.setdefault((school.educationOfficeCode, school.schoolCode), school)

    return sorted(
        unique.values(),
        key=lambda school: (
            school.name,
            school.region,
            school.address,
            school.educationOfficeCode,
            school.schoolCode,
        ),
    )


def dedupe_and_sort_meals(meals: list[MealRecord]) -> list[MealRecord]:
    seen: set[str] = set()
    unique: list[MealRecord] = []

    for meal in meals:
        signature = json.dumps(meal.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
        if signature in seen:
            continue
        seen.add(signature)
        unique.append(meal)

    return sorted(unique, key=lambda meal: meal.date)
