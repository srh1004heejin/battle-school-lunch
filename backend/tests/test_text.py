from app.text import parse_menu, parse_nutrition, parse_optional_text


def test_menu_parsing_preserves_allergy_text_and_removes_markup() -> None:
    value = "쌀밥<br/>김치찌개 (1.2.5.6.)<br><b>사과 &amp; 배</b>"

    assert parse_menu(value) == [
        "쌀밥",
        "김치찌개 (1.2.5.6.)",
        "사과 & 배",
    ]


def test_text_parsing_discards_script_content() -> None:
    assert parse_optional_text("국내산<script>alert(1)</script><br>미국산") == (
        "국내산\n미국산"
    )


def test_nutrition_parsing_preserves_labeled_and_unlabeled_values() -> None:
    assert parse_nutrition("탄수화물(g) : 90.1<br/>단백질(g)：25<br/>참고값") == {
        "탄수화물(g)": "90.1",
        "단백질(g)": "25",
        "정보": "참고값",
    }

