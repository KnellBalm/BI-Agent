# UI Plan B: Inline Block (Warp Terminal Style)

> BI-Agent UI Redesign Proposal - prompt_toolkit + rich 기반 터미널 스크롤 방식

**작성일:** 2026-02-20
**버전:** v0.1.0-draft
**대상 프로젝트:** BI-Agent (`/Users/zokr/python_workspace/BI-Agent`)

---

## 1. 개요 및 컨셉

### 1.1 핵심 아이디어

Textual 풀스크린 TUI를 **완전히 제거**하고, **prompt_toolkit + rich** 조합으로 순수 터미널 스크롤 기반의 CLI를 구축한다.
Warp 터미널의 "Inline Block" 컨셉을 차용하여 각 질문-응답 쌍을 **독립적인 블록**으로 묶고, 블록 단위로 접기/펼치기와 키보드 탐색을 지원한다.

기존 `backend/main.py`의 REPL 구조를 확장하는 방식으로, 터미널의 기본 스크롤을 그대로 활용한다.

### 1.2 디자인 원칙

| 원칙 | 설명 |
|------|------|
| **터미널 네이티브** | 풀스크린 없음. 터미널의 기본 스크롤 동작을 그대로 활용 |
| **블록 기반 구조** | 각 질문-응답이 하나의 시각적 블록(bordered box)으로 묶임 |
| **접기/펼치기** | 블록 내 SQL, 데이터, 상세 분석을 선택적으로 접기/펼치기 |
| **키보드 탐색** | Ctrl+Up/Down으로 블록 간 점프, 블록 내 섹션 토글 |
| **최소 의존성** | prompt_toolkit + rich만 사용. Textual 의존성 제거 |

### 1.3 참고 인터페이스

- **Warp Terminal**: 명령어+결과를 블록으로 묶는 UX
- **Claude CLI (Anthropic)**: 배너 -> 프롬프트 -> 결과 스크롤
- **GitHub CLI (`gh`)**: rich 터미널 출력 + 인터랙티브 프롬프트
- **ipython/jupyter console**: 셀 기반 인터랙션


---

## 2. 유저 저니 (User Journey)

### 시나리오 1: 첫 실행

```
$ bi-agent-cli

    ____  ____     ___                    __
   / __ )/  _/    /   | ____ ____  ____  / /_
  / __  |/ /_____/ /| |/ __ `/ _ \/ __ \/ __/
 / /_/ // /_____/ ___ / /_/ /  __/ / / / /_
/_____/___/    /_/  |_\__, /\___/_/ /_/\__/
                     /____/

  v0.1.0  *  DB: my_postgres (PostgreSQL)  *  /help

 > _
```

사용자는 일반 터미널에서 `bi-agent-cli`를 실행한다.
ASCII 배너가 출력되고, 연결 상태가 표시된 후 프롬프트가 나타난다.

### 시나리오 2: 데이터 분석 질문

```
 > 월별 매출 트렌드를 분석해줘

 ┌─ [1] 월별 매출 트렌드를 분석해줘 ─────────────── 12:34:56 ─┐
 │                                                              │
 │  Thinking...                                                 │
 │  [*] 테이블 스캔: orders (1 table)                           │
 │  [*] SQL 생성 완료                                            │
 │  [*] 쿼리 실행 완료 (0.23s)                                   │
 │  [*] 분석 완료                                                │
 │                                                              │
 │  [SQL] (접힘 - Tab으로 펼치기) ............................. │
 │                                                              │
 │  | month    | total_sales  |                                 │
 │  |----------|--------------|                                 │
 │  | 2025-01  | 12,340,000   |                                 │
 │  | 2025-02  | 15,670,000   |                                 │
 │  | 2025-03  | 11,890,000   |                                 │
 │                                                              │
 │  ## 분석 인사이트                                              │
 │  2월에 매출이 **26.9% 증가**했으며, 3월에는 소폭 감소했습니다. │
 │  주요 원인은 프로모션 이벤트(2월 1-14일)로 추정됩니다.         │
 │                                                              │
 └──────────────────────────────────────────────────────────────┘

 > _
