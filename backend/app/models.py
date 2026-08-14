from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ErrorDetail(BaseModel):
    code: str
    message: str
    requestId: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class HealthResponse(BaseModel):
    status: Literal["ok"]


class SchoolSummary(BaseModel):
    educationOfficeCode: str
    schoolCode: str
    name: str
    region: str
    address: str


class SelectedSchool(BaseModel):
    educationOfficeCode: str
    schoolCode: str
    name: str


class SchoolSearchResponse(BaseModel):
    schools: list[SchoolSummary]


class RandomSchoolResponse(BaseModel):
    schools: list[SchoolSummary] = Field(min_length=10, max_length=10)


class MealRecord(BaseModel):
    date: date
    mealType: Literal["lunch"]
    menu: list[str] = Field(min_length=1)
    calories: str | None = None
    nutrition: dict[str, str] | None = None
    origin: str | None = None
    mealCount: str | None = None


class MealSearchResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    school: SelectedSchool
    from_date: date = Field(alias="from", serialization_alias="from")
    to_date: date = Field(alias="to", serialization_alias="to")
    meals: list[MealRecord]
