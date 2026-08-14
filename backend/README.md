# Backend

FastAPI 기반 내부 API입니다.

## 스크립트

- `python -m pip install -e ".[dev]"`: 개발 의존성 설치
- `python -m pytest`: 단위/통합 테스트
- `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`: 로컬 실행
