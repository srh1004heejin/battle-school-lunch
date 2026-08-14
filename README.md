# 급식배틀: GitHub Copilot 활용 초중고 급식 메뉴 조회 및 분석 앱 개발 워크숍

NEIS 공개 API를 활용해 초중고 급식 메뉴를 조회하고 AI 에이전트로 분석하는 웹 애플리케이션을 단계별로 구현하는 워크숍입니다. GitHub Copilot과 함께 요구사항 및 API 명세 작성부터 앱 개발, Azure 배포, MCP 서버와 멀티 에이전트 워크플로우 구현까지 진행합니다.

[워크숍 시작하기](docs/00-setup.md) | [전체 커리큘럼 보기](#커리큘럼) | [데모 앱 리포지토리](https://github.com/devkimchi/battle-school-lunch) | [템플릿으로 저장소 만들기](https://github.com/new?template_name=battle-school-lunch-workshop&template_owner=devkimchi)

## 워크숍에서 만드는 것

- 학교와 날짜 범위를 기준으로 급식 메뉴를 조회하는 웹 애플리케이션
- NEIS 공개 API를 연동하는 백엔드와 사용자 인터페이스
- Azure 배포 및 GitHub Actions 기반 테스트·배포 자동화
- 급식 정보 활용을 위한 MCP 서버
- 평가 루브릭에 따라 두 학교의 급식을 비교하는 멀티 에이전트 워크플로우

## 시작하기

워크숍을 시작하려면 GitHub 및 Azure 계정과 다음 도구가 필요합니다.

- [GitHub Copilot app](https://gh.io/app)
- [GitHub Copilot CLI](https://gh.io/copilot-cli)
- [GitHub CLI](https://gh.io/cli)
- [Azure CLI](https://aka.ms/az-cli)
- [Azure Developer CLI](https://aka.ms/azd-cli)

이 저장소를 포크하는 대신 템플릿으로 새 저장소를 만든 후 [개발 환경 설정](docs/00-setup.md)의 안내를 따라 진행하세요.

> [!TIP]
> 바로 시작하려면 [이 템플릿으로 새 저장소를 만드세요](https://github.com/new?template_name=battle-school-lunch-workshop&template_owner=devkimchi).

> [!NOTE]
> 완성된 애플리케이션을 직접 실행하거나 구현 결과를 비교하려면 [데모 앱 리포지토리](https://github.com/devkimchi/battle-school-lunch)를 참고하세요.

## 커리큘럼

| 단계 | 주제                                                                         |
|------|------------------------------------------------------------------------------|
| 00   | [개발 환경 설정](docs/00-setup.md)                                           |
| 01   | [`openapi.json` 명세 생성](docs/01-generate-openapi.md)                      |
| 02   | [`AGENTS.md` 문서 생성](docs/02-generate-agents-md.md)                       |
| 03   | [PRD 및 TRD 생성](docs/03-generate-prd-trd.md)                               |
| 04   | [앱 개발](docs/04-implement-app.md)                                          |
| 05   | [`AGENTS.md` 문서 수정](docs/05-update-agents-md.md)                         |
| 06   | [Azure에 앱 배포](docs/06-deplopy-to-azure.md)                               |
| 07   | [GitHub Actions로 테스트 및 배포 자동화](docs/07-generate-github-actions.md) |
| 08   | [MCP 서버 구현](docs/08-implement-mcp.md)                                    |
| 09   | [에이전트 분석 평가 항목 정의](docs/09-define-evaluation-rubric.md)          |
| 10   | [멀티 에이전트 워크플로우 구현](docs/10-implement-agent-workflow.md)         |
| 11   | [데이터베이스 연동](docs/11-integrate-database.md) (작성 예정)               |

## 저장소 구성

| 경로    | 설명                                 |
|---------|--------------------------------------|
| `data/` | API 명세 작성에 사용하는 원본 데이터 |
| `docs/` | 단계별 워크숍 가이드                 |

프론트엔드, 백엔드 및 배포 관련 소스는 워크숍을 진행하면서 참가자의 저장소에 생성됩니다.

## 추가 학습 자료

- [GitHub Copilot cloud agent 알아보기](https://docs.github.com/copilot/concepts/agents/coding-agent/about-coding-agent)
- [`AGENTS.md` 작성 가이드와 예제](https://agents.md/)
- [OpenAPI Specification](https://spec.openapis.org/oas/latest.html)
- [Azure Developer CLI 문서](https://learn.microsoft.com/azure/developer/azure-developer-cli/)
- [GitHub Actions 문서](https://docs.github.com/actions)
- [Model Context Protocol 소개](https://modelcontextprotocol.io/docs/getting-started/intro)
- [MCP Inspector](https://github.com/modelcontextprotocol/inspector)
- [Microsoft Agent Framework](https://aka.ms/agentframework)

## 프로젝트 안내

- 질문이나 도움이 필요하면 [지원 안내](SUPPORT.md)를 확인하세요.
- 프로젝트에 참여하려면 [기여 가이드](CONTRIBUTING.md)와 [행동 강령](CODE_OF_CONDUCT.md)을 확인하세요.
- 보안 문제는 [보안 정책](SECURITY.md)에 따라 비공개로 신고해 주세요.
- 이 프로젝트는 [MIT 라이선스](LICENSE)를 따릅니다.