```

1. 사용자가 질문을 입력하면 프롬프트 아래에 블록이 생성된다.
2. `Thinking...` 단계가 실시간으로 업데이트된다 (`rich.live.Live` 사용).
3. 완료되면 블록 내에 SQL(접힌 상태), 데이터 테이블, 인사이트가 표시된다.
4. 블록이 닫히고 다음 프롬프트가 나타난다.

### 시나리오 3: 블록 탐색 및 접기/펼치기

```
 > /blocks

 최근 블록 목록:
   [1] 월별 매출 트렌드를 분석해줘          12:34:56
   [2] 가장 많이 팔린 상품 TOP 5는?         12:35:42
   [3] 지역별 매출을 비교해줘               12:36:15

 > /block 1 --expand sql

 ┌─ [1] 월별 매출 트렌드를 분석해줘 ─────────────── 12:34:56 ─┐
 │                                                              │
 │  [SQL] (펼침)                                                │
 │  ┌────────────────────────────────────────────────────────┐  │
 │  │ SELECT DATE_TRUNC('month', order_date) AS month,       │  │
 │  │        SUM(amount) AS total_sales                      │  │
 │  │ FROM orders                                            │  │
 │  │ GROUP BY 1                                             │  │
 │  │ ORDER BY 1;                                            │  │
 │  └────────────────────────────────────────────────────────┘  │
 │                                                              │
 │  | month    | total_sales  |                                 │
 │  ...                                                         │
 └──────────────────────────────────────────────────────────────┘
```

### 시나리오 4: 자동완성 및 히스토리

```
 > /con[Tab]
 > /connect           <- Tab 자동완성

 > [Up Arrow]
 > 지역별 매출을 비교해줘    <- 이전 입력 복원

 > 월별[자동 제안: "월별 매출 트렌드를 분석해줘" dim 표시]
 > 월별 매출 트렌드를 분석해줘    <- Right Arrow로 수락
```

### 시나리오 5: 블록 내 인터랙티브 모드

```
 ┌─ [2] 가장 많이 팔린 상품 TOP 5는? ──────────── 12:35:42 ─┐
 │                                                              │
 │  | rank | product_name  | total_qty |                        │
 │  |------|---------------|-----------|                        │
 │  | 1    | Widget Pro    | 15,234    |                        │
 │  | 2    | Gadget Plus   | 12,891    |                        │
 │  | ... 3 more rows (Enter로 더보기) |                        │
 │                                                              │
 │  [E]xport CSV  [C]opy SQL  [F]ollow-up question              │
 └──────────────────────────────────────────────────────────────┘
