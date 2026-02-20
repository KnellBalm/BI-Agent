# BI-Agent Next-Gen: AaC (Analysis as Code) 구현계획

> **컨셉**: `plan.md` 마크다운 문서 → 에이전트 자율 실행 → 완성된 대시보드/리포트 패키지
> **철학**: IaC(Infrastructure as Code)에서 차용한 선언형, 버전 관리 가능, 재현 가능한 데이터 분석
> **워크플로우 패러다임**: Cursor Composer 방식의 **하이브리드 REPL (채팅창 내부 코드/마크다운 에디터 결합)**

---

## 1. 개요 및 방향성 전환
단순 대화형 챗봇에서 벗어나, 마크다운 템플릿(plan.md)을 작성하면 에이전트가 완벽한 시각화/분석 리포트를 빌드해주는 **AaC 패키지** 형태로 진화합니다.
사용자 피드백을 수용하여, 밖에서 독립 스크립트로 도는 형태가 아닌 **`bi-agent` REPL을 구동시킨 상태에서 마크다운을 직접 편집하고 에이전트에게 지시를 내리는 Cursor Composer 방식**으로 설계를 대폭 수정했습니다.

## 2. REPL-First 하이브리드 워크플로우 (User Journey)
기존 `main.py`의 Prompt Toolkit 기반 스크롤링 REPL에 아래 워크플로우를 완벽히 통폐합합니다.

### 2.1 슬래시 명령어 명세 (내부 명령어 편입)
독립적인 `bi-agent-aac` 명령어는 폐기하고 `main.py` REPL 내부 슬래시 명령어로 통폐합합니다.

| REPL 내부 명령어 | 설명                                                                                 |
| ---------------- | ------------------------------------------------------------------------------------ |
| `/init`          | 현재 작업 디렉토리에 `plan.md` 템플릿 및 `skills/` 폴더 스캐폴딩 생성                |
| `/edit plan`     | **(신규) 플랜 에디터 모드 진입**. UI 모달 또는 화면 분할을 통한 마크다운 편집기 오픈 |
| `/edit skills`   | 지식 베이스(Skills) 마크다운 편집기 모드 진입                                        |
| `/build`         | 작성된 `plan.md`를 바탕으로 분석 파이프라인 가동 (오케스트레이터 호출)               |
| `/export [fmt]`  | 최종 완료된 대시보드를 HTML/Streamlit/PDF 지정 포맷으로 익스포트                     |

### 2.2 사용자 경험 시나리오 (Workflow)
```
$ bi-agent   # 앱 실행 (일반 채팅 콘솔 모드 진입)
> /init
   [시스템] 현재 디렉토리에 plan.md 템플릿과 skills/ 폴더가 생성되었습니다.
> /edit plan
   [에디터 모드] 마크다운 에디터용 UI 팝업 화면이 열림.
   (사용자가 목표, 데이터소스, 지표 등을 채워 넣음. 저장 후 종료 시 기존 채팅 로그로 부드럽게 복귀)
> /build
   [파이프라인] plan.md 파싱 및 분석 실행...
   [오케스트레이터] profile → query → transform → visualize 
   (진행 상황이 터미널 블록으로 스크롤되며 출력됨)
   [대화형 리뷰] 차트 초안(HTML 등) 완성.
> "x축을 날짜로 바꿔주고, 색상은 파란색으로 칠해줘" 
   (기존 프롬프트 활용하여 자연어로 수정 지시)
> /export streamlit
   [완료] 결과물이 my_dashboard/ 디렉토리에 Streamlit 패키지로 빌드되었습니다.
```

## 3. 마크다운 전용 내장 에디터 (Textual 기반)
마크다운 문법에 익숙하지 않은 사용자나 터미널 안에서 쾌적한 작성을 원할 경우를 대비하여 **REPL과 부드럽게 통합되는 편집 모드**를 지원합니다.

* **팝업/모달 형태의 에디터 모드 (`/edit plan`)**:
  - `vi`나 `nano`로 튕겨 나가지 않고, `Textual`의 `TextArea` 위젯 등을 활용해 BI-Agent 내부에서 부드럽게 마크다운을 편집하는 오버레이 화면을 띄웁니다.
  - 마크다운 블록의 구문 강조(Syntax Highlighting)를 지원하여 가독성을 높입니다.
