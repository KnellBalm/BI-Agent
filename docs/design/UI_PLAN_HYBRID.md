# BI-Agent Hybrid CLI+TUI 구현 계획

> **전략**: `bi-agent-cli` (prompt_toolkit REPL)을 메인 껍데기로 삼고,
> 결과는 rich 블록으로 쌓으며, 복잡한 연결/탐색 흐름은 Textual 스크린을 재사용한다.

---

## 현재 코드베이스 스냅샷 (2026-02-20)

| 파일 | 상태 | 역할 |
|------|------|------|
| `backend/main.py` | ✅ 완성 (219줄) | prompt_toolkit REPL 껍데기 |
| `backend/orchestrator/bi_agent_console.py` | ✅ 유지 (456줄) | Textual TUI (복잡한 흐름용) |
| `backend/orchestrator/ui/components/` | ✅ 8개 컴포넌트 | 일부 재사용 |
| `backend/orchestrator/screens/` | ✅ 6개 스크린 | 모달 흐름 재사용 |
| `pyproject.toml` | ✅ 두 entry point | `bi-agent`, `bi-agent-cli` |

---

## 비전: 완성된 모습

```
$ bi-agent-cli

  ██████╗ ██╗      █████╗  ██████╗ ███████╗███╗   ██╗████████╗
  ...

  v2.3.2  ·  ● sample_sales.sqlite (sqlite)  ·  /help 로 도움말

 ─────────────────────────────────────────────────────────────────
  [#1] 2026-02-20 14:32  월별 매출 트렌드 분석
 ─────────────────────────────────────────────────────────────────
  ## 월별 매출 트렌드

  | 월   | 매출    | 전월 대비 |
  |------|---------|----------|
  | 1월  | 1,200만 | -        |
  | 2월  | 1,350만 | ▲ 12.5%  |

  💡 후속 질문: 카테고리별 차이는? / 이상치가 있는 월은?

 ─────────────────────────────────────────────────────────────────
  [#2] 2026-02-20 14:35  카테고리별 매출 비교
 ─────────────────────────────────────────────────────────────────
  ...

  [분석 중 ⠋]

 sample_sales.sqlite  ●  2개 대화  ·  Gemini 2.0 Flash
 > _
```

**핵심 특징:**
- 터미널 자연 스크롤 (풀스크린 앱 없음)
- 각 Q&A가 번호 붙은 블록으로 구분
- 하단 고정 상태바 (prompt_toolkit bottom toolbar)
- prompt_toolkit 입력 (히스토리, 자동완성)
- `/connect`, `/explore` 등 복잡한 명령은 Textual 팝업 실행 후 복귀

---

## 유저 저니 (User Journey)

### 시나리오 1: 첫 실행 — 데이터 분석

```
1. $ bi-agent-cli
   → 배너 출력, 연결 정보 표시

2. > 월별 매출을 분석해줘
   → [분석 중 ⠋] 스피너 (transient)
   → 블록 #1 출력: Markdown 테이블 + 후속 질문 제안

3. > 카테고리별로도 보여줘
   → 블록 #2 출력

4. > @1  (블록 #1 참조)
   → 블록 #1 내용 다시 출력 또는 요약 표시

5. > /quit
   → Bye!
```

### 시나리오 2: 데이터 소스 연결

```
1. > /connect
   → Textual 스크린 팝업 (ConnectionScreen 재사용)
   → 연결 설정 완료

2. Textual 종료 → REPL 복귀
   → 하단 상태바 업데이트: ● new_db.sqlite

3. > 방금 연결한 DB에서 테이블 목록 보여줘
   → 블록 #1 출력
```

### 시나리오 3: DB 탐색

```
1. > /explore
   → Textual DatabaseExplorerScreen 팝업
   → 테이블 구조, 샘플 데이터 탐색

2. ESC로 탐색 종료 → REPL 복귀
   → 탐색 결과가 블록으로 인라인 출력
```

### 시나리오 4: 히스토리 탐색

```
1. > /history
   → 지금까지의 블록 목록 출력
   ┌─ 대화 히스토리 ──────────────────────────┐
   │ #1  14:32  월별 매출 트렌드 분석          │
   │ #2  14:35  카테고리별 매출 비교           │
   │ #3  14:40  /explore — DB 탐색             │
   └───────────────────────────────────────────┘

2. > @2
   → 블록 #2 전체 재출력
```

---

## 아키텍처

