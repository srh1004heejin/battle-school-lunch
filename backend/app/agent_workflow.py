from __future__ import annotations

import json
import asyncio
from contextlib import AsyncExitStack
from typing import Any, Protocol

from agent_framework.github import GitHubCopilotAgent, GitHubCopilotOptions
from agent_framework.orchestrations import ConcurrentBuilder
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from .evaluation import (
    AREA_WEIGHTS,
    AnalysisRequest,
    AnalysisResult,
    AreaEvaluation,
    FinalReview,
    calculate_scores,
    parse_json_model,
    validate_analysis_date,
)
from .settings import Settings

_COMMON_RULES = """
EVALUATION_RUBRIC.md의 기준만 적용한다. 워크플로가 MCP로 조회해 제공한 두 학교의 선택 날짜 중식만 사용한다.
한 학교라도 중식 데이터가 없으면 성공 결과를 만들지 말고 오류를 명시한다.
NEIS에서 확인할 수 없는 수치를 추정하지 않는다. 메뉴명만으로 재료나 조리법을 단정하지 않는다.
각 학교에 대해 1~5 정수 평점, 입력 데이터에서 직접 확인되는 근거, 제한적 추정 표시를 작성한다.
마크다운 없이 요청된 JSON 객체 하나만 반환한다.
"""

_AREA_INSTRUCTIONS: dict[str, str] = {
    "nutrition_balance": _COMMON_RULES
    + """
영양 균형(45%)만 평가한다. 열량, 영양정보, 확인 가능한 식품군 구성을 사용한다.
반환 스키마:
{"area":"nutrition_balance","evaluations":[{"educationOfficeCode":"...","schoolCode":"...","score":1,"rationale":"...","evidence":["..."],"estimatedFlags":[]}]}
""",
    "healthiness": _COMMON_RULES
    + """
건강성(30%)만 평가한다. 수치가 있으면 나트륨·당류·지방을 우선하고, 없으면 메뉴명에서 직접 확인되는 신호만 제한적으로 사용한다.
반환 스키마:
{"area":"healthiness","evaluations":[{"educationOfficeCode":"...","schoolCode":"...","score":1,"rationale":"...","evidence":["..."],"estimatedFlags":[]}]}
""",
    "ingredient_menu_quality": _COMMON_RULES
    + """
식재료 및 메뉴 품질(25%)만 평가한다. 식재료 다양성, 메뉴 조화와 중복, 한 끼 완성도를 사용한다.
신선도와 학생 선호도는 추정하지 않는다.
반환 스키마:
{"area":"ingredient_menu_quality","evaluations":[{"educationOfficeCode":"...","schoolCode":"...","score":1,"rationale":"...","evidence":["..."],"estimatedFlags":[]}]}
""",
}


