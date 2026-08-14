from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class School(ApiModel):
    education_office_code: str = Field(alias="educationOfficeCode")
    school_code: str = Field(alias="schoolCode")
    name: str
    region: str
    address: str


class SchoolSummary(ApiModel):
    education_office_code: str = Field(alias="educationOfficeCode")
    school_code: str = Field(alias="schoolCode")
    name: str


class SchoolSearchResponse(ApiModel):
    schools: list[School]


class Meal(ApiModel):
    date: date
    meal_type: str = Field(default="lunch", alias="mealType")
    menu: list[str]
    calories: str | None = None
    nutrition: dict[str, str] | None = None
    origin: str | None = None


class MealsResponse(ApiModel):
    school: SchoolSummary
    from_date: date = Field(alias="from")
    to_date: date = Field(alias="to")
    meals: list[Meal]


class ErrorDetail(ApiModel):
    code: str
    message: str
    request_id: str = Field(alias="requestId")


class ErrorResponse(ApiModel):
    error: ErrorDetail


class NeisResult(BaseModel):
    code: str = Field(alias="CODE")
    message: str = Field(alias="MESSAGE", default="")


class NeisSchoolRow(BaseModel):
    education_office_code: str = Field(alias="ATPT_OFCDC_SC_CODE", min_length=1)
    education_office_name: str | None = Field(
        alias="ATPT_OFCDC_SC_NM", default=None
    )
    school_code: str = Field(alias="SD_SCHUL_CODE", min_length=1)
    name: str = Field(alias="SCHUL_NM", min_length=1)
    location: str | None = Field(alias="LCTN_SC_NM", default=None)
    jurisdiction: str | None = Field(alias="JU_ORG_NM", default=None)
    road_address: str | None = Field(alias="ORG_RDNMA", default=None)
    address_detail: str | None = Field(alias="ORG_RDNDA", default=None)


class NeisMealRow(BaseModel):
    education_office_code: str = Field(alias="ATPT_OFCDC_SC_CODE", min_length=1)
    school_code: str = Field(alias="SD_SCHUL_CODE", min_length=1)
    school_name: str = Field(alias="SCHUL_NM", min_length=1)
    meal_code: str = Field(alias="MMEAL_SC_CODE", min_length=1)
    service_date: str = Field(alias="MLSV_YMD", pattern=r"^\d{8}$")
    dishes: str = Field(alias="DDISH_NM")
    origin: str | None = Field(alias="ORPLC_INFO", default=None)
    calories: str | None = Field(alias="CAL_INFO", default=None)
    nutrition: str | None = Field(alias="NTR_INFO", default=None)
