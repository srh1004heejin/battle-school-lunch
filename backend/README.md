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

## 분석 결과 데이터베이스

분석 결과는 별도 서버 없이 로컬 개발과 단일 컨테이너 배포에서 일관되게 사용할 수
있고, 학교·분석 요청·에이전트별 점수 사이의 관계와 트랜잭션을 보장하는 SQLite에
저장합니다. 기본 파일은 `data/analyses.db`이며 `DATABASE_PATH`로 변경할 수 있습니다.
Docker Compose에서는 `analysis-data` 볼륨에 파일을 보존합니다.

스키마는 다음 관계로 구성됩니다.

- `schools`: 교육청 코드와 학교 코드로 식별되는 학교
- `analysis_requests`: 분석 날짜, 프롬프트, 승패/동점, 총평과 비교 결과
- `analysis_schools`: 분석 요청과 두 학교 및 총점의 연결
- `agent_results`: 학교별 세 전문 에이전트의 평점, 가중 점수, 근거와 추정 표시

애플리케이션 시작 시 `app/migrations/001_initial.sql`이 자동 적용됩니다. 새 마이그레이션은
번호가 증가하는 SQL 파일로 추가하고 `PRAGMA user_version`을 함께 올립니다. 현재
마이그레이션을 수동 적용하려면 백엔드 디렉터리에서 아래 명령을 실행합니다.

```sh
python -c "from app.database import SqliteAnalysisRepository; from app.settings import Settings; s=Settings.from_env(); SqliteAnalysisRepository(s.database_path).initialize()"
```

완료된 분석 응답의 `analysisId`를
`GET /api/analyses/{analysisId}`에 전달하면 분석 날짜, 두 학교, 에이전트별 결과와
점수, 승패/동점 및 총평을 다시 조회할 수 있습니다. 분석 저장은 하나의 트랜잭션으로
실행되어 일부 행만 남지 않습니다.