class GitHubCopilotEvaluationEngine:
    def __init__(self, settings: Settings, meal_provider: "MealProvider | None" = None) -> None:
        self._settings = settings
        self._meal_provider = meal_provider or McpMealProvider(settings.agent_mcp_url)

    def _options(self) -> GitHubCopilotOptions:
        if self._settings.github_copilot_model:
            return GitHubCopilotOptions(
                model=self._settings.github_copilot_model,
                timeout=self._settings.github_copilot_timeout_seconds,
            )
        return GitHubCopilotOptions(timeout=self._settings.github_copilot_timeout_seconds)

    async def evaluate(self, request: AnalysisRequest) -> AnalysisResult:
        validate_analysis_date(request.date)
        meal_data = await self._meal_provider.get_meals(request)
        request_payload = json.dumps(
            {
                "schools": [school.model_dump() for school in request.schools],
                "date": request.date.isoformat(),
                "userPrompt": request.prompt,
                "mealDataFromMcp": meal_data,
            },
            ensure_ascii=False,
        )
        captured: list[AreaEvaluation] = []

        async with AsyncExitStack() as stack:
            specialists: list[GitHubCopilotAgent[GitHubCopilotOptions]] = []
            for area, instructions in _AREA_INSTRUCTIONS.items():
                agent = GitHubCopilotAgent(
                    id=area,
                    name=area,
                    instructions=instructions,
                    default_options=self._options(),
                )
                specialists.append(await stack.enter_async_context(agent))

            async def aggregate(results: list[Any]) -> str:
                parsed: list[AreaEvaluation] = []
                for result in results:
                    response_text = result.agent_response.text
                    if not response_text.strip():
                        raise ValueError(f"{result.executor_id} 평가 결과가 비어 있습니다.")
                    parsed.append(parse_json_model(response_text, AreaEvaluation))
                captured.extend(parsed)
                return "세 전문 평가가 완료되었습니다."

            workflow = (
                ConcurrentBuilder(participants=specialists)
                .with_aggregator(aggregate)
                .build()
            )
            await workflow.run(request_payload)

            scores, outcome, winner_school = calculate_scores(request, captured)
            review_agent = await stack.enter_async_context(
                GitHubCopilotAgent(
                    id="final_reviewer",
                    name="final_reviewer",
                    instructions=(
                        "당신은 학교 급식 비교의 최종 품질 검토자다. 새 점수를 부여하거나 계산된 점수를 변경하지 않는다. "
                        "전문 평가가 각 영역 기준을 지켰는지, 모든 핵심 주장에 입력 근거가 있는지, 평가 간 모순·근거 부족·"
                        "과도한 추정이 있는지 검토한다. 승자 또는 동점과 핵심 이유, 양쪽 학교의 실행 가능한 개선안을 한국어로 쓴다. "
                        "마크다운 없이 다음 JSON만 반환한다: "
                        '{"summary":"...","keyReason":"...","firstSchoolImprovement":"...",'
                        '"secondSchoolImprovement":"...","qualityWarnings":[]}'
                    ),
                    default_options=self._options(),
                )
            )
            review_payload = json.dumps(
                {
                    "request": json.loads(request_payload),
                    "weights": AREA_WEIGHTS,
                    "scores": [score.model_dump() for score in scores],
                    "outcome": outcome,
                    "winnerSchool": winner_school.model_dump() if winner_school else None,
                    "specialistEvaluations": [result.model_dump() for result in captured],
                },
                ensure_ascii=False,
            )
            review_response = await review_agent.run(review_payload)
            review = parse_json_model(review_response.text, FinalReview)

        return AnalysisResult(
            scores=scores,
            outcome=outcome,
            winnerSchool=winner_school,
            review=review,
        )


class MealProvider(Protocol):
    async def get_meals(self, request: AnalysisRequest) -> list[dict[str, Any]]: ...


class McpMealProvider:
    def __init__(self, url: str) -> None:
        self._url = url

    async def get_meals(self, request: AnalysisRequest) -> list[dict[str, Any]]:
        async with streamable_http_client(self._url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                async def fetch_school(school_code: str, office_code: str) -> dict[str, Any]:
                    result = await session.call_tool(
                        "get_lunch_meal",
                        {
                            "education_office_code": office_code,
                            "school_code": school_code,
                            "meal_date": request.date.isoformat(),
                        },
                    )
                    if result.isError or result.structuredContent is None:
                        raise ValueError(f"{school_code}의 중식 데이터를 MCP에서 가져오지 못했습니다.")
                    payload = result.structuredContent
                    if set(payload) == {"result"} and isinstance(payload["result"], dict):
                        payload = payload["result"]
                    meals = payload.get("meals")
                    if not isinstance(meals, list) or not meals:
                        raise ValueError("선택한 학교 중 한 곳 이상에 해당 날짜 중식 데이터가 없습니다.")
                    return payload

                return await asyncio.gather(
                    *[
                        fetch_school(school.schoolCode, school.educationOfficeCode)
                        for school in request.schools
                    ]
                )
