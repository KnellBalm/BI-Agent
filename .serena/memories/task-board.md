# Task Board (bi-agent-impl / antigravity)

## P1: Core Infrastructure (v0) — Claude Code
- [x] **Task #1**: ✅ 프로젝트 기반 구조 (pyproject.toml, server.py, config.py, __init__.py)
- [x] **Task #2**: ✅ auth/credentials.py — OS 키체인 + 환경변수 자격증명 관리
- [x] **Task #3**: ✅ auth/oauth.py — Google OAuth 2.0 PKCE 흐름
- [x] **Task #4**: ✅ tools/db.py — connect_db, list_connections, get_schema, run_query, profile_table

## P2: External Data Integration (v1)
- [x] **Task #5**: ✅ tools/ga4.py — connect_ga4, get_ga4_report
  - [x] OAuth PKCE 흐름 호출 및 `_ga4_connections` 등록
  - [x] GA4 Data API v1 호출 및 마크다운 테이블 반환
  - [ ] 단위 테스트 작성 (추후 통합 단계)
- [x] **Task #6**: ✅ tools/amplitude.py — connect_amplitude, get_amplitude_events
  - [x] API/Secret Key 등록 및 연결 테스트
  - [x] Amplitude Export API 호출 및 마크다운 테이블 반환
  - [ ] 단위 테스트 작성 (추후 통합 단계)
- [x] **Task #7**: ✅ tools/analysis.py — suggest_analysis, generate_report, save_query, list_saved_queries
  - [x] 규칙 기반 분석 제안 로직 (`suggest_analysis`)
  - [x] 마크다운 보고서 생성 (`generate_report`)
  - [x] 쿼리 JSON 저장 및 조회 기능
  - [ ] 단위 테스트 작성 (추후 통합 단계)

## P2: Output Generation (v2)
- [x] **Task #8**: ✅ tools/tableau.py — generate_twbx
  - [x] 마크다운 테이블 파서 작성
  - [x] .twb XML 생성 및 .twbx 패키징 로직 작성
  - [x] `TableauMetadataEngine` 연동 고려
  - [ ] 단위 테스트 작성 (추후 통합 단계)

## Legend
- ⏳ Ready
- 🏃 Running
- ✅ Done
- ❌ Failed