* 기존 UX를 해치지 않기 위해 에디터에서 `Esc` 또는 `Ctrl+C/Q`를 누르면 언제든지 기존 대화창 REPL 뷰(블록 렌더링 화면)로 안전하게 복귀할 수 있게 설계합니다.

## 4. 백엔드 아키텍처 재설계 (`backend/aac/`)
시스템 아키텍처는 CLI 스크립트 중심에서 **하위 라이브러리 형태**로 변경되어 `main.py`에서 손쉽게 임포트해서 씁니다.

### 4.1 `PlanParser` (`backend/aac/plan_parser.py`)
- `python-frontmatter` 라이브러리를 활용하여 YAML 헤더(목표, 지표 등)와 Markdown 본문(세부 컨텍스트 선언)을 완벽히 분리해 파싱합니다. 파싱 결과는 `AnalysisIntent` 객체로 넘깁니다.
- 파싱 실패 시 LLM에게 구조화를 보정받는 3단계 폴백(YAML -> 정규식 헤딩 -> LLM) 장치를 둡니다.

### 4.2 `SkillsRAGManager` (`backend/aac/skills_rag.py`)
- `skills/` 폴더 내의 사내 SQL 컨벤션, 태블로 규칙 등 마크다운 지식 베이스를 런타임에 읽어들입니다.
- 초기엔 정밀도를 위해 모호한 벡터 유사도보다 파일명+키워드 빈도를 바탕으로 한 **Deterministic Keyword-Weighted RAG**를 구현합니다 (환각 방지).

### 4.3 `AaCOrchestrator` (`backend/aac/aac_orchestrator.py`)
- 기존 LangGraph 기반의 `AgenticOrchestrator`를 "플랜 완수형 파이프라인"으로 랩핑합니다.
- 파이프라인(Profile → Query → Transform → Visualize → Insight)을 따라 실행하되, `AgenticOrchestrator`가 스스로 무한 재계획(Re-planning Loop)에 빠지지 않도록 `ToolRegistry`를 **명령 이행 모드**(`step_executor`)로 다이렉트 호출합니다.

## 5. 단계별 개발 계획 및 우선순위 (총 5~6일)

| Phase       | 태스크 내용                                                                                                                                  | 비고        |
| ----------- | -------------------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| **Phase 0** | 기반 작업: `pyproject.toml` 라이브러리 추가(`python-frontmatter` 등), `backend/aac` 빈 디렉토리 생성                                         | -           |
| **Phase 1** | **`PlanParser` 로직 구현**: 마크다운 템플릿 처리. YAML과 본문 분리 파싱. 예외처리 폴백 등                                                    | 코어 모듈   |
| **Phase 2** | **명령어 및 내장 에디터 편입 (`main.py`)**: `/init`, `/build`, `/edit plan` 명령어 구현 및 팝업 모달 형태의 쾌적한 마크다운 에디터 UI 연동   | TUI/UX 통합 |
| **Phase 3** | **AaC 코어 엔진 파이프라인 연결**: `AaCOrchestrator` 설계. Plan 파싱 결과 기반으로 기존 Agentic 도구들(query, schema 등) 순차 실행 흐름 제어 | 백엔드 통합 |
| **Phase 4** | **`SkillsRAG` 구현**: 에이전트에 스킬 폴더 텍스트를 주입                                                                                     | 고도화 기능 |
| **Phase 5** | 통합 테스트 및 샘플 템플릿 파일(basic, advanced) 준비                                                                                        | QA          |

## 6. 잠재적 위험 및 완화 방안 (Risk & Mitigation)
- **에디터와 콘솔 출력의 충돌**: `Textual` 위젯(마크다운 내장 에디터)과 `Prompt Toolkit`(CLI 텍스트, 하단바)의 화면 렌더링 싸움이 일어날 수 있음. `/edit` 명령 시에는 `PromptSession`의 입력을 일시 중지(Suspend)하거나, 비동기 루프를 일시적으로 TUI 앱에 넘기는 방식으로 매끄럽게 핸들링합니다.
- **컨텍스트 로실**: REPL 대화 도중 세션 상태 증발을 막기 위해 실행 스텝마다 `AaCSessionManager`를 통해 JSON 파일로 상태 스냅샷을 단위 단위로 디스크에 직렬화 저장합니다.
