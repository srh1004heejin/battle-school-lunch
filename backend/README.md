# Backend

FastAPI 기반 내부 API입니다.

급식 분석은 Microsoft Agent Framework의 `ConcurrentBuilder`로 세 전문 평가를
병렬 실행한 뒤, 애플리케이션 코드가 가중 점수를 계산하고 최종 평가 에이전트가
순차적으로 품질을 검토합니다. 모델 공급자는 GitHub Copilot SDK이며 급식 데이터는
별도 MCP 서버를 통해 기존 백엔드 API에서 가져옵니다. 프론트엔드 통신에는 AG-UI
프로토콜을 사용합니다.

## 스크립트

- `python -m pip install -e ".[dev]"`: 개발 의존성 설치
- `python -m pytest`: 단위/통합 테스트
- `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`: 로컬 실행
- `python -m app.mcp_server`: MCP Streamable HTTP 서버 실행(기본
  `127.0.0.1:8001`)
- `python -m app.devui`: 분석 워크플로를 Agent Framework DevUI에서 확인

GitHub Copilot CLI 인증이 필요합니다. 필요하면 `GITHUB_COPILOT_MODEL`로 모델을
지정하고, `AGENT_MCP_URL`로 MCP 주소를 설정합니다. DevUI는 개발 확인용이며 운영
UI로 사용하지 않습니다.

Docker처럼 대화형 로그인을 사용할 수 없는 환경에서는 Copilot 사용 권한이 있는
토큰을 `COPILOT_GITHUB_TOKEN` 환경 변수로 주입합니다. 토큰을 이미지나 소스에
포함하지 마세요.
