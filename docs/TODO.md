# BI-Agent 개발 TODO 리스트

> 최종 업데이트: 2026-01-22
> 현재 단계: Phase 3 - MCP 서버 패키지화

---

## 완료된 작업 ✅

### Phase 1: 기반 구축 ✓

- [x] 프로젝트 구조 및 의존성 설정
- [x] MCP 서버 구현 (PostgreSQL, MySQL, Excel)
- [x] 환경 변수 템플릿 (`.env.example`)
- [x] Python 가상환경 및 의존성 설치
- [x] MCP 클라이언트 연결 테스트 완료

### Phase 2: Agent 구현 ✓

- [x] Data Source Agent (MCP 클라이언트, SQL 생성, 데이터 조회)
- [x] BI Tool Agent (JSON 파서, 시각화 디코더, 데이터모델 수정)
- [x] Orchestrator Agent (LLM Provider, LangGraph 워크플로우, CLI)

---

## 진행 중 🚧

### Phase 3: 기능 고도화 및 검증

**목표**: 모든 데이터 소스(SaaS 포함)와 BI 수정 기능을 완벽하게 구현하고 TUI 제공

#### 3.1 기능 고도화 (Data & SaaS)
- [ ] **SaaS 연동**: Snowflake, BigQuery MCP 서버 연동 테스트
- [ ] **Cloud Storage**: Amazon S3 내의 데이터 조회 기능
- [ ] **MySQL 연동 검증** (Docker 컨테이너 활용)
- [ ] **Excel 연동 구현** (pandas 연동 및 자연어 질의)

#### 3.2 UI/UX 및 자동화
- [ ] **TUI (Terminal User Interface) 구현**: `rich`/`textual` 활용
- [ ] **Airflow 연동**: 쿼리를 Airflow DAG로 변환하는 PoC 진행
- [ ] **BI Tool Agent 강화**: Base64 시각화 옵션 처리 보강

#### 3.3 통합 테스트 및 검증
- [ ] SaaS + DB + Excel 교차 질의 테스트
- [ ] `backend/tests/verify_bi_agent_mcp.js`를 사용한 브릿지 검증
- [ ] `backend/main.py` CLI/TUI 풀 시나리오 테스트

---

### Phase 4: 패키징 및 배포

**목표**: 완성된 에이전트를 MCP 패키지 형태로 배포

#### 4.1 MCP 서버 패키지화
- [ ] `bin/bi-agent-mcp.js` 안정화 (venv 경로 처리 등)
- [ ] `backend/mcp_bridge.py` 기능 확장
- [ ] `package.json` npm 퍼블리시 설정

#### 4.2 배포 문서 및 가이드
- [ ] `docs/USER_GUIDE.md` 최신화
- [ ] Claude Desktop / Cursor 연동 가이드 작성
- [ ] npx 실행 확인

---

## Future Plan 🚀

- [ ] Snowflake / BigQuery / S3 MCP 서버
- [ ] Airflow 통합
- [ ] Ollama 통합 (폐쇄망)
- [ ] Tableau 연동

---

## 개발 환경

```bash
# 로컬 DB 실행
cd /mnt/z/GitHub/docker-db && docker compose up -d
```

| 서비스 | 포트 | 인증 |
|--------|------|------|
| PostgreSQL | 5433 | biagent/biagent123 |
| MySQL | 3307 | biagent/biagent123 |

---

**마지막 업데이트**: 2026-01-22