```
bi-agent-cli (entry point)
│
└── backend/main.py (REPL 루프)
    ├── prompt_toolkit PromptSession     ← 입력 (히스토리, 자동완성)
    ├── prompt_toolkit bottom_toolbar    ← 상태바 (연결, 블록 수, 모델)
    ├── BlockRenderer                   ← rich Panel 블록 렌더링 [신규]
    ├── BlockStore                      ← 블록 메모리 저장소 [신규]
    ├── CommandRouter                   ← 슬래시 명령어 라우터 [신규]
    └── TuiLauncher                     ← Textual 서브프로세스 실행 [신규]
        └── bi_agent_console.py         ← 기존 Textual TUI (수정 없음)
            ├── DatabaseExplorerScreen  ← /explore 시 재사용
            └── ConnectionScreen        ← /connect 시 재사용
```

---

## 구현 계획

### Phase 0: 기반 정리 (현재 완료)
- [x] `prompt_toolkit` 의존성 추가 (`pyproject.toml`)
- [x] `bi-agent-cli` entry point 등록
- [x] 기본 REPL 루프 (`backend/main.py`)
- [x] `get_conn_info()`, `run_query()`, `print_banner()` 구현
- [x] `/help`, `/list`, `/clear`, `/quit` 슬래시 명령어

**예상 기간**: 완료

---

### Phase 1: 블록 시스템 (BlockStore + BlockRenderer)
**목표**: 각 Q&A가 번호 붙은 rich Panel 블록으로 출력

**신규 파일**: `backend/orchestrator/ui/block_renderer.py`

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from rich import box

@dataclass
class Block:
    index: int
    query: str
    response: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)

class BlockStore:
    def __init__(self):
        self._blocks: List[Block] = []

    def add(self, query: str, response: str, metadata: dict = None) -> Block:
        block = Block(
            index=len(self._blocks) + 1,
            query=query,
            response=response,
            metadata=metadata or {}
        )
        self._blocks.append(block)
        return block

    def get(self, index: int) -> Optional[Block]:
        if 1 <= index <= len(self._blocks):
            return self._blocks[index - 1]
        return None

    def all(self) -> List[Block]:
        return list(self._blocks)

class BlockRenderer:
    def __init__(self, console: Console):
        self.console = console

    def render(self, block: Block):
        ts = block.timestamp.strftime("%H:%M")
        title = f"[dim]#{block.index}[/dim]  [dim]{ts}[/dim]  {block.query[:60]}"
        try:
            content = Markdown(block.response)
        except Exception:
            content = Text(block.response)
        self.console.print(
            Panel(content, title=title, title_align="left",
                  border_style="dim", box=box.SIMPLE_HEAD, padding=(0, 1))
        )

    def render_history_list(self, blocks: List[Block]):
        from rich.table import Table
        t = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
        t.add_column("No", style="cyan dim", width=4)
        t.add_column("시간", style="dim", width=6)
        t.add_column("질문")
        for b in blocks:
            t.add_row(f"#{b.index}", b.timestamp.strftime("%H:%M"), b.query[:60])
        self.console.print(t)
```

**`backend/main.py` 수정 사항**:
- `BlockStore`, `BlockRenderer` import 및 초기화
- `print_response()` → `block_store.add()` + `block_renderer.render()` 로 교체
- `@N` 참조 명령어 처리 추가
- `/history` 명령어 추가

**예상 기간**: 1~2일

---

### Phase 2: 하단 상태바 (Bottom Toolbar)

**목표**: prompt_toolkit의 `bottom_toolbar` 로 연결 상태, 블록 수, 모델명 고정 표시

**`backend/main.py` 수정 사항**:

```python
def get_toolbar(store: BlockStore, conn_display: str) -> str:
    count = len(store.all())
    return (
        f" ● {conn_display}  "
        f"│  {count}개 대화  "
        f"│  Gemini 2.0 Flash  "
        f"│  /help"
    )

# PromptSession 생성 시:
session = PromptSession(
    history=FileHistory(HISTORY_FILE),
    auto_suggest=AutoSuggestFromHistory(),
    style=PROMPT_STYLE,
    bottom_toolbar=lambda: get_toolbar(store, conn_display),
)
```

**예상 기간**: 반나절

---

### Phase 3: 슬래시 명령어 라우터 정리

**목표**: 명령어 처리 로직을 별도 모듈로 분리, 자동완성 등록

**신규 파일**: `backend/orchestrator/cli/command_router.py`

```python
COMMANDS = {
    "/help":    "도움말 표시",
    "/list":    "연결 목록",
    "/connect": "데이터 소스 연결 (TUI 팝업)",
    "/explore": "DB 탐색기 (TUI 팝업)",
    "/history": "대화 히스토리",
    "/clear":   "화면 초기화",
    "/quit":    "종료",
}
```

**`backend/main.py` 수정 사항**:
- `prompt_toolkit.completion.WordCompleter` 로 슬래시 명령어 자동완성 등록

**예상 기간**: 반나절

---

### Phase 4: Textual 팝업 연동 (TuiLauncher)

**목표**: `/connect`, `/explore` 호출 시 Textual 앱을 서브프로세스로 실행 후 REPL 복귀

**구현 방법**: 두 가지 옵션

**옵션 A (권장)**: `subprocess` 로 `bi-agent --screen connect` 실행

```python
import subprocess

