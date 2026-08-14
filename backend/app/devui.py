from __future__ import annotations

from agent_framework.devui import serve

from .agent_workflow import GitHubCopilotEvaluationEngine
from .analysis_entity import create_analysis_workflow
from .settings import Settings


def main() -> None:
    settings = Settings.from_env()
    workflow = create_analysis_workflow(GitHubCopilotEvaluationEngine(settings))
    serve(entities=[workflow], host="127.0.0.1", port=8090, auto_open=True)


if __name__ == "__main__":
    main()
