from __future__ import annotations

import asyncio
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sqlite3
from typing import Iterator, Protocol
import uuid

from .evaluation import AnalysisEngine, AnalysisRequest, AnalysisResult, StoredAnalysis


class AnalysisRepository(Protocol):
    def initialize(self) -> None: ...

    def save(self, request: AnalysisRequest, result: AnalysisResult) -> str: ...

    def get(self, analysis_id: str) -> StoredAnalysis | None: ...


class SqliteAnalysisRepository:
    def __init__(self, database_path: str, backup_path: str | None = None) -> None:
        self._database_path = Path(database_path)
        self._backup_path = Path(backup_path) if backup_path else None
        self._migration_directory = Path(__file__).resolve().parent / "migrations"

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        if (
            self._backup_path is not None
            and self._backup_path.is_file()
            and not self._database_path.exists()
        ):
            shutil.copy2(self._backup_path, self._database_path)
        with self._connection() as connection:
            current_version = connection.execute("PRAGMA user_version").fetchone()[0]
            for migration_path in sorted(self._migration_directory.glob("[0-9][0-9][0-9]_*.sql")):
                version = int(migration_path.name.split("_", maxsplit=1)[0])
                if version <= current_version:
                    continue
                connection.executescript(migration_path.read_text(encoding="utf-8"))
                applied_version = connection.execute("PRAGMA user_version").fetchone()[0]
                if applied_version != version:
                    raise RuntimeError(
                        f"{migration_path.name} 적용 후 user_version이 {version}이 아닙니다."
                    )
                current_version = applied_version
        self._sync_backup()

    def _sync_backup(self) -> None:
        if self._backup_path is None:
            return
        self._backup_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self._backup_path.with_name(f".{self._backup_path.name}.{uuid.uuid4()}.tmp")
        try:
            shutil.copy2(self._database_path, temporary_path)
            temporary_path.replace(self._backup_path)
        finally:
            temporary_path.unlink(missing_ok=True)

    def save(self, request: AnalysisRequest, result: AnalysisResult) -> str:
        analysis_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        with self._connection() as connection:
            school_ids: dict[tuple[str, str], int] = {}
            for school in request.schools:
                connection.execute(
                    """
                    INSERT INTO schools (education_office_code, school_code, name)
                    VALUES (?, ?, ?)
                    ON CONFLICT (education_office_code, school_code)
                    DO UPDATE SET name = excluded.name
                    """,
                    (school.educationOfficeCode, school.schoolCode, school.name),
                )
                row = connection.execute(
                    """
                    SELECT id FROM schools
                    WHERE education_office_code = ? AND school_code = ?
                    """,
                    (school.educationOfficeCode, school.schoolCode),
                ).fetchone()
                if row is None:
                    raise RuntimeError("저장한 학교를 다시 조회하지 못했습니다.")
                school_ids[(school.educationOfficeCode, school.schoolCode)] = row["id"]

            winner_school_id = None
            if result.winnerSchool is not None:
                winner_school_id = school_ids[
                    (result.winnerSchool.educationOfficeCode, result.winnerSchool.schoolCode)
                ]

            connection.execute(
                """
                INSERT INTO analysis_requests (
                    id, analysis_date, prompt, outcome, winner_school_id, summary,
                    key_reason, first_school_improvement, second_school_improvement,
                    quality_warnings, disclaimer, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    analysis_id,
                    request.date.isoformat(),
                    request.prompt,
                    result.outcome,
                    winner_school_id,
                    result.review.summary,
                    result.review.keyReason,
                    result.review.firstSchoolImprovement,
                    result.review.secondSchoolImprovement,
                    json.dumps(result.review.qualityWarnings, ensure_ascii=False),
                    result.disclaimer,
                    created_at,
                ),
            )

            scores_by_school = {
                (score.school.educationOfficeCode, score.school.schoolCode): score
                for score in result.scores
            }
            for position, school in enumerate(request.schools):
                key = (school.educationOfficeCode, school.schoolCode)
                score = scores_by_school[key]
                school_id = school_ids[key]
                connection.execute(
                    """
                    INSERT INTO analysis_schools (analysis_id, school_id, position, total_score)
                    VALUES (?, ?, ?, ?)
                    """,
                    (analysis_id, school_id, position, score.totalScore),
                )
                for area in score.areas:
                    connection.execute(
                        """
                        INSERT INTO agent_results (
                            analysis_id, school_id, area, rating, weight, weighted_score,
                            rationale, evidence, estimated_flags
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            analysis_id,
                            school_id,
                            area.area,
                            area.rating,
                            area.weight,
                            area.weightedScore,
                            area.rationale,
                            json.dumps(area.evidence, ensure_ascii=False),
                            json.dumps(area.estimatedFlags, ensure_ascii=False),
                        ),
                    )

        self._sync_backup()
        return analysis_id

    def get(self, analysis_id: str) -> StoredAnalysis | None:
        with self._connection() as connection:
            analysis = connection.execute(
                "SELECT * FROM analysis_requests WHERE id = ?",
                (analysis_id,),
            ).fetchone()
            if analysis is None:
                return None
            rows = connection.execute(
                """
                SELECT
                    s.education_office_code, s.school_code, s.name,
                    ars.position, ars.total_score,
                    ar.area, ar.rating, ar.weight, ar.weighted_score,
                    ar.rationale, ar.evidence, ar.estimated_flags
                FROM analysis_schools AS ars
                JOIN schools AS s ON s.id = ars.school_id
                JOIN agent_results AS ar
                    ON ar.analysis_id = ars.analysis_id AND ar.school_id = ars.school_id
                WHERE ars.analysis_id = ?
                ORDER BY ars.position, ar.id
                """,
                (analysis_id,),
            ).fetchall()

        schools: list[dict[str, str]] = []
        scores: list[dict[str, object]] = []
        for position in (0, 1):
            school_rows = [row for row in rows if row["position"] == position]
            if not school_rows:
                raise RuntimeError(f"{analysis_id} 분석의 학교별 결과가 완전하지 않습니다.")
            school = {
                "educationOfficeCode": school_rows[0]["education_office_code"],
                "schoolCode": school_rows[0]["school_code"],
                "name": school_rows[0]["name"],
            }
            schools.append(school)
            scores.append(
                {
                    "school": school,
                    "totalScore": school_rows[0]["total_score"],
                    "areas": [
                        {
                            "area": row["area"],
                            "rating": row["rating"],
                            "weight": row["weight"],
                            "weightedScore": row["weighted_score"],
                            "rationale": row["rationale"],
                            "evidence": json.loads(row["evidence"]),
                            "estimatedFlags": json.loads(row["estimated_flags"]),
                        }
                        for row in school_rows
                    ],
                }
            )

        winner = None
        if analysis["outcome"] != "tie":
            winner = schools[0 if analysis["outcome"] == "first" else 1]
        return StoredAnalysis.model_validate(
            {
                "analysisId": analysis["id"],
                "analysisDate": analysis["analysis_date"],
                "schools": schools,
                "prompt": analysis["prompt"],
                "scores": scores,
                "outcome": analysis["outcome"],
                "winnerSchool": winner,
                "review": {
                    "summary": analysis["summary"],
                    "keyReason": analysis["key_reason"],
                    "firstSchoolImprovement": analysis["first_school_improvement"],
                    "secondSchoolImprovement": analysis["second_school_improvement"],
                    "qualityWarnings": json.loads(analysis["quality_warnings"]),
                },
                "disclaimer": analysis["disclaimer"],
                "createdAt": analysis["created_at"],
            }
        )


class PersistingAnalysisEngine:
    def __init__(self, engine: AnalysisEngine, repository: AnalysisRepository) -> None:
        self._engine = engine
        self._repository = repository

    async def evaluate(self, request: AnalysisRequest) -> AnalysisResult:
        result = await self._engine.evaluate(request)
        analysis_id = await asyncio.to_thread(self._repository.save, request, result)
        return result.model_copy(update={"analysisId": analysis_id})
