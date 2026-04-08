# BI-Agent — AI 에이전트 가이드

이 가이드는 Claude Code 이외의 AI 도구(Codex, OpenCode 등)에서 BI-Agent를 사용할 때의 지침이다.

## 프로젝트 개요

BI-Agent MCP 서버: DA가 자연어로 데이터를 분석하는 도구. 176개 MCP 도구 포함.
진입점: `bi_agent_mcp/server.py`

## 핵심 워크플로우: bi-solve

모든 분석은 `skills/bi-solve.md`의 5개 Gate를 따라 진행한다.

비즈니스 문제를 받으면:
1. `skills/bi-solve.md` 파일을 읽는다
2. 그 안의 [G1]~[G5] Gate를 순서대로 실행한다
3. Gate를 건너뛰지 않는다
4. 한 번에 하나의 질문만 한다

## /bi-history — 분석 히스토리 검색

과거 분석 세션을 검색하고 관리한다. `skills/bi-history.md` 파일을 읽고 지침을 따른다.

| 명령 | 동작 |
|------|------|
| `bi-history` (인수 없음) | 최근 10개 세션 목록 |
| `bi-history "매출"` | 키워드로 세션 검색 |
| `bi-history --type diagnostic` | 진단형 세션만 조회 |
| `bi-history --result confirmed` | 가설 확인된 세션만 조회 |
| `bi-history "광고" --deep` | LLM 심층 검색 |

사용 MCP 도구: `search_history(query, type, result, limit)`, `tag_session(session_id, add_tags)`

## 주요 파일 위치

| 역할 | 경로 |
|---|---|
| bi-solve 워크플로우 | `skills/bi-solve.md` |
| 분석 유형별 프레임워크 | `context/playbooks/{type}.md` |
| 소크라테스 질문 세트 | `context/socratic_questions/{type}_qs.md` |
| 분석 세션 기록 | `context/sessions/` |
| 히스토리 인덱스 DB | `context/sessions/history.db` |
| bi-history 워크플로우 | `skills/bi-history.md` |
| 비즈니스 컨텍스트 | `context/01_business_context.md` 등 |

## 분석 유형

| 유형 | 대표 질문 |
|---|---|
| diagnostic | "왜 X가 바뀌었나?" |
| exploratory | "X가 어떻게 생겼나?" |
| comparative | "A vs B 중 뭐가 나은가?" |
| predictive | "앞으로 어떻게 될까?" |
| decision | "어떻게 해야 하나?" |
| monitoring | "계속 봐야 할 것은?" |

## MCP 도구 사용

분석 실행 시 bi_agent_mcp 서버의 MCP 도구를 활용한다.
주요 도구: `run_query`, `bi_start`, `bi_orchestrate`, `generate_report`, `generate_dashboard`

도구 선택 가이드: `context/04_analysis_patterns.md` 참조
