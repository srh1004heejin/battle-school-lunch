from __future__ import annotations

import json
import re
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal, Protocol, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from .models import SelectedSchool

AreaId = Literal["nutrition_balance", "healthiness", "ingredient_menu_quality"]
Outcome = Literal["first", "second", "tie"]
ModelT = TypeVar("ModelT", bound=BaseModel)

AREA_WEIGHTS: dict[AreaId, int] = {
    "nutrition_balance": 45,
    "healthiness": 30,
    "ingredient_menu_quality": 25,
}


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schools: list[SelectedSchool] = Field(min_length=2, max_length=2)
    date: date
    prompt: str = Field(min_length=1, max_length=4000)

    @model_validator(mode="after")
    def ensure_distinct_schools(self) -> "AnalysisRequest":
        for school in self.schools:
            if not re.fullmatch(r"[A-Z0-9]+", school.educationOfficeCode):
                raise ValueError("교육청 코드는 영문 대문자와 숫자만 사용할 수 있습니다.")
            if not re.fullmatch(r"[A-Z0-9]+", school.schoolCode):
                raise ValueError("학교 코드는 영문 대문자와 숫자만 사용할 수 있습니다.")
        identifiers = {(school.educationOfficeCode, school.schoolCode) for school in self.schools}
        if len(identifiers) != 2:
            raise ValueError("서로 다른 학교 두 곳을 선택해야 합니다.")
        return self


class SchoolAreaEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    educationOfficeCode: str
    schoolCode: str
    score: int = Field(ge=1, le=5)
    rationale: str = Field(min_length=1)
    evidence: list[str] = Field(min_length=1)
    estimatedFlags: list[str] = Field(default_factory=list)


class AreaEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    area: AreaId
    evaluations: list[SchoolAreaEvaluation] = Field(min_length=2, max_length=2)


class WeightedAreaScore(BaseModel):
    area: AreaId
    rating: int = Field(ge=1, le=5)
    weight: int
    weightedScore: float
    rationale: str
    evidence: list[str]
    estimatedFlags: list[str]


class SchoolScore(BaseModel):
    school: SelectedSchool
    areas: list[WeightedAreaScore] = Field(min_length=3, max_length=3)
    totalScore: float = Field(ge=0, le=100)


class FinalReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1)
    keyReason: str = Field(min_length=1)
    firstSchoolImprovement: str = Field(min_length=1)
    secondSchoolImprovement: str = Field(min_length=1)
    qualityWarnings: list[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    scores: list[SchoolScore] = Field(min_length=2, max_length=2)
    outcome: Outcome
    winnerSchool: SelectedSchool | None
    review: FinalReview
    disclaimer: str = "이 분석은 영양사의 전문 진단을 대체하지 않습니다."


class AnalysisEngine(Protocol):
    async def evaluate(self, request: AnalysisRequest) -> AnalysisResult: ...


def validate_analysis_date(selected_date: date, today: date | None = None) -> None:
    reference = today or date.today()
    current_month_start = reference.replace(day=1)
    previous_month_end = current_month_start.fromordinal(current_month_start.toordinal() - 1)
    previous_month_start = previous_month_end.replace(day=1)
    if selected_date < previous_month_start or selected_date > reference:
        raise ValueError("분석 날짜는 직전 달 1일부터 오늘 사이여야 합니다.")


def calculate_scores(
    request: AnalysisRequest,
    area_results: list[AreaEvaluation],
) -> tuple[list[SchoolScore], Outcome, SelectedSchool | None]:
    by_area = {result.area: result for result in area_results}
    if set(by_area) != set(AREA_WEIGHTS):
        raise ValueError("세 평가영역의 결과가 모두 필요합니다.")

    scores: list[SchoolScore] = []
    for school in request.schools:
        weighted_areas: list[WeightedAreaScore] = []
        for area, weight in AREA_WEIGHTS.items():
            matching = [
                evaluation
                for evaluation in by_area[area].evaluations
                if (
                    evaluation.educationOfficeCode == school.educationOfficeCode
                    and evaluation.schoolCode == school.schoolCode
                )
            ]
            if len(matching) != 1:
                raise ValueError(f"{school.name}의 {area} 평가 결과가 정확히 하나여야 합니다.")
            evaluation = matching[0]
            weighted = (
                Decimal(evaluation.score) / Decimal(5) * Decimal(weight)
            ).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
            weighted_areas.append(
                WeightedAreaScore(
                    area=area,
                    rating=evaluation.score,
                    weight=weight,
                    weightedScore=float(weighted),
                    rationale=evaluation.rationale,
                    evidence=evaluation.evidence,
                    estimatedFlags=evaluation.estimatedFlags,
                )
            )
        total = sum((Decimal(str(area.weightedScore)) for area in weighted_areas), Decimal(0))
        scores.append(SchoolScore(school=school, areas=weighted_areas, totalScore=float(total)))

    if scores[0].totalScore == scores[1].totalScore:
        return scores, "tie", None
    if scores[0].totalScore > scores[1].totalScore:
        return scores, "first", scores[0].school
    return scores, "second", scores[1].school


def parse_json_model(text: str, model: type[ModelT]) -> ModelT:
    normalized = text.strip()
    if normalized.startswith("```"):
        lines = normalized.splitlines()
        normalized = "\n".join(lines[1:-1]).strip()
    try:
        payload = json.loads(normalized)
        return model.model_validate(payload)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError(f"에이전트가 유효한 {model.__name__} JSON을 반환하지 않았습니다.") from exc
