from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class SchoolRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    education_office_code: str = Field(alias="ATPT_OFCDC_SC_CODE")
    education_office_name: str = Field(alias="ATPT_OFCDC_SC_NM")
    school_code: str = Field(alias="SD_SCHUL_CODE")
    school_name: str = Field(alias="SCHUL_NM")
    region: str | None = Field(default=None, alias="LCTN_SC_NM")
    address: str | None = Field(default=None, alias="ORG_RDNMA")


class MealRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    meal_code: str = Field(alias="MMEAL_SC_CODE")
    meal_date: str = Field(alias="MLSV_YMD")
    dish_name: str = Field(alias="DDISH_NM")
    calorie_info: str | None = Field(default=None, alias="CAL_INFO")
    nutrition_info: str | None = Field(default=None, alias="NTR_INFO")
    origin_info: str | None = Field(default=None, alias="ORPLC_INFO")


class School(BaseModel):
    educationOfficeCode: str
    educationOfficeName: str
    schoolCode: str
    name: str
    region: str | None = None
    address: str | None = None


class Meal(BaseModel):
    date: date
    menu: list[str] = Field(min_length=1)
    calories: str | None = None
    nutrition: dict[str, str] | None = None
    origin: str | None = None
