from __future__ import annotations

from datetime import date

import pytest

from app.evaluation import (
    AnalysisRequest,
    AreaEvaluation,
    calculate_scores,
    validate_analysis_date,
)


def build_request() -> AnalysisRequest:
    return AnalysisRequest.model_validate(
        {
            "schools": [
                {"educationOfficeCode": "B10", "schoolCode": "7010001", "name": "첫학교"},
                {"educationOfficeCode": "C10", "schoolCode": "7010002", "name": "둘학교"},
            ],
            "date": "2026-08-14",
            "prompt": "두 학교의 급식을 비교해 주세요.",
        }
    )


def area_result(area: str, first_score: int, second_score: int) -> AreaEvaluation:
    return AreaEvaluation.model_validate(
        {
            "area": area,
            "evaluations": [
                {
                    "educationOfficeCode": "B10",
                    "schoolCode": "7010001",
                    "score": first_score,
                    "rationale": "첫 학교 근거",
                    "evidence": ["NEIS 확인값"],
                    "estimatedFlags": [],
                },
                {
                    "educationOfficeCode": "C10",
                    "schoolCode": "7010002",
                    "score": second_score,
                    "rationale": "둘 학교 근거",
                    "evidence": ["NEIS 확인값"],
                    "estimatedFlags": [],
                },
            ],
        }
    )


def test_calculate_scores_applies_documented_weights_and_selects_winner() -> None:
    scores, outcome, winner = calculate_scores(
        build_request(),
        [
            area_result("nutrition_balance", 5, 4),
            area_result("healthiness", 4, 3),
            area_result("ingredient_menu_quality", 3, 5),
        ],
    )

    assert [area.weightedScore for area in scores[0].areas] == [45.0, 24.0, 15.0]
    assert scores[0].totalScore == 84.0
    assert scores[1].totalScore == 79.0
    assert outcome == "first"
    assert winner == scores[0].school


def test_calculate_scores_preserves_tie() -> None:
    scores, outcome, winner = calculate_scores(
        build_request(),
        [
            area_result("nutrition_balance", 4, 4),
            area_result("healthiness", 3, 3),
            area_result("ingredient_menu_quality", 5, 5),
        ],
    )

    assert scores[0].totalScore == scores[1].totalScore
    assert outcome == "tie"
    assert winner is None


def test_calculate_scores_uses_compound_school_identifier() -> None:
    request = build_request().model_copy(
        update={
            "schools": [
                build_request().schools[0],
                build_request().schools[1].model_copy(update={"schoolCode": "7010001"}),
            ]
        }
    )
    results = [
        area_result("nutrition_balance", 5, 4),
        area_result("healthiness", 5, 4),
        area_result("ingredient_menu_quality", 5, 4),
    ]
    for result in results:
        result.evaluations[1].schoolCode = "7010001"

    scores, outcome, winner = calculate_scores(request, results)

    assert [score.totalScore for score in scores] == [100.0, 80.0]
    assert outcome == "first"
    assert winner == scores[0].school


def test_analysis_request_requires_two_distinct_schools() -> None:
    request = build_request().model_dump(mode="json")
    request["schools"][1] = request["schools"][0]

    with pytest.raises(ValueError, match="서로 다른 학교"):
        AnalysisRequest.model_validate(request)


@pytest.mark.parametrize("selected", [date(2026, 7, 1), date(2026, 8, 14)])
def test_validate_analysis_date_accepts_current_and_previous_month(selected: date) -> None:
    validate_analysis_date(selected, today=date(2026, 8, 14))


@pytest.mark.parametrize("selected", [date(2026, 6, 30), date(2026, 8, 15)])
def test_validate_analysis_date_rejects_out_of_range_dates(selected: date) -> None:
    with pytest.raises(ValueError, match="직전 달"):
        validate_analysis_date(selected, today=date(2026, 8, 14))
