# NEIS 급식 MCP 서버

학교 검색과 중식 조회 도구를 제공하는 독립 Python MCP 서버입니다. 공식 MCP
SDK 1.x의 Streamable HTTP 전송을 사용하며 엔드포인트는 `/mcp`입니다.

## 실행

```powershell
cd src/mcp
python -m pip install -e ".[dev]"
$env:NEIS_API_KEY='your-real-key'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

MCP Inspector는 다음 명령으로 실행한 뒤 transport에 `Streamable HTTP`, URL에
`http://127.0.0.1:8001/mcp`를 지정합니다.

```powershell
npx -y @modelcontextprotocol/inspector
```

## 도구

- `search_schools`: 부분 학교명으로 학교명, 교육청 코드·이름, 학교 코드 검색
- `get_lunch_meals`: 학교 식별 정보와 `YYYY-MM-DD` 날짜 범위로 중식 조회

검색 또는 급식 결과가 없거나 입력 및 NEIS 요청에 문제가 있으면 도구 호출은
`isError: true`와 안정적인 오류 코드·메시지를 반환합니다. API 키와 외부 응답
원문은 오류에 포함하지 않습니다.

## 테스트

```powershell
cd src/mcp
python -m pytest
```
