from __future__ import annotations

from agent_framework import Message, WorkflowBuilder, WorkflowContext, executor
from pydantic import ValidationError

from .evaluation import AnalysisEngine, AnalysisRequest


def create_analysis_workflow(engine: AnalysisEngine):
    @executor(id="evaluate_school_lunch")
    async def evaluate_school_lunch(messages: list[Message], ctx: WorkflowContext) -> None:
        try:
            if not messages:
                raise ValueError("분석 요청 메시지가 비어 있습니다.")
            request = AnalysisRequest.model_validate_json(messages[-1].text)
            result = await engine.evaluate(request)
        except (ValidationError, ValueError) as exc:
            raise ValueError(f"급식 분석 요청을 처리할 수 없습니다: {exc}") from exc
        await ctx.yield_output(result.model_dump_json())

    return WorkflowBuilder(start_executor=evaluate_school_lunch).build()