```

블록 하단에 액션 바를 표시하여 결과에 대한 후속 작업을 지원한다.


---

## 3. UI 레이아웃 ASCII 목업

### 3.1 기본 플로우 (터미널 스크롤)

```
┌─ Terminal ──────────────────────────────────────────────────────┐
│                                                                 │
│     ____  ____     ___                    __                    │
│    / __ )/  _/    /   | ____ ____  ____  / /_                   │
│   / __  |/ /_____/ /| |/ __ `/ _ \/ __ \/ __/                  │
│  / /_/ // /_____/ ___ / /_/ /  __/ / / / /_                    │
│ /_____/___/    /_/  |_\__, /\___/_/ /_/\__/                    │
│                      /____/                                     │
│                                                                 │
│  v0.1.0  *  DB: my_postgres (PostgreSQL)  *  /help             │
│                                                                 │
│ > 월별 매출 트렌드를 분석해줘                                     │
│                                                                 │
│ ┌─ [1] ──────────────────────────────────────── 12:34:56 ──┐   │
│ │  [SQL] ............  [Data] 3 rows  [Insight] 2 lines    │   │
│ │                                                           │   │
│ │  2월에 매출이 26.9% 증가했으며...                           │   │
│ └───────────────────────────────────────────────────────────┘   │
│                                                                 │
│ > 가장 많이 팔린 상품 TOP 5는?                                   │
│                                                                 │
│ ┌─ [2] ──────────────────────────────────────── 12:35:42 ──┐   │
│ │  [SQL] ............  [Data] 5 rows  [Insight] 3 lines    │   │
│ │                                                           │   │
│ │  | rank | product_name  | total_qty |                     │   │
│ │  |------|---------------|-----------|                     │   │
│ │  | 1    | Widget Pro    | 15,234    |                     │   │
│ │  | 2    | Gadget Plus   | 12,891    |                     │   │
│ │  | ...                              |                     │   │
│ │                                                           │   │
│ │  Widget Pro가 전체 판매량의 23.1%를 차지...                  │   │
│ └───────────────────────────────────────────────────────────┘   │
│                                                                 │
│ > _                                                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Thinking 상태 (Live 업데이트)

```
│ > 지역별 매출을 비교해줘                                         │
│                                                                 │
│ ┌─ [3] ──────────────────────────────────────────────────┐     │
│ │  * 테이블 스캔: orders, regions                         │     │
│ │  * SQL 생성 완료                                        │     │
│ │  * 쿼리 실행 중...  /                                   │     │
│ └─────────────────────────────────────────────────────────┘     │
```

`rich.live.Live`와 `rich.spinner.Spinner`를 사용하여 블록 내에서 실시간 업데이트.
완료 시 `Live`가 종료되고 최종 결과 블록이 print된다.

### 3.3 블록 접힌 상태 (Compact View)

```
│ ┌─ [1] 월별 매출 트렌드를 분석해줘 ──── 12:34:56 ──┐          │
│ │  SQL | 3 rows | 2월에 매출이 26.9% 증가...        │          │
│ └────────────────────────────────────────────────────┘          │
│                                                                 │
│ ┌─ [2] 가장 많이 팔린 상품 TOP 5는? ──── 12:35:42 ──┐         │
│ │  SQL | 5 rows | Widget Pro가 전체 판매량의 23.1%.. │         │
│ └────────────────────────────────────────────────────┘          │
```

`/compact` 명령어로 모든 블록을 1-2줄 요약으로 접음. `/expand N`으로 특정 블록 펼침.

### 3.4 CommandPalette (prompt_toolkit 네이티브)

```
│ > /ex                                                           │
│   /exit        종료                                              │
│   /export      결과 내보내기 (CSV/Excel/PDF)                     │
│   /explore     스키마 탐색                                       │
```

prompt_toolkit의 `Completer`를 사용하여 입력 바로 아래에 자동완성 후보를 표시.


---

## 4. 구현 계획 (단계별)

### Phase 1: 블록 렌더링 엔진

**목표:** 질문-응답 쌍을 rich Panel 블록으로 렌더링하는 핵심 엔진 구축.

**작업 내용:**

1. `BlockRenderer` 클래스 개발
   - 입력: 질문 텍스트, SQL 문자열, 데이터 (pandas DataFrame), 인사이트 텍스트
   - 출력: `rich.panel.Panel`로 감싼 복합 렌더러블
   - 내부 구성:
     - 헤더: 블록 번호, 질문 요약, 타임스탬프
     - SQL 섹션: `rich.syntax.Syntax` (접힘/펼침 상태 관리)
     - 데이터 섹션: `rich.table.Table` (행 수 제한 + 더보기)
     - 인사이트 섹션: `rich.markdown.Markdown`
     - 액션 바: 키보드 힌트 (Export, Copy, Follow-up)

2. `BlockStore` 클래스 개발
   - 블록 히스토리를 메모리에 저장
   - 블록 ID로 접근, 접힘/펼침 상태 관리
   - 직렬화/역직렬화 (세션 간 블록 히스토리 유지)

3. 접기/펼치기 상태 관리
   - 각 블록은 `expanded_sections: Set[str]` 보유 (sql, data, insight, thinking)
   - 기본 상태: sql=접힘, data=펼침(5행까지), insight=펼침, thinking=접힘

**완료 기준:**
- `BlockRenderer`가 rich Panel을 정상 출력
- SQL 접기/펼치기 상태가 `/block N --expand sql` 명령으로 전환
- 블록이 `BlockStore`에 저장/조회 가능

### Phase 2: REPL 루프 확장

**목표:** 기존 `backend/main.py`의 REPL 루프를 블록 시스템과 통합.

**작업 내용:**

1. `main.py` REPL 루프 리팩토링
   - 기존 `print_response()` -> `BlockRenderer.render()` + `console.print()` 교체
   - Thinking 단계를 `rich.live.Live` 컨텍스트 내에서 실시간 업데이트
   - 쿼리 결과를 파싱하여 SQL, DataFrame, Insight로 분리

2. 블록 명령어 추가
   - `/blocks` : 최근 블록 목록 표시
   - `/block N` : N번 블록 전체 펼침
   - `/block N --expand sql` : 특정 섹션 펼침
   - `/compact` : 모든 블록 접힘 (재출력)
   - `/export N csv` : N번 블록 데이터를 CSV로 내보내기

3. AgenticOrchestrator 결과 파싱
   - `orchestrator.run()` 결과를 구조화된 형태로 수신
   - SQL, DataFrame, final_answer 등을 별도 필드로 추출
   - 파싱 실패 시 폴백: 전체 텍스트를 인사이트로 표시

**완료 기준:**
- 질문 입력 시 블록이 생성되어 터미널에 출력
- `/blocks`, `/block N` 명령어 동작
- Thinking 애니메이션이 블록 내에서 실시간 표시

### Phase 3: prompt_toolkit 고급 기능

**목표:** 입력 경험을 CLI 수준으로 끌어올림.

**작업 내용:**

1. 커스텀 `Completer` 구현
   - 슬래시 명령어 자동완성: `/` 입력 시 명령어 목록 표시
   - 테이블명/컬럼명 자동완성: 연결된 DB의 스키마 정보 활용
   - fuzzy matching 지원 (`FuzzyCompleter` 래핑)

2. 멀티라인 입력 지원
   - `\` (백슬래시)로 줄 바꿈 -> 멀티라인 질문 입력 가능
   - 또는 `"""` 트리플 쿼트로 멀티라인 블록 시작/종료

3. 프롬프트 커스터마이징
   - 연결 상태에 따른 프롬프트 색상 변경
   - 접속된 DB명 표시: `my_postgres > `
   - vi/emacs 키맵 선택 지원

4. 히스토리 검색 강화
   - `Ctrl+R` 역방향 검색 (prompt_toolkit 빌트인)
   - `FileHistory` 유지 (기존 `~/.bi-agent/repl_history`)

**완료 기준:**
- `/` 입력 시 명령어 자동완성 드롭다운 표시
- 테이블명 자동완성 동작
- `Ctrl+R` 히스토리 검색 동작
- 멀티라인 입력 동작

### Phase 4: 블록 탐색 인터랙션

**목표:** 키보드로 블록 간 이동 및 블록 내 인터랙션 지원.

**작업 내용:**

1. 블록 점프 (Block Navigation)
   - 구현 방식: `/block N` 명령어로 블록을 재출력
   - 또는: ANSI escape 시퀀스로 터미널 스크롤 위치 이동 (터미널 호환성 주의)
   - 현실적 접근: 블록을 재출력하는 방식이 안정적

2. 블록 내 액션
   - 블록 출력 후 인터랙티브 프롬프트: `[E]xport [C]opy [F]ollow-up [Enter] continue`
   - `E` -> CSV/Excel 내보내기 (기존 `dashboard_generator.py` 활용)
   - `C` -> SQL을 클립보드에 복사 (pyperclip)
   - `F` -> 후속 질문 모드 (이전 컨텍스트 유지)
   - `Enter` -> 다음 프롬프트로 이동

3. 블록 북마크
   - `/bookmark N` -> 블록을 즐겨찾기에 추가
   - `/bookmarks` -> 북마크 목록 표시
   - 세션 간 유지 (`~/.bi-agent/bookmarks.json`)

**완료 기준:**
- 블록 출력 후 액션 바에서 E/C/F 키 동작
- CSV 내보내기 파일 생성 확인
- 북마크 저장/조회 동작

### Phase 5: 통합 및 폴리싱

**목표:** 전체 플로우 검증, 에지 케이스 처리, 엔트리포인트 정리.

**작업 내용:**

1. 엔트리포인트 통합
   - `pyproject.toml`의 `bi-agent-cli` 엔트리포인트를 새 REPL로 교체
   - 기존 `bi-agent` (Textual TUI)는 그대로 유지 (Plan A 또는 레거시)
   - `bi-agent-cli --compact` 옵션: 블록 기본 접힘 모드

2. 에러 핸들링
   - DB 연결 끊김 시 블록 내 에러 표시 (빨간 테두리)
   - LLM 타임아웃 시 재시도 옵션 제공
   - 잘못된 SQL 생성 시 자동 수정 시도 (query_healer 연동)

3. 테마 시스템
   - 다크/라이트 테마 전환: `/theme dark`, `/theme light`
   - rich의 `Theme` 클래스로 색상 팔레트 관리
   - 환경변수 `BI_AGENT_THEME=dark` 지원

4. 성능 최적화
   - 블록 재출력 시 필요한 블록만 렌더링
   - 대형 DataFrame은 청크 단위로 스트리밍 표시
   - 히스토리 파일 크기 제한 (최근 1000개)

**완료 기준:**
- `bi-agent-cli` 명령어로 새 REPL 실행 가능
- 에러 시나리오에서 크래시 없음
- 다크/라이트 테마 전환 동작


---

## 5. 기술 스택 선택 이유

### 5.1 prompt_toolkit 선택 이유

| 근거 | 설명 |
|------|------|
| **네이티브 터미널** | 풀스크린 TUI와 달리 터미널의 기본 스크롤을 활용. 사용자가 `less`, `grep` 등 터미널 도구와 자연스럽게 연계 가능. |
| **기존 코드 베이스** | `backend/main.py`에 이미 prompt_toolkit 기반 REPL이 구현됨. `PromptSession`, `FileHistory`, `AutoSuggestFromHistory` 재사용. |
| **자동완성 생태계** | `Completer`, `FuzzyCompleter`, `WordCompleter`, `NestedCompleter` 등 풍부한 자동완성 시스템 제공. |
| **비동기 지원** | `prompt_async()`로 asyncio 이벤트 루프와 자연스럽게 통합. `AgenticOrchestrator`의 `await run()` 호출과 호환. |
| **이벤트 루프 단순** | Textual과 달리 자체 위젯 시스템이 없어 이벤트 루프가 단순. prompt -> process -> print 사이클만 관리. |

### 5.2 rich 선택 이유

| 근거 | 설명 |
|------|------|
| **이미 사용 중** | 프로젝트 전반에서 `rich.console.Console`, `Panel`, `Table`, `Markdown`, `Syntax` 등 광범위하게 사용됨. |
| **Live 렌더링** | `rich.live.Live`로 Thinking 단계를 블록 내에서 실시간 업데이트. `transient=True`로 완료 후 최종 결과로 교체. |
| **복합 렌더러블** | `Panel` 안에 `Table`, `Syntax`, `Markdown`, `Text`를 `Group`으로 합성하여 하나의 블록으로 출력 가능. |
| **prompt_toolkit 호환** | rich는 prompt_toolkit과 같은 프로세스에서 문제 없이 동작. 출력은 rich, 입력은 prompt_toolkit으로 역할 분리가 자연스러움. |

### 5.3 Textual을 쓰지 않는 이유

| 이유 | 설명 |
|------|------|
| **풀스크린 강제** | Textual은 터미널 전체를 점유하는 풀스크린 TUI. "CLI 느낌"과 본질적으로 충돌. |
| **스크롤 모델 차이** | Textual의 스크롤은 위젯 내부 가상 스크롤. 터미널 네이티브 스크롤(scrollback buffer)과 다름. |
| **복잡도** | 단순한 "질문 -> 응답 출력" 패턴에 Textual의 위젯/메시지/TCSS 시스템은 과도한 추상화. |
| **터미널 도구 연계** | 풀스크린 TUI에서는 `|` (파이프), `>` (리다이렉트), `tmux copy-mode` 등 터미널 도구 사용이 어려움. |


---

## 6. 장단점 비교

### 6.1 장점

| 장점 | 설명 |
|------|------|
| **진짜 CLI 느낌** | 터미널 네이티브 스크롤, 파이프라인 연계(`bi-agent-cli | grep "매출"`), 리다이렉트 가능. |
| **낮은 복잡도** | 위젯 시스템 없음. Python 함수 호출로 블록 출력. 디버깅과 유지보수가 단순. |
| **빠른 시작** | Textual 앱 초기화 없이 즉시 프롬프트 표시. 체감 시작 속도가 빠름. |
| **터미널 도구 호환** | `tmux`, `screen`, `less`, `grep` 등과 완전 호환. 출력을 파일로 리다이렉트 가능. |
| **경량** | Textual 의존성 제거 시 패키지 크기 감소. 설치가 간단해짐. |
| **접근성** | 풀스크린 TUI에 익숙하지 않은 사용자도 CLI는 직관적으로 사용 가능. |

### 6.2 단점

| 단점 | 설명 |
|------|------|
| **기존 위젯 재사용 불가** | `MessageBubble`, `ThinkingPanel`, `HUDStatusLine` 등 Textual 위젯을 모두 새로 구현해야 함 (rich 기반으로). |
| **모달/오버레이 없음** | 연결 설정, 스키마 탐색 등 복잡한 플로우를 모달 Screen으로 처리할 수 없음. 인라인 인터랙티브 프롬프트로 대체해야 함. |
| **레이아웃 제한** | 사이드바, 분할 패널 등 복잡한 레이아웃 불가. 정보 밀도가 낮을 수 있음. |
| **블록 재출력** | 접기/펼치기 시 블록을 다시 print해야 함. 터미널 scrollback이 오염될 수 있음. |
| **DataTable 인터랙션** | rich Table은 정적 출력. 정렬, 필터링 등 인터랙티브 테이블 기능은 별도 구현 필요. |
| **상태 표시 제한** | 풀스크린 TUI의 상시 HUD/사이드바와 달리, 상태 정보를 프롬프트나 명령어로만 확인 가능. |


---

## 7. 파일 구조 변경 예상

```
backend/
  main.py                     # 대폭 확장: 블록 REPL 메인 루프
  cli/                        # 신규 디렉토리
    __init__.py
    block_renderer.py         # 신규: 블록 렌더링 엔진
    block_store.py            # 신규: 블록 히스토리 저장소
    completers.py             # 신규: 커스텀 자동완성 (명령어, 테이블명)
    commands.py               # 신규: 슬래시 명령어 핸들러
    themes.py                 # 신규: 다크/라이트 테마 정의
    actions.py                # 신규: 블록 액션 (export, copy, follow-up)
  orchestrator/
    bi_agent_console.py       # 기존 유지 (Plan A 또는 레거시 TUI)
    ui/                       # 기존 유지 (Textual 위젯들)
    ...
```

### 신규 파일 상세

| 파일 | 역할 | 예상 규모 |
|------|------|-----------|
| `cli/block_renderer.py` | rich Panel 기반 블록 렌더링. SQL/Data/Insight 섹션 합성 | 200-300줄 |
| `cli/block_store.py` | 블록 저장, 조회, 상태 관리, JSON 직렬화 | 100-150줄 |
| `cli/completers.py` | 명령어/테이블/컬럼 자동완성 | 100-150줄 |
| `cli/commands.py` | `/blocks`, `/block N`, `/export`, `/compact` 등 | 150-200줄 |
| `cli/themes.py` | 다크/라이트 테마 색상 팔레트 | 50-80줄 |
| `cli/actions.py` | CSV 내보내기, 클립보드 복사, 후속 질문 | 100-150줄 |


---

## 8. 마이그레이션 전략

### 8.1 병행 운영

1. **기존 엔트리포인트 유지**
   - `bi-agent` -> Textual TUI (기존 `bi_agent_console.py`)
   - `bi-agent-cli` -> 새 Inline Block REPL (확장된 `main.py`)

2. **점진적 기능 이관**
   - Phase 1-2: 기본 질문-응답만 블록으로
   - Phase 3: 자동완성, 히스토리
   - Phase 4: 블록 탐색, 액션
   - Phase 5: 연결 관리 등 고급 기능도 CLI 명령어로 지원

3. **공유 백엔드**
   - `AgenticOrchestrator`, `ConnectionManager` 등 백엔드 로직은 양쪽에서 공유
   - UI 레이어만 다름: Textual 위젯 vs rich print

### 8.2 Textual TUI 제거 시점

- Plan B가 충분히 안정화되고 모든 기능이 이관된 후
- 사용자 피드백을 수집하여 결정
- `textual` 의존성 제거 시 `pyproject.toml` 업데이트 필요


---

## 9. 핵심 구현 패턴

### 9.1 블록 렌더링 패턴 (의사 코드)

```python
# block_renderer.py 핵심 구조

from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.console import Group
from rich.text import Text

class BlockRenderer:
    def render(self, block: Block) -> Panel:
        sections = []

        # SQL 섹션
        if block.sql:
            if "sql" in block.expanded:
                sections.append(Syntax(block.sql, "sql", theme="monokai"))
            else:
                sections.append(Text("[SQL] (Tab으로 펼치기)", style="dim"))

        # Data 섹션
        if block.dataframe is not None:
            table = self._build_table(block.dataframe, max_rows=5)
            sections.append(table)

        # Insight 섹션
        if block.insight:
            sections.append(Markdown(block.insight))

        header = f"[{block.id}] {block.question[:50]}"
        return Panel(
            Group(*sections),
            title=header,
            subtitle=block.timestamp,
            border_style="cyan",
        )
```

### 9.2 Live Thinking 패턴 (의사 코드)

```python
# main.py REPL 루프 내

from rich.live import Live
from rich.spinner import Spinner

with Live(console=console, transient=True) as live:
    steps = []
    for step_name, step_result in orchestrator.run_steps(query):
        steps.append(f"[*] {step_name}")
        panel = Panel(
            "\n".join(steps) + f"\n[ ] {step_name}...  ",
            title=f"[{block_id}] Thinking",
            border_style="yellow",
        )
        live.update(panel)

# Live 종료 후 최종 블록 출력
console.print(block_renderer.render(result_block))
```


---

## 10. 리스크 및 완화 방안

| 리스크 | 확률 | 영향 | 완화 방안 |
|--------|------|------|-----------|
| 블록 재출력 시 터미널 scrollback 오염 | 중 | 중 | 접기/펼치기는 `/block N` 명령어로 처리 (새로 print). 또는 ANSI 커서 이동 사용. |
| 모달 플로우 구현 복잡도 | 중 | 높 | 연결 설정 등은 인터랙티브 프롬프트 체인으로 구현. `questionary` 라이브러리 도입 검토. |
| 대형 DataFrame 출력 시 스크롤 과다 | 낮 | 중 | 기본 5행 + "더보기" 패턴. `/block N --expand data` 시 전체 표시. |
| Textual 위젯 재구현 비용 | 높 | 중 | 최소 기능만 구현. `ThinkingPanel` -> `rich.live.Live`, `MessageBubble` -> `rich.panel.Panel`로 단순 매핑. |
| Windows 터미널 호환성 | 낮 | 낮 | rich와 prompt_toolkit 모두 Windows Terminal 지원. 레거시 cmd는 지원 범위 외. |


---

## 11. 예상 일정

| Phase | 작업 | 예상 소요 |
|-------|------|-----------|
| Phase 1 | 블록 렌더링 엔진 | 2-3일 |
| Phase 2 | REPL 루프 확장 | 2일 |
| Phase 3 | prompt_toolkit 고급 기능 | 2-3일 |
| Phase 4 | 블록 탐색 인터랙션 | 2일 |
| Phase 5 | 통합 및 폴리싱 | 2-3일 |
| **합계** | | **10-13일** |


---

## 부록: Plan A와의 비교 요약

| 항목 | Plan A (Split Pane) | Plan B (Inline Block) |
|------|--------------------|-----------------------|
| **프레임워크** | Textual (기존 유지) | prompt_toolkit + rich (신규) |
| **화면 모드** | 풀스크린 TUI | 터미널 스크롤 |
| **CLI 느낌** | 중간 (TUI 기반 모방) | 높음 (네이티브 터미널) |
| **기존 코드 재사용** | 높음 (위젯 재사용) | 낮음 (새로 구현) |
| **레이아웃 유연성** | 높음 (사이드바, 패널) | 낮음 (순차 출력) |
| **모달/오버레이** | 지원 (Textual Screen) | 미지원 (인라인 프롬프트) |
| **터미널 도구 호환** | 낮음 (풀스크린) | 높음 (파이프, 리다이렉트) |
| **구현 비용** | 중간 (레이아웃 변경) | 높음 (새 렌더링 시스템) |
| **유지보수** | Textual 프레임워크 의존 | 단순한 함수 호출 기반 |
| **예상 일정** | 9-11일 | 10-13일 |
| **추천 시나리오** | 기존 TUI 자산 활용 원할 때 | 진정한 CLI 경험을 원할 때 |
