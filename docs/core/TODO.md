# bi-agent-mcp 개발 현황 (TODO.md)

> [ 🗺️ 전략/로드맵 (PLAN)](./PLAN.md) · [ 🛠️ 상세 설계 (DETAILED_SPEC)](./DETAILED_SPEC.md) · **[ 📋 현재 실행 ]** · [ 📜 변경 이력 (CHANGELOG)](./CHANGELOG.md)

---

> 마지막 업데이트: 2026-03-20 (Phase 2 완료)

---

## ✅ Phase 1 완료 항목 (2026-03-20)

- [x] 레거시 코드 정리 (backend/, .agent/, .agents/, .serena/, analyses/, bin/ 등 제거)
- [x] 연결 영속성 (`~/.config/bi-agent/connections.json` 저장/복원)
- [x] Snowflake 지원 (`snowflake-connector-python>=3.0`, connect_db/get_schema/run_query/profile_table)
- [x] Excel/CSV 파일 데이터 소스 (`tools/files.py` 신규, duckdb 기반 SQL)
- [x] docs 전면 업데이트

---

## ✅ Phase 2 완료 항목 (2026-03-20)

- [x] `load_domain_context` MCP 도구 추가 (context/ 마크다운 파일 로드)
- [x] `list_query_history` MCP 도구 추가 (쿼리 실행 이력 조회)
- [x] `suggest_analysis` 도메인 컨텍스트 연동 개선 (question 파라미터, context/ 자동 탐색)
- [x] context/ 비즈니스 도메인 지식 템플릿 시스템 구축 (README + 5개 마크다운 템플릿)
- [x] .claude/commands/ BI 스킬 5개 생성 (/bi-connect, /bi-explore, /bi-analyze, /bi-report, /bi-domain)

---

## 🔲 Phase 3 예정 항목

- [ ] GA4/Amplitude 단위 테스트 (httpx/google-auth mock)
- [ ] pytest-cov 활성화 + 80% 커버리지 게이트
- [ ] E2E 통합 테스트 (SQLite/Docker PostgreSQL)
- [ ] MCP 서버 토큰 인증 레이어

---

Copyright © 2026 BI-Agent Team. All rights reserved.
