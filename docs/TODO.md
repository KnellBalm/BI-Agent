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

**목표**: BI 툴 메타데이터(.twbx, .pbix) 지능형 수정 및 도구별 전문 가이드/로직 생성 구현

#### 3.1 기능 고도화 (Data & SaaS)
- [ ] **SaaS 연동**: Snowflake, BigQuery MCP 서버 연동 테스트
- [ ] **Cloud Storage**: Amazon S3 내의 데이터 조회 기능
- [ ] **MySQL 연동 검증** (Docker 컨테이너 활용)
- [x] **Excel 연동 구현** (pandas 연동 및 자연어 질의)

#### 3.2 BI Intelligence & Library
- [ ] **Tableau Metadata (.twbx XML)**: XML 기반 시각화 및 데이터 바인딩 자동 수정
- [ ] **Power BI Logic (DAX)**: 고도화된 DAX 계산식 및 M 문구 생성 기능
- [ ] **UI Guide RAG**: BI 도구 공식 문서 기반의 조작 가이드 에이전트 구축
- [x] **TUI 고도화**: `rich` 라이브러리를 통한 분석 프로세스 시각화
- [ ] **BI Tool Agent 강화**: 시각화 명세(JSON/XML) 처리 및 스타일 튜닝 보강

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

- [ ] Tableau / Power BI Meta-Intelligence (Advanced)
- [ ] UI Guide Assistant (RAG) Extension
- [ ] Enterprise Connector expansion (SAP, etc)
- [ ] Self-Healing Visualization Logic for 연동 테스트

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