async def launch_connect():
    """Textual ConnectionScreen을 서브프로세스로 실행."""
    proc = await asyncio.create_subprocess_exec(
        "bi-agent", "--screen", "connect",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await proc.communicate()
    # 완료 후 연결 정보 새로고침
```

**옵션 B**: `bi_agent_console.py` 에 `--screen` 인자 지원 추가

```python
# bi_agent_console.py 에 추가
import sys
if "--screen" in sys.argv:
    screen_name = sys.argv[sys.argv.index("--screen") + 1]
    app = BI_AgentConsole(initial_screen=screen_name)
else:
    app = BI_AgentConsole()
app.run()
```

**예상 기간**: 1~2일

---

### Phase 5: 후속 질문 제안 인라인 표시

**목표**: `ProactiveQuestionGenerator` 결과를 블록 하단에 인라인 출력

**`backend/main.py` 수정 사항**:
- `run_query()` 응답에서 후속 질문 추출
- 블록 렌더링 후 `💡 다음 질문 제안:` 섹션 출력

**예상 기간**: 반나절

---

## 파일별 변경 범위 요약

| 파일 | 변경 | 내용 |
|------|------|------|
| `backend/main.py` | 수정 | BlockStore/Renderer 연동, 상태바, @N 명령어 |
| `backend/orchestrator/ui/block_renderer.py` | **신규** | BlockStore, BlockRenderer 클래스 |
| `backend/orchestrator/cli/command_router.py` | **신규** | 명령어 라우터, 자동완성 사전 |
| `backend/orchestrator/bi_agent_console.py` | 선택적 수정 | `--screen` 인자 지원 (Phase 4) |
| `pyproject.toml` | 완료 | prompt_toolkit, bi-agent-cli 등록 |

**건드리지 않는 파일** (재사용만):
- `backend/orchestrator/screens/` 6개 스크린 — 변경 없음
- `backend/orchestrator/ui/components/` 8개 컴포넌트 — 변경 없음
- `backend/agents/` 모든 에이전트 — 변경 없음

---

## 단계별 우선순위

| Phase | 난이도 | 기간 | 사용자 체감 효과 |
|-------|--------|------|-----------------|
| Phase 1: 블록 시스템 | ⭐⭐ | 1~2일 | ⭐⭐⭐⭐ 가장 큰 차별점 |
| Phase 2: 상태바 | ⭐ | 반나절 | ⭐⭐⭐ 정보 표시 |
| Phase 3: 명령어 자동완성 | ⭐ | 반나절 | ⭐⭐ UX 개선 |
| Phase 4: TUI 팝업 | ⭐⭐⭐ | 1~2일 | ⭐⭐⭐ 복잡한 흐름 |
| Phase 5: 후속 질문 | ⭐ | 반나절 | ⭐⭐ AI 경험 강화 |

**권장 순서**: Phase 1 → 2 → 3 → 5 → 4 (TUI 팝업은 마지막)

**총 예상 기간**: 4~6일

---

## Architect 핵심 권고사항 반영

1. ✅ **`asyncio.get_running_loop()` 사용** — 이미 반영됨 (`metadata_scanner.py`)
2. ✅ **BlockStore 패턴** — Phase 1에서 구현
3. ✅ **`bi-agent-cli` 경량 REPL 유지** — 기본 entry point로
4. ✅ **기존 6개 모달 스크린 재사용** — Phase 4에서 서브프로세스로 연동
5. ⚠️ **`VerticalScroll` 100+ 위젯 성능** — REPL 방식이므로 해당 없음 (터미널 자연 스크롤)

---

## 장단점

| 항목 | 평가 |
|------|------|
| 기존 코드 재사용 | 백엔드 100%, UI 컴포넌트 선택적 |
| CLI 느낌 | ✅ 진정한 터미널 스크롤 방식 |
| 히스토리 가시성 | ✅ 번호 블록으로 스크롤 업해서 확인 가능 |
| 복잡한 흐름 (연결 등) | ✅ Textual 서브프로세스로 처리 |
| 테스트 | ⚠️ Textual pilot 사용 불가, 하지만 유닛 테스트 가능 |
| 리스크 | 낮음 — 점진적 추가, 기존 TUI 유지 |

---

Copyright © 2026 BI-Agent Team. All rights reserved.
