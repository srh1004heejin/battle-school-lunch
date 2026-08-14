from __future__ import annotations

import sqlite3

import httpx
import pytest

from app.database import PersistingAnalysisEngine, SqliteAnalysisRepository
from app.evaluation import AnalysisRequest, AnalysisResult
from app.main import create_app
from app.settings import Settings


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


def build_result() -> AnalysisResult:
    areas = [
        ("nutrition_balance", 5, 45, 45.0),
        ("healthiness", 4, 30, 24.0),
        ("ingredient_menu_quality", 3, 25, 15.0),
    ]
    return AnalysisResult.model_validate(
        {
            "scores": [
                {
                    "school": school,
                    "totalScore": 84.0 - index * 5,
                    "areas": [
                        {
                            "area": area,
                            "rating": rating - index,
                            "weight": weight,
                            "weightedScore": weighted - index,
                            "rationale": f"{area} 평가 근거",
                            "evidence": ["NEIS 확인값"],
                            "estimatedFlags": [],
                        }
                        for area, rating, weight, weighted in areas
                    ],
                }
                for index, school in enumerate(
                    [
                        {"educationOfficeCode": "B10", "schoolCode": "7010001", "name": "첫학교"},
                        {"educationOfficeCode": "C10", "schoolCode": "7010002", "name": "둘학교"},
                    ]
                )
            ],
            "outcome": "first",
            "winnerSchool": {
                "educationOfficeCode": "B10",
                "schoolCode": "7010001",
                "name": "첫학교",
            },
            "review": {
                "summary": "첫학교가 우수합니다.",
                "keyReason": "총점이 더 높습니다.",
                "firstSchoolImprovement": "현재 구성을 유지하세요.",
                "secondSchoolImprovement": "영양 균형을 개선하세요.",
                "qualityWarnings": ["일부 영양 정보가 없습니다."],
            },
        }
    )


class FakeEngine:
    async def evaluate(self, _: AnalysisRequest) -> AnalysisResult:
        return build_result()


@pytest.mark.asyncio
async def test_completed_analysis_is_stored_and_returned_by_api(tmp_path) -> None:
    database_path = tmp_path / "analyses.db"
    repository = SqliteAnalysisRepository(str(database_path))
    repository.initialize()
    engine = PersistingAnalysisEngine(FakeEngine(), repository)

    result = await engine.evaluate(build_request())

    assert result.analysisId is not None
    settings = Settings(neis_api_key="test-key", database_path=str(database_path))
    app = create_app(
        settings=settings,
        analysis_engine=FakeEngine(),
        analysis_repository=repository,
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://backend.test",
    ) as client:
        response = await client.get(f"/api/analyses/{result.analysisId}")

    assert response.status_code == 200
    stored = response.json()
    assert stored["analysisDate"] == "2026-08-14"
    assert [school["name"] for school in stored["schools"]] == ["첫학교", "둘학교"]
    assert stored["scores"][0]["areas"][0]["rating"] == 5
    assert stored["scores"][1]["totalScore"] == 79.0
    assert stored["outcome"] == "first"
    assert stored["review"]["summary"] == "첫학교가 우수합니다."


def test_failed_save_rolls_back_all_analysis_data(tmp_path) -> None:
    database_path = tmp_path / "analyses.db"
    repository = SqliteAnalysisRepository(str(database_path))
    repository.initialize()
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TRIGGER fail_agent_result
            BEFORE INSERT ON agent_results
            WHEN NEW.area = 'healthiness'
            BEGIN
                SELECT RAISE(ABORT, 'forced test failure');
            END
            """
        )

    with pytest.raises(sqlite3.IntegrityError, match="forced test failure"):
        repository.save(build_request(), build_result())

    with sqlite3.connect(database_path) as connection:
        counts = [
            connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("schools", "analysis_requests", "analysis_schools", "agent_results")
        ]
    assert counts == [0, 0, 0, 0]


def test_tied_analysis_is_stored_without_a_winner(tmp_path) -> None:
    repository = SqliteAnalysisRepository(str(tmp_path / "analyses.db"))
    repository.initialize()
    tied_result = build_result().model_copy(
        update={
            "outcome": "tie",
            "winnerSchool": None,
            "scores": [
                score.model_copy(update={"totalScore": 84.0})
                for score in build_result().scores
            ],
        }
    )

    analysis_id = repository.save(build_request(), tied_result)
    stored = repository.get(analysis_id)

    assert stored is not None
    assert stored.outcome == "tie"
    assert stored.winnerSchool is None


def test_database_is_restored_from_backup(tmp_path) -> None:
    database_path = tmp_path / "local" / "analyses.db"
    backup_path = tmp_path / "persistent" / "analyses.db"
    repository = SqliteAnalysisRepository(str(database_path), str(backup_path))
    repository.initialize()
    analysis_id = repository.save(build_request(), build_result())

    database_path.unlink()
    restored_repository = SqliteAnalysisRepository(str(database_path), str(backup_path))
    restored_repository.initialize()

    stored = restored_repository.get(analysis_id)
    assert stored is not None
    assert stored.review.summary == "첫학교가 우수합니다."
