from __future__ import annotations

from app.neis_schemas import MealServiceDietInfoRow
from app.normalization import dedupe_and_sort_meals, normalize_meal


def test_normalize_meal_preserves_allergy_text_and_strips_markup() -> None:
    meal = normalize_meal(
        MealServiceDietInfoRow.model_validate(
            {
                "ATPT_OFCDC_SC_CODE": "B10",
                "ATPT_OFCDC_SC_NM": "서울특별시교육청",
                "SD_SCHUL_CODE": "7010570",
                "SCHUL_NM": "한국중학교",
                "MMEAL_SC_CODE": "2",
                "MMEAL_SC_NM": "중식",
                "MLSV_YMD": "20260802",
                "DDISH_NM": "잡곡밥 (5.6.)<br/>된장찌개 <span>(5.6.)</span>",
                "ORPLC_INFO": "쌀: 국내산<br/>배추김치: 국내산",
                "CAL_INFO": "710.2 Kcal",
                "NTR_INFO": "탄수화물: 98.3g<br/>단백질: 25.1g",
            }
        )
    )

    assert meal.menu == ["잡곡밥 (5.6.)", "된장찌개 (5.6.)"]
    assert meal.origin == "쌀: 국내산\n배추김치: 국내산"
    assert meal.nutrition == {"탄수화물": "98.3g", "단백질": "25.1g"}


def test_normalize_meal_accepts_numeric_meal_count_from_neis() -> None:
    meal = normalize_meal(
        MealServiceDietInfoRow.model_validate(
            {
                "ATPT_OFCDC_SC_CODE": "R10",
                "SD_SCHUL_CODE": "8801090",
                "SCHUL_NM": "테스트학교",
                "MMEAL_SC_CODE": "2",
                "MLSV_YMD": "20260708",
                "MLSV_FGR": 321.0,
                "DDISH_NM": "현미밥",
            }
        )
    )

    assert meal.mealCount == "321"


def test_dedupe_and_sort_meals_keeps_first_unique_records_in_date_order() -> None:
    meal_a = normalize_meal(
        MealServiceDietInfoRow.model_validate(
            {
                "ATPT_OFCDC_SC_CODE": "B10",
                "ATPT_OFCDC_SC_NM": "서울특별시교육청",
                "SD_SCHUL_CODE": "7010570",
                "SCHUL_NM": "한국중학교",
                "MMEAL_SC_CODE": "2",
                "MMEAL_SC_NM": "중식",
                "MLSV_YMD": "20260802",
                "DDISH_NM": "A",
            }
        )
    )
    meal_b = normalize_meal(
        MealServiceDietInfoRow.model_validate(
            {
                "ATPT_OFCDC_SC_CODE": "B10",
                "ATPT_OFCDC_SC_NM": "서울특별시교육청",
                "SD_SCHUL_CODE": "7010570",
                "SCHUL_NM": "한국중학교",
                "MMEAL_SC_CODE": "2",
                "MMEAL_SC_NM": "중식",
                "MLSV_YMD": "20260801",
                "DDISH_NM": "B",
            }
        )
    )

    normalized = dedupe_and_sort_meals([meal_a, meal_b, meal_b])

    assert [meal.date.isoformat() for meal in normalized] == ["2026-08-01", "2026-08-02"]
