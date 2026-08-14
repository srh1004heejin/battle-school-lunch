# Frontend

React + strict TypeScript 기반 UI입니다.

상단 탭에서 급식 조회와 급식 분석 페이지를 전환합니다. 분석 페이지는 무작위
학교 10곳 중 두 곳과 직전 달 또는 이번 달의 날짜를 선택하고, 수정 가능한
프롬프트를 Microsoft Agent Framework의 AG-UI 엔드포인트로 전송합니다.

## 스크립트

- `npm run dev`: Vite 개발 서버
- `npm run lint`: oxlint 검사
- `npm test`: Vitest 통합 테스트
- `npm run build`: 프로덕션 번들
- `npm run test:e2e`: Playwright E2E
