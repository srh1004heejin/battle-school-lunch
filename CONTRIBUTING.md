# 급식배틀에 기여하기

프로젝트에 기여해 주셔서 감사합니다. 이슈 또는 Pull Request를 제출하기
전에 이 안내서를 읽어 주세요.

## 행동 강령

이 프로젝트는 [Contributor Covenant 행동 강령](CODE_OF_CONDUCT.md)을
준수합니다. 프로젝트에 참여하면 이 행동 강령을 지키는 데 동의하는 것으로
간주합니다.

## 시작하기

1. 리포지토리를 포크합니다.
2. 포크한 리포지토리를 복제합니다.
3. `feat/`, `fix/`, `docs/` 중 하나를 사용해 브랜치를 생성합니다.
4. 변경할 구성 요소의 의존성을 설치합니다.
5. 코드를 변경하고 테스트를 추가하거나 수정합니다.
6. 관련 검사를 로컬에서 실행합니다.

프론트엔드 설정 및 검사:

```sh
cd frontend
npm install
npm run build
npm test
```

백엔드 설정 및 검사:

```sh
cd backend
python -m venv .venv
# 사용 중인 셸에서 .venv를 활성화한 후 실행합니다.
python -m pip install -e ".[dev]"
pytest
```

전체 애플리케이션 실행:

```sh
docker compose up --build
```

## Pull Request 절차

1. 각 Pull Request는 하나의 변경 사항에 집중합니다.
2. 동작 또는 설정이 바뀌면 관련 문서를 수정합니다.
3. 버그 수정과 새로운 기능에 대한 테스트를 추가합니다.
4. 모든 CI 검사가 통과하는지 확인합니다.
5. `Closes #123` 형식으로 관련 이슈를 연결합니다.

## 커밋 규칙

[Conventional Commits](https://www.conventionalcommits.org/) 규칙을
사용합니다.

- `feat:` 새로운 기능
- `fix:` 버그 수정
- `docs:` 문서 변경
- `test:` 테스트 추가 또는 변경
- `refactor:` 동작 변경이 없는 코드 구조 개선
- `chore:` 유지 관리 및 의존성 변경

## 버그 신고 및 기능 제안

`.github/ISSUE_TEMPLATE/`에 있는 구조화된 양식을 사용해 주세요. 보안
취약점은 공개적으로 신고하지 말고 [SECURITY.md](SECURITY.md)의 안내를
따라 주세요.
