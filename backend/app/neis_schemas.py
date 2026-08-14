from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NeisResultStatus(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    code: str = Field(alias="CODE")
    message: str = Field(alias="MESSAGE")


class SchoolInfoRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    education_office_code: str = Field(alias="ATPT_OFCDC_SC_CODE")
    education_office_name: str | None = Field(default=None, alias="ATPT_OFCDC_SC_NM")
    school_code: str = Field(alias="SD_SCHUL_CODE")
    school_name: str = Field(alias="SCHUL_NM")
    english_school_name: str | None = Field(default=None, alias="ENG_SCHUL_NM")
    school_kind_name: str | None = Field(default=None, alias="SCHUL_KND_SC_NM")
    location_name: str | None = Field(default=None, alias="LCTN_SC_NM")
    jurisdiction_name: str | None = Field(default=None, alias="JU_ORG_NM")
    foundation_name: str | None = Field(default=None, alias="FOND_SC_NM")
    postal_code: str | None = Field(default=None, alias="ORG_RDNZC")
    road_address: str | None = Field(default=None, alias="ORG_RDNMA")
    road_address_detail: str | None = Field(default=None, alias="ORG_RDNDA")
    telephone: str | None = Field(default=None, alias="ORG_TELNO")
    homepage_url: str | None = Field(default=None, alias="HMPG_ADRES")
    coeducation_name: str | None = Field(default=None, alias="COEDU_SC_NM")
    fax_number: str | None = Field(default=None, alias="ORG_FAXNO")
    high_school_name: str | None = Field(default=None, alias="HS_SC_NM")
    industry_special_class_exists: str | None = Field(default=None, alias="INDST_SPECL_CCCCL_EXST_YN")
    high_school_general_business_name: str | None = Field(default=None, alias="HS_GNRL_BUSNS_SC_NM")
    special_purpose_high_school_name: str | None = Field(default=None, alias="SPCLY_PURPS_HS_ORD_NM")
    admission_period_name: str | None = Field(default=None, alias="ENE_BFE_SEHF_SC_NM")
    day_night_name: str | None = Field(default=None, alias="DGHT_SC_NM")
    foundation_date: str | None = Field(default=None, alias="FOND_YMD")
    anniversary: str | None = Field(default=None, alias="FOAS_MEMRD")
    load_datetime: str | None = Field(default=None, alias="LOAD_DTM")


class MealServiceDietInfoRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    education_office_code: str = Field(alias="ATPT_OFCDC_SC_CODE")
    education_office_name: str | None = Field(default=None, alias="ATPT_OFCDC_SC_NM")
    school_code: str = Field(alias="SD_SCHUL_CODE")
    school_name: str = Field(alias="SCHUL_NM")
    meal_code: str = Field(alias="MMEAL_SC_CODE")
    meal_name: str | None = Field(default=None, alias="MMEAL_SC_NM")
    meal_date: str = Field(alias="MLSV_YMD")
    meal_count: str | None = Field(default=None, alias="MLSV_FGR")
    dish_name: str = Field(alias="DDISH_NM")
    origin_info: str | None = Field(default=None, alias="ORPLC_INFO")
    calorie_info: str | None = Field(default=None, alias="CAL_INFO")
    nutrition_info: str | None = Field(default=None, alias="NTR_INFO")
    meal_from_date: str | None = Field(default=None, alias="MLSV_FROM_YMD")
    meal_to_date: str | None = Field(default=None, alias="MLSV_TO_YMD")
    load_datetime: str | None = Field(default=None, alias="LOAD_DTM")

    @field_validator("meal_count", mode="before")
    @classmethod
    def normalize_numeric_meal_count(cls, value: object) -> object:
        if isinstance(value, int) and not isinstance(value, bool):
            return str(value)
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return value
