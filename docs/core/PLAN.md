# bi-agent-mcp 전략 및 로드맵 (PLAN.md)

> **[ 🗺️ 전략/로드맵 ]** · [ 🛠️ 상세 설계 (DETAILED_SPEC)](./DETAILED_SPEC.md) · [ 📋 현재 실행 (TODO)](./TODO.md) · [ 📜 변경 이력 (CHANGELOG)](./CHANGELOG.md)

---

## 1. 프로젝트 비전

**bi-agent-mcp** 는 LLM 클라이언트(Claude, Cursor 등)가 데이터베이스 및 파일 기반 분석 도구를 자연어로 호출할 수 있는 **MCP(Model Context Protocol) 서버 패키지**입니다.

기존 TUI/LangGraph 오케스트레이터 코드를 제거하고, 표준 MCP 인터페이스를 통해 DB 연결·쿼리·분석·리포트 생성 기능을 LLM 클라이언트에 직접 제공합니다.

---

## 2. 로드맵

### Phase 1 — 레거시 정리 + 데이터 소스 확장 (✅ 완료 — 2026-03-20)

- 구 TUI/LangGraph 오케스트레이터 코드(backend/, .agent/, .agents/, .serena/ 등) 완전 제거
- 연결 영속성: `~/.config/bi-agent/connections.json` 저장/복원
- Snowflake 지원 추가 (`snowflake-connector-python>=3.0`)
- Excel/CSV 파일 데이터 소스 추가 (`tools/files.py`, DuckDB 기반 SQL)
- docs 전면 업데이트

---

### Phase 2 — 도메인 지식 시스템 + BI 스킬 + MCP 도구 강화 (✅ 완료 — 2026-03-20)

- `load_domain_context` MCP 도구 추가 (context/ 마크다운 파일 로드)
- `list_query_history` MCP 도구 추가 (쿼리 실행 이력 조회)
- `suggest_analysis` 도메인 컨텍스트 연동 개선 (question 파라미터, context/ 자동 탐색)
- context/ 비즈니스 도메인 지식 템플릿 시스템 구축 (README + 5개 마크다운 템플릿)
- .claude/commands/ BI 스킬 5개 생성 (/bi-connect, /bi-explore, /bi-analyze, /bi-report, /bi-domain)

---

### Phase 3 — 테스트 품질 + 멀티유저 (🔲 예정)

- GA4/Amplitude 단위 테스트 (httpx/google-auth mock)
- pytest-cov 활성화 + 80% 커버리지 게이트
- E2E 통합 테스트 (로컬 DB — SQLite/Docker PostgreSQL)
- MCP 서버 토큰 인증 레이어

---

Copyright © 2026 BI-Agent Team. All rights reserved.
