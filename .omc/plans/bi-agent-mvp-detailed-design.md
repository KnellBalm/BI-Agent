# BI-Agent MVP Detailed Design Plan

**Plan ID:** `bi-agent-mvp-detailed-design`
**Created:** 2026-02-02
**Status:** READY FOR EXECUTION
**Based On:** PLAN.md, DETAILED_SPEC.md, PHASE2/3 Completion Reports

---

## 1. Executive Summary

### MVP Goal
**사용자가 TUI에 접속하여 자연어 질문을 입력하고, 실제로 작동하는 시각화된 BI 리포트를 얻는 End-to-End 여정을 완성한다.**

### Current Gap Analysis

| Phase | Status | Gap Description |
|-------|--------|-----------------|
| Phase 1 (Step 1-3) | **100%** | Launch, Auth, Connection - 완료 |
| Phase 2 (Step 4-6) | **96%** | Intent, Targeting, Scanning - 거의 완료 |
| Phase 3 (Step 7-9) | **88%** | Planning, Thinking, Alignment - 기능 완성, 통합 미흡 |
| Phase 4 (Step 10-12) | **30%** | Query, Design, Interaction - 핵심 기능 미완성 |
| Phase 5 (Step 13-15) | **10%** | Preview, Refine, Export - 대부분 미구현 |

### Critical Problem
**"각 기능들이 사용자가 접속해서 결과물을 얻기까지 매우 세부적인 부분이 잘 구현되지 않았다"**

구체적으로:
1. **컴포넌트 간 연결 부재**: 개별 모듈은 존재하나 TUI 진입점(`bi_agent_console.py`)과 제대로 연결되지 않음
2. **데이터 흐름 단절**: `/analyze` 명령어 실행 시 실제 데이터 처리가 불완전
3. **시각화 파이프라인 미완성**: 쿼리 결과 -> 차트 렌더링 -> 사용자 출력 경로 불완전
4. **결과물 출력 미완성**: 웹 대시보드, Excel/PDF 내보내기 미구현

### MVP Scope Definition

**포함 (In Scope):**
- TUI 실행 -> LLM 인증 확인
- 데이터 소스 연결 (SQLite/PostgreSQL/Excel)
- 자연어 질문 입력 -> 의도 파싱
- 테이블 추천 및 선택
- SQL 자동 생성 및 실행
- TUI 내 차트 시각화
- 웹 대시보드 미리보기

**제외 (Out of Scope - Post MVP):**
- Tableau .twb 내보내기
- 고급 드릴다운/크로스필터링
- PDF 리포트 생성
- 실시간 협업 기능
- 고급 가설 검증 로직

---

## 2. End-to-End User Journey

### Happy Path Scenario

```
사용자: python -m backend.orchestrator.bi_agent_console 실행
    ↓
Step 1: [Launch] ASCII 배너 표시, 환경 체크
    ↓
Step 2: [Auth] LLM 인증 상태 확인 (사이드바 표시)
    ↓
사용자: /connect 입력
    ↓
Step 3: [Connection] ConnectionScreen 표시 → SQLite 파일 선택 → 테이블 스캔
    ↓
사용자: /explore 입력
    ↓
Step 4-6: [Explore] 테이블 목록 표시 → 테이블 선택 → 스키마 및 샘플 데이터 표시
    ↓
사용자: /analyze 매출 트렌드 분석해줘 입력
    ↓
Step 7: [Plan] LLM이 분석 파이프라인 생성, ThinkingPanel에 실시간 표시
    ↓
Step 8: [SQL] 쿼리 자동 생성 → 실행 → 결과 반환
    ↓
Step 9: [Visualize] TUI 내 ASCII 차트 렌더링 OR 웹 대시보드 오픈
    ↓
결과: 사용자가 분석 결과를 확인
```

### Journey Step Details

| Step | TUI Action | Backend Flow | Output |
|------|------------|--------------|--------|
| 1 | App Launch | `run_app()` → `BI_AgentConsole.__init__()` | Banner + sidebar |
| 2 | Check Auth | `auth_manager.is_authenticated()` | Sidebar status |
| 3 | `/connect` | `ConnectionScreen` → `conn_mgr.register()` | Connection saved |
| 4 | `/explore` | `MetadataScanner.scan_source()` | Table list |
| 5 | Select table | `context_manager.set_active_table()` | Context pinned |
| 6 | `/analyze` | `NLIntentParser.parse()` → `PipelineGenerator` | Analysis plan |
| 7 | Execute | `SQLGenerator` → `conn_mgr.run_query()` | DataFrame |
| 8 | Visualize | `TUIChartRenderer` / `DashboardGenerator` | Charts/Dashboard |

---

## 3. Core Features Breakdown

### P0 - MVP Critical (Must Have - 없으면 동작 불가)

| ID | Feature | Current State | Gap |
|----|---------|---------------|-----|
| P0-1 | TUI-to-Orchestrator 연결 | Partial | `/analyze` 명령이 실제 파이프라인 미실행 |
| P0-2 | SQL 생성 및 실행 | Exists | `collaborative_orchestrator`와 `SQLGenerator` 연동 필요 |
| P0-3 | 쿼리 결과 -> 차트 변환 | Partial | `TUIChartRenderer`가 실제 데이터 처리 미완성 |
| P0-4 | 웹 대시보드 미리보기 | Partial | `DashboardGenerator`가 불완전하게 동작 |
| P0-5 | 에러 핸들링 및 복구 | Weak | 연결 실패, 쿼리 실패 시 사용자 안내 부족 |

### P1 - MVP+ (Should Have - 사용자 경험 향상)

| ID | Feature | Current State | Gap |
|----|---------|---------------|-----|
| P1-1 | ThinkingPanel 실시간 업데이트 | 95% | AgentMessageBus 연동 완료, 애니메이션 미완 |
| P1-2 | HypothesisScreen 통합 | 100% screen | Console 통합 코드 누락 |
| P1-3 | ConstraintScreen 통합 | 100% screen | Console 통합 코드 누락 |
| P1-4 | 차트 추천 엔진 | 0% | `ChartRecommender` 미구현 |
| P1-5 | Excel 내보내기 | 0% | `OutputPackager` 확장 필요 |

### P2 - Future (Nice to Have)

| ID | Feature | Description |
|----|---------|-------------|
| P2-1 | PDF 리포트 | weasyprint 활용 |
| P2-2 | 고급 인터랙션 | varList/eventList 완전 지원 |
| P2-3 | 드릴다운 네비게이션 | 계층형 데이터 탐색 |
| P2-4 | 다중 차트 레이아웃 | 그리드 기반 배치 |

---

## 4. Detailed Implementation Tasks

### 4.0 Pre-Implementation Fixes (기존 코드 버그 수정)

**이 섹션의 작업은 다른 모든 작업보다 먼저 수행되어야 합니다.**

#### Task P0-0-A: collaborative_orchestrator.py import 수정

**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/orchestrator/collaborative_orchestrator.py`

**문제:** `context_manager`를 Line 51, 62, 108, 114, 120, 122, 139, 246 등에서 사용하지만 import 구문이 없어 `NameError: name 'context_manager' is not defined` 발생.

**수정:** Line 17 (import 블록 마지막) 이후에 다음 추가:

```python
from backend.orchestrator.context_manager import context_manager
```

**Acceptance Criteria:**
- `python -c "from backend.orchestrator.collaborative_orchestrator import CollaborativeOrchestrator"` 실행 시 import 에러 없음
- `/analyze` 명령 실행 시 `NameError` 발생하지 않음

---

### 4.1 P0-1: TUI-to-Orchestrator Complete Integration

**목표:** `/analyze` 명령 실행 시 전체 파이프라인이 End-to-End로 동작

**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/orchestrator/bi_agent_console.py`

| Task ID | Task | Acceptance Criteria |
|---------|------|---------------------|
| P0-1-A | `_handle_analyze_command()` 리팩토링 | `/analyze` 입력 시 `PipelineGenerator` 호출 |
| P0-1-B | Context 검증 강화 | 테이블 미선택 시 `/explore` 안내 메시지 |
| P0-1-C | 에러 복구 로직 | LLM 실패 시 재시도/대체 모델 안내 |
| P0-1-D | 진행 상태 표시 | 각 단계별 MessageBubble 업데이트 |

**Code Changes:**

```python
# bi_agent_console.py - _handle_analyze_command() 수정

async def _handle_analyze_command(self, query: str):
    """P0-1: Complete analysis pipeline integration"""
    from backend.orchestrator.context_manager import context_manager

    chat_log = self.query_one("#chat-log", VerticalScroll)

    # P0-1-B: Context validation
    if not context_manager.active_table:
        chat_log.mount(MessageBubble(
            role="system",
            content="[yellow]분석할 테이블을 먼저 선택해주세요.[/yellow]\n"
                    "[dim]힌트: /explore <conn_id>.<table_name> 으로 테이블을 선택하세요.[/dim]"
        ))
        return

    # P0-1-D: Progress indication
    chat_log.mount(MessageBubble(
        role="system",
        content=f"[bold cyan]분석 시작[/bold cyan]: '{context_manager.active_table}' 기반"
    ))

    try:
        # Step 1: Intent Analysis
        # NOTE: parse_analysis_intent()는 user_input 단일 파라미터만 받음 (스키마는 LLM이 추론)
        chat_log.mount(MessageBubble(role="system", content="[dim]1/4 의도 분석 중...[/dim]"))

        from backend.agents.bi_tool.nl_intent_parser import NLIntentParser
        parser = NLIntentParser(self.orchestrator.llm)
        intent = await parser.parse_analysis_intent(query)  # 단일 파라미터

        # Step 2: Pipeline Generation
        chat_log.mount(MessageBubble(role="system", content="[dim]2/4 분석 계획 수립 중...[/dim]"))

        from backend.agents.bi_tool.pipeline_generator import PipelineGenerator
        pipeline_gen = PipelineGenerator(self.orchestrator.llm, context_manager.active_schema)
        pipeline = await pipeline_gen.generate_pipeline(intent, [context_manager.active_table])

        # Display pipeline
        plan_msg = "[bold cyan]분석 계획:[/bold cyan]\n"
        for i, step in enumerate(pipeline.steps):
            plan_msg += f"  {i+1}. {step.description}\n"
        chat_log.mount(MessageBubble(role="agent", content=plan_msg))

        # Step 3: SQL Generation and Execution
        chat_log.mount(MessageBubble(role="system", content="[dim]3/4 쿼리 실행 중...[/dim]"))

        from backend.agents.data_source.sql_generator import (
            SQLGenerator, SchemaInfo, ColumnInfo, DatabaseDialect
        )
        sql_gen = SQLGenerator(self.orchestrator.llm)

        # 스키마 변환: context_manager.active_schema -> SchemaInfo 객체
        schema_info = self._convert_to_schema_info(context_manager.active_schema)
        db_dialect = self._get_db_dialect(context_manager.active_conn_id)

        # generate_sql_with_validation() 사용 (검증 기능 포함)
        sql_result = await sql_gen.generate_sql_with_validation(
            user_query=query,
            dialect=db_dialect,
            schema=schema_info,
            table_row_counts=None  # 선택적: 행 수 정보 있으면 전달
        )

        # SQL 결과 검증
        if not sql_result.is_valid:
            chat_log.mount(MessageBubble(
                role="system",
                content=f"[yellow]SQL 검증 경고:[/yellow] {', '.join(sql_result.warnings)}"
            ))

        df = self.orchestrator.conn_mgr.run_query(
            context_manager.active_conn_id,
            sql_result.sql  # .query가 아닌 .sql 속성 사용
        )

        # Step 4: Visualization
        chat_log.mount(MessageBubble(role="system", content="[dim]4/4 시각화 생성 중...[/dim]"))

        tui_data = self._prepare_tui_data(df, intent)

        # Show in TUI
        self.push_screen(VisualAnalysisScreen(tui_data, title=f"분석: {query[:30]}..."))

        # Generate web dashboard
        dash_result = self.orchestrator.dash_gen.generate_dashboard({
            "status": "success",
            "table": context_manager.active_table,
            "data": df.to_dict(orient="records"),
            "intent": intent.to_dict() if hasattr(intent, 'to_dict') else str(intent)
        })

        chat_log.mount(MessageBubble(
            role="system",
            content=f"[green]분석 완료![/green] 웹 대시보드: {dash_result}"
        ))

    except Exception as e:
        # P0-1-C: Error recovery
        logger.error(f"Analysis failed: {e}", exc_info=True)
        chat_log.mount(MessageBubble(
            role="system",
            content=f"[red]분석 중 오류 발생:[/red] {str(e)}\n"
                    "[dim]힌트: /errors 로 상세 로그를 확인하세요.[/dim]"
        ))
```

#### Helper Methods for bi_agent_console.py

다음 헬퍼 메서드들을 `BI_AgentConsole` 클래스에 추가해야 합니다:

```python
def _get_db_dialect(self, conn_id: str) -> 'DatabaseDialect':
    """
    연결 ID로부터 DatabaseDialect Enum 반환

    Args:
        conn_id: 연결 ID (예: "my_sqlite_db", "postgres_prod")

    Returns:
        DatabaseDialect enum 값
    """
    from backend.agents.data_source.sql_generator import DatabaseDialect

    conn_info = self.orchestrator.conn_mgr.get_connection(conn_id)
    conn_type = conn_info.get('type', '').lower() if conn_info else ''

    # 연결 타입 또는 conn_id 패턴으로 판단
    if 'postgres' in conn_type or 'postgres' in conn_id.lower():
        return DatabaseDialect.POSTGRESQL
    elif 'mysql' in conn_type or 'mysql' in conn_id.lower():
        return DatabaseDialect.MYSQL
    elif 'bigquery' in conn_type or 'bigquery' in conn_id.lower():
        return DatabaseDialect.BIGQUERY
    elif 'snowflake' in conn_type or 'snowflake' in conn_id.lower():
        return DatabaseDialect.SNOWFLAKE
    else:
        return DatabaseDialect.SQLITE  # default

def _convert_to_schema_info(self, active_schema: Dict[str, Any]) -> 'SchemaInfo':
    """
    context_manager.active_schema를 SQLGenerator의 SchemaInfo 객체로 변환

    Args:
        active_schema: context_manager에서 가져온 스키마 딕셔너리
            예: {"table_name": "sales", "columns": [{"name": "id", "type": "INT"}, ...]}

    Returns:
        SchemaInfo 객체
    """
    from backend.agents.data_source.sql_generator import SchemaInfo, ColumnInfo

    if not active_schema:
        return SchemaInfo()

    table_name = active_schema.get('table_name', 'unknown')
    columns = active_schema.get('columns', [])

    column_infos = [
        ColumnInfo(
            name=col.get('name', ''),
            data_type=col.get('type', col.get('data_type', 'TEXT')),
            table=table_name,
            nullable=col.get('nullable', True)
        )
        for col in columns
    ]

    return SchemaInfo(tables={table_name: column_infos})

def _prepare_tui_data(self, df: 'pd.DataFrame', intent: 'AnalysisIntent') -> Dict[str, Any]:
    """
    TUI 차트 렌더링을 위한 데이터 준비

    Args:
        df: 쿼리 실행 결과 DataFrame
        intent: 파싱된 AnalysisIntent 객체

    Returns:
        VisualAnalysisScreen에 전달할 데이터 딕셔너리
    """
    from backend.orchestrator.components.tui_charts import TUIChartRenderer

    # 차트 타입 자동 선택
    chart_type = TUIChartRenderer.auto_select_chart(df, intent.purpose)

    # KPI 메트릭 추출
    metrics = []
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    for col in numeric_cols[:3]:  # 상위 3개 숫자 컬럼
        metrics.append({
            "label": col,
            "value": f"{df[col].sum():,.0f}" if df[col].dtype in ['int64', 'float64'] else str(df[col].iloc[0]),
            "delta": "N/A",
            "color": "cyan"
        })

    # 차트 데이터 준비
    charts = []
    if len(df) > 0 and len(df.columns) >= 2:
        # 첫 번째 카테고리 컬럼과 첫 번째 숫자 컬럼으로 차트 생성
        cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        if cat_cols and numeric_cols:
            charts.append({
                "title": intent.title or f"{intent.purpose} 분석",
                "label_col": cat_cols[0],
                "value_col": numeric_cols[0],
                "data": df.head(20).to_dict(orient="records"),  # 상위 20개
                "chart_type": chart_type
            })

    return {
        "metrics": metrics,
        "charts": charts,
        "dataframe": df,
        "title": intent.title or f"{intent.purpose} 분석",
        "intent": {
            "purpose": intent.purpose,
            "target_metrics": intent.target_metrics,
            "scope": getattr(intent, 'scope', '전체')
        }
    }
```

**Acceptance Criteria for Helper Methods:**
- `_get_db_dialect()`: 연결 ID "sqlite_test"에 대해 `DatabaseDialect.SQLITE` 반환
- `_convert_to_schema_info()`: 빈 스키마에 대해 빈 `SchemaInfo()` 반환, 에러 없음
- `_prepare_tui_data()`: DataFrame이 비어있어도 에러 없이 기본 구조 반환

---

### 4.2 P0-2: SQL Generator Integration

**목표:** Intent 객체로부터 올바른 SQL 생성 및 안전한 실행

**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/data_source/sql_generator.py`

**기존 API 확인 (변경 불필요 - 이미 구현됨):**

`sql_generator.py`에는 이미 다음 메서드들이 구현되어 있습니다:

| 메서드 | 시그니처 | 용도 |
|--------|----------|------|
| `generate_sql()` | `async generate_sql(user_query: str, db_type: str, schema_info: str) -> str` | 기본 SQL 생성 |
| `generate_sql_with_validation()` | `async generate_sql_with_validation(user_query: str, dialect: DatabaseDialect, schema: SchemaInfo, table_row_counts: Optional[Dict]) -> SQLGenerationResult` | 검증 포함 SQL 생성 |

**Section 4.1에서 이미 `generate_sql_with_validation()` 사용으로 통합됨.**

| Task ID | Task | Acceptance Criteria |
|---------|------|---------------------|
| P0-2-A | `generate_from_intent()` 메서드 추가 (선택) | AnalysisIntent를 자연어로 변환 후 기존 `generate_sql_with_validation()` 호출 |
| P0-2-B | DB Dialect 자동 감지 | **이미 구현됨**: `DatabaseDialect` Enum, `DialectValidator` 클래스 |
| P0-2-C | 결과 검증 | **이미 구현됨**: `SQLGenerationResult.is_valid`, `.warnings` 필드 |

**추가 구현 (선택사항) - Intent-to-Query 래퍼:**

```python
# sql_generator.py - 편의 메서드 추가 (선택적)

async def generate_from_intent(
    self,
    intent: Union['AnalysisIntent', 'ChartIntent'],
    schema: SchemaInfo,
    dialect: DatabaseDialect = DatabaseDialect.SQLITE,
    table_row_counts: Optional[Dict[str, int]] = None
) -> SQLGenerationResult:
    """
    P0-2-A: Intent 객체로부터 자연어 쿼리를 구성한 후 SQL 생성

    이 메서드는 Intent의 속성들을 자연어로 변환하여
    기존 generate_sql_with_validation()을 호출합니다.

    Args:
        intent: AnalysisIntent 또는 ChartIntent 객체
        schema: SchemaInfo 객체
        dialect: DatabaseDialect enum
        table_row_counts: 테이블별 행 수 (비용 추정용)

    Returns:
        SQLGenerationResult
    """
    # Intent 속성을 자연어 쿼리로 변환
    query_parts = []

    if hasattr(intent, 'purpose'):
        purpose_map = {
            'trend': '추이 분석',
            'performance': '성과 분석',
            'comparison': '비교 분석',
            'anomaly': '이상치 탐지',
            'forecast': '예측 분석'
        }
        query_parts.append(purpose_map.get(intent.purpose, intent.purpose))

    if hasattr(intent, 'target_metrics') and intent.target_metrics:
        query_parts.append(f"측정 항목: {', '.join(intent.target_metrics)}")

    if hasattr(intent, 'filters') and intent.filters:
        filter_strs = [f"{f.get('field')} {f.get('operator')} {f.get('value')}" for f in intent.filters]
        query_parts.append(f"필터: {', '.join(filter_strs)}")

    if hasattr(intent, 'time_range') and intent.time_range:
        query_parts.append(f"기간: {intent.time_range}")

    natural_query = " | ".join(query_parts) if query_parts else "데이터 조회"

    return await self.generate_sql_with_validation(
        user_query=natural_query,
        dialect=dialect,
        schema=schema,
        table_row_counts=table_row_counts
    )
```

**핵심: Section 4.1 코드에서 이미 올바른 메서드를 호출하도록 수정됨**
- `generate_sql_with_validation()` 사용
- `DatabaseDialect` Enum 사용
- `SchemaInfo` 객체 변환 헬퍼 메서드 추가됨

---

### 4.3 P0-3: TUI Chart Rendering Enhancement

**목표:** 쿼리 결과를 다양한 차트 형태로 TUI에 렌더링

**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/orchestrator/components/tui_charts.py`

| Task ID | Task | Acceptance Criteria |
|---------|------|---------------------|
| P0-3-A | 라인 차트 추가 | 시계열 데이터용 `render_line_chart()` |
| P0-3-B | 파이 차트 추가 | 비율 데이터용 `render_pie_chart()` |
| P0-3-C | 스파크라인 추가 | KPI 카드 내 미니 차트 |
| P0-3-D | 자동 차트 선택 | 데이터 특성에 따른 차트 자동 결정 |

**Code Changes:**

```python
# tui_charts.py - 추가 메서드

class TUIChartRenderer:

    # ... existing methods ...

    @staticmethod
    def render_line_chart(
        df: pd.DataFrame,
        x_col: str,
        y_col: str,
        title: str = "Line Chart"
    ) -> Panel:
        """
        P0-3-A: 시계열 라인 차트 렌더링
        """
        if df.empty:
            return Panel("No data", title=title)

        # Normalize to 0-10 range for ASCII display
        y_min, y_max = df[y_col].min(), df[y_col].max()
        y_range = y_max - y_min if y_max != y_min else 1

        height = 10
        width = min(60, len(df))

        # Create grid
        grid = [[' ' for _ in range(width)] for _ in range(height)]

        # Plot points
        for i, (_, row) in enumerate(df.head(width).iterrows()):
            normalized = int(((row[y_col] - y_min) / y_range) * (height - 1))
            y_pos = height - 1 - normalized
            grid[y_pos][i] = '●'

            # Connect with lines
            if i > 0:
                prev_row = df.iloc[i-1]
                prev_norm = int(((prev_row[y_col] - y_min) / y_range) * (height - 1))
                prev_y = height - 1 - prev_norm
                # Simple line drawing
                for y in range(min(y_pos, prev_y), max(y_pos, prev_y) + 1):
                    if grid[y][i] == ' ':
                        grid[y][i] = '│'

        chart_str = '\n'.join([''.join(row) for row in grid])

        # Add axis labels
        chart_str += f"\n{'─' * width}"
        chart_str += f"\n{df[x_col].iloc[0]:<{width//2}} {df[x_col].iloc[-1]:>{width//2}}"

        return Panel(chart_str, title=f"[bold]{title}[/bold]", border_style="cyan")

    @staticmethod
    def render_sparkline(values: List[float]) -> str:
        """
        P0-3-C: 미니 스파크라인 (KPI 카드용)
        """
        if not values:
            return ""

        chars = "▁▂▃▄▅▆▇█"
        v_min, v_max = min(values), max(values)
        v_range = v_max - v_min if v_max != v_min else 1

        result = ""
        for v in values[-20:]:  # Last 20 values
            idx = int(((v - v_min) / v_range) * (len(chars) - 1))
            result += chars[idx]

        return result

    @staticmethod
    def auto_select_chart(
        df: pd.DataFrame,
        analysis_purpose: str = "general"
    ) -> str:
        """
        P0-3-D: 데이터 특성에 따른 차트 자동 선택

        Returns: "bar", "line", "pie", "table"
        """
        # Check for time-series columns
        date_cols = [c for c in df.columns if 'date' in c.lower() or 'time' in c.lower()]
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()

        if date_cols and numeric_cols:
            return "line"  # Time series -> line chart

        if len(categorical_cols) >= 1 and len(numeric_cols) >= 1:
            unique_count = df[categorical_cols[0]].nunique()
            if unique_count <= 5:
                return "pie"  # Few categories -> pie
            elif unique_count <= 20:
                return "bar"  # Medium categories -> bar
            else:
                return "table"  # Many categories -> table

        return "bar"  # Default
```

---

### 4.4 P0-4: Web Dashboard Generation Fix

**목표:** 생성된 대시보드가 실제로 브라우저에서 열리고 데이터 표시

**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/utils/dashboard_generator.py`

| Task ID | Task | Acceptance Criteria |
|---------|------|---------------------|
| P0-4-A | HTML 템플릿 완성 | Chart.js 기반 반응형 대시보드 |
| P0-4-B | 데이터 주입 | JSON 데이터가 올바르게 임베드 |
| P0-4-C | 자동 브라우저 오픈 | 생성 후 기본 브라우저에서 열기 |
| P0-4-D | 에러 처리 | 생성 실패 시 fallback 메시지 |

---

### 4.5 P0-5: Error Handling Enhancement

**목표:** 모든 실패 시나리오에 대한 명확한 사용자 안내

**파일 수정 대상:**
- `bi_agent_console.py`
- `collaborative_orchestrator.py`
- `connection_manager.py`

| Task ID | Task | Acceptance Criteria |
|---------|------|---------------------|
| P0-5-A | 연결 실패 핸들링 | DB 연결 실패 시 원인 분석 및 해결 안내 |
| P0-5-B | 쿼리 실패 핸들링 | SQL 에러 시 `QueryHealer` 자동 수정 시도 |
| P0-5-C | LLM 실패 핸들링 | API 에러 시 대체 모델 시도 또는 오프라인 모드 |
| P0-5-D | 일반 예외 핸들링 | 모든 예외가 `diagnostic_logger`에 기록 |

---

### 4.6 P1-1: HypothesisScreen Console Integration

**목표:** `/analyze` 실행 시 가설 선택 화면 자동 표시

**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/orchestrator/bi_agent_console.py`

| Task ID | Task | Acceptance Criteria |
|---------|------|---------------------|
| P1-1-A | Import 추가 | `from backend.orchestrator.screens import HypothesisScreen` |
| P1-1-B | 가설 생성 로직 | `HypothesisTemplateEngine`으로 가설 목록 생성 |
| P1-1-C | Screen Push | 가설 선택 후 콜백으로 분석 진행 |
| P1-1-D | 건너뛰기 옵션 | ESC로 기본 가설 사용 |

**Code Integration Point:**

```python
# bi_agent_console.py - _handle_analyze_command() 내부

# After intent parsing, before SQL generation:
from backend.agents.bi_tool.hypothesis_templates import HypothesisTemplateEngine, Industry
from backend.orchestrator.screens import HypothesisScreen

engine = HypothesisTemplateEngine()
# Detect industry from data (or use GENERAL)
hypotheses = engine.suggest_templates(
    Industry.GENERAL,
    context_manager.active_schema.get("columns", [])
)

# Convert to Hypothesis objects for screen
from backend.orchestrator.screens.hypothesis_screen import Hypothesis
hypothesis_objects = [
    Hypothesis(id=f"h_{i}", text=h.template, priority=0)
    for i, h in enumerate(hypotheses[:5])
]

def on_hypotheses_selected(selected: List[Hypothesis]):
    # Continue with analysis using selected hypotheses
    asyncio.create_task(self._continue_analysis(intent, selected))

self.push_screen(HypothesisScreen(hypothesis_objects, on_hypotheses_selected))
```

---

### 4.7 P1-2: ConstraintScreen Console Integration

**목표:** 분석 전 필터 조건 입력 화면 제공

**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/orchestrator/bi_agent_console.py`

| Task ID | Task | Acceptance Criteria |
|---------|------|---------------------|
| P1-2-A | Import 추가 | `from backend.orchestrator.screens import ConstraintScreen` |
| P1-2-B | 필드 목록 추출 | 스키마에서 필터 가능한 필드 추출 |
| P1-2-C | Screen Push | 가설 선택 후 제약조건 입력 |
| P1-2-D | 제약조건 적용 | SQL 생성 시 WHERE 절에 반영 |

---

### 4.8 P1-3: Chart Recommender Implementation

**목표:** 데이터 특성에 따른 최적 차트 자동 추천

**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/chart_recommender.py` (NEW)

| Task ID | Task | Acceptance Criteria |
|---------|------|---------------------|
| P1-3-A | `ChartRecommender` 클래스 생성 | 데이터 특성 분석 메서드 |
| P1-3-B | 차트 타입 매핑 | 시계열->Line, 분포->Histogram, 비교->Bar |
| P1-3-C | 추천 순위 생성 | 근거와 함께 상위 3개 추천 |
| P1-3-D | TUI 통합 | `VisualAnalysisScreen`에서 추천 차트 사용 |

---

### 4.9 P1-4: Excel Export Implementation

**목표:** 분석 결과를 Excel 파일로 내보내기

**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/utils/output_packager.py`

| Task ID | Task | Acceptance Criteria |
|---------|------|---------------------|
| P1-4-A | `export_to_excel()` 메서드 추가 | openpyxl 사용 |
| P1-4-B | 다중 시트 지원 | 데이터, 요약, 차트 설정 각각 시트 |
| P1-4-C | 스타일링 | 헤더 굵게, 숫자 포맷팅 |
| P1-4-D | `/export` 명령어 추가 | TUI에서 내보내기 실행 |

---

## 5. Integration Architecture

### Data Flow Diagram

```
[User Input]
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  bi_agent_console.py (TUI Entry Point)                      │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ on_input_submitted │  │ handle_command  │                   │
│  └────────┬────────┘  └────────┬────────┘                   │
│           │                     │                            │
│           ▼                     ▼                            │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              _handle_analyze_command()               │    │
│  └──────────────────────┬──────────────────────────────┘    │
└─────────────────────────┼───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  collaborative_orchestrator.py                               │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐ │
│  │ NLIntentParser │→│PipelineGenerator│→│  SQLGenerator   │ │
│  └───────┬────────┘  └───────┬────────┘  └───────┬────────┘ │
│          │                   │                    │          │
│          ▼                   ▼                    ▼          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              conn_mgr.run_query()                    │    │
│  └──────────────────────┬──────────────────────────────┘    │
└─────────────────────────┼───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Visualization Layer                                         │
│  ┌────────────────┐  ┌────────────────┐                     │
│  │TUIChartRenderer│  │DashboardGenerator│                    │
│  └───────┬────────┘  └───────┬────────┘                     │
│          │                    │                              │
│          ▼                    ▼                              │
│  ┌────────────────┐  ┌────────────────┐                     │
│  │VisualAnalysisScreen│  │ Browser Open  │                     │
│  └────────────────┘  └────────────────┘                     │
└─────────────────────────────────────────────────────────────┘
```

### Component Dependencies

```
bi_agent_console.py
├── collaborative_orchestrator.py
│   ├── NLIntentParser (nl_intent_parser.py)
│   ├── PipelineGenerator (pipeline_generator.py)
│   ├── SQLGenerator (sql_generator.py)
│   ├── ConnectionManager (connection_manager.py)
│   └── DashboardGenerator (dashboard_generator.py)
├── context_manager.py
├── screens/
│   ├── HypothesisScreen
│   ├── ConstraintScreen
│   ├── TableSelectionScreen
│   └── VisualAnalysisScreen
└── components/
    ├── TUIChartRenderer
    └── data_grid.py
```

---

## 6. Acceptance Criteria

### P0 Completion Criteria

| Criterion | Test Method | Pass Condition |
|-----------|-------------|----------------|
| TUI 실행 | `python -m backend.orchestrator.bi_agent_console` | 배너 표시, 입력 가능 |
| 연결 설정 | `/connect` → SQLite 선택 | 테이블 목록 표시 |
| 테이블 탐색 | `/explore <conn>.<table>` | 스키마 및 샘플 표시 |
| 분석 실행 | `/analyze 매출 분석` | 차트 렌더링 또는 대시보드 |
| 에러 복구 | 잘못된 쿼리 입력 | 명확한 에러 메시지 |

### P1 Completion Criteria

| Criterion | Test Method | Pass Condition |
|-----------|-------------|----------------|
| 가설 선택 | `/analyze` 후 가설 화면 | 가설 선택 후 분석 진행 |
| 제약조건 입력 | 가설 선택 후 필터 화면 | 날짜/카테고리 필터 적용 |
| 차트 추천 | 자동 차트 선택 | 데이터에 적합한 차트 |
| Excel 내보내기 | `/export excel` | .xlsx 파일 생성 |

---

## 7. Implementation Schedule

### Week 1: P0 Critical Path

| Day | Tasks | Deliverables |
|-----|-------|--------------|
| Day 1 | P0-1-A, P0-1-B | TUI-Orchestrator 기본 연결 |
| Day 2 | P0-2-A, P0-2-B | SQL Generator Intent 연동 |
| Day 3 | P0-3-A, P0-3-D | TUI 차트 렌더링 완성 |
| Day 4 | P0-4-A, P0-4-B, P0-4-C | 웹 대시보드 동작 |
| Day 5 | P0-5-A~D, 통합 테스트 | 에러 핸들링 및 검증 |

### Week 2: P1 Enhancement

| Day | Tasks | Deliverables |
|-----|-------|--------------|
| Day 1-2 | P1-1, P1-2 | Screen 통합 완료 |
| Day 3 | P1-3 | ChartRecommender |
| Day 4 | P1-4 | Excel 내보내기 |
| Day 5 | 통합 테스트 및 문서화 | MVP 완성 |

---

## 8. Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| LLM API 제한 | High | High | 로컬 Ollama fallback, 캐싱 |
| DB 연결 실패 | Medium | High | 명확한 에러 메시지, 재시도 로직 |
| TUI 렌더링 이슈 | Medium | Medium | 간단한 fallback 텍스트 출력 |
| 대용량 데이터 처리 | Medium | Medium | LIMIT 1000, 페이지네이션 |

---

## 9. File Change Summary

### Pre-Implementation Fixes (P0-0) - MUST DO FIRST

| File | Change | Priority |
|------|--------|----------|
| `/backend/orchestrator/collaborative_orchestrator.py` | Line 17 이후에 `from backend.orchestrator.context_manager import context_manager` 추가 | **CRITICAL** |

### New Files to Create

1. `/backend/agents/bi_tool/chart_recommender.py` (P1-3)
2. `/backend/tests/test_chart_recommender.py`
3. `/backend/tests/test_constraint_screen.py` (기존 누락분)

### Files to Modify

| Priority | File | Tasks | Changes |
|----------|------|-------|---------|
| **P0-0** | `/backend/orchestrator/collaborative_orchestrator.py` | P0-0-A | import 추가 (기존 버그 수정) |
| **P0-1** | `/backend/orchestrator/bi_agent_console.py` | P0-1-A~D, P1-1, P1-2 | `_handle_analyze_command()` 전체 재작성, 헬퍼 메서드 3개 추가 |
| **P0-2** | `/backend/agents/data_source/sql_generator.py` | P0-2-A (선택) | `generate_from_intent()` 편의 메서드 추가 (선택적) |
| **P0-3** | `/backend/orchestrator/components/tui_charts.py` | P0-3-A~D | 라인/파이 차트, 스파크라인, auto_select_chart 추가 |
| **P0-4** | `/backend/utils/dashboard_generator.py` | P0-4-A~D | HTML 템플릿, 데이터 주입, 브라우저 오픈 |
| **P0-5** | `/backend/orchestrator/collaborative_orchestrator.py` | P0-5-A~D | 에러 핸들링 강화 |
| **P1-4** | `/backend/utils/output_packager.py` | P1-4-A~D | Excel 내보내기 |

### Implementation Order (권장)

```
1. P0-0-A (collaborative_orchestrator.py import 수정) - 5분
2. P0-1 (bi_agent_console.py 전체 통합) - 2시간
3. P0-3 (tui_charts.py 차트 추가) - 1시간
4. P0-4 (dashboard_generator.py 수정) - 1시간
5. P0-5 (에러 핸들링) - 30분
6. 통합 테스트 - 1시간
```

---

## 10. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| End-to-End 성공률 | 90% | 10회 시나리오 테스트 중 9회 성공 |
| 평균 응답 시간 | < 30초 | 분석 요청 -> 결과 표시 |
| 에러 메시지 명확성 | 100% | 모든 에러에 해결 힌트 포함 |
| 차트 정확성 | 95% | 데이터와 시각화 일치 |

---

---

## 11. Revision History

| Version | Date | Changes | Reviewer |
|---------|------|---------|----------|
| 1.0 | 2026-02-02 | Initial plan creation | Prometheus |
| 1.1 | 2026-02-02 | **Critical Fixes Applied:** | Prometheus |
| | | - P0-0 섹션 추가: collaborative_orchestrator.py context_manager import 누락 수정 | |
| | | - P0-1 코드: `parse_analysis_intent(query)` 단일 파라미터로 수정 (Line 177 TypeError 해결) | |
| | | - P0-1 코드: `sql_gen.generate_query()` → `sql_gen.generate_sql_with_validation()` 수정 | |
| | | - P0-1 코드: `sql_result.query` → `sql_result.sql` 속성명 수정 | |
| | | - 헬퍼 메서드 3개 구현 명세 추가: `_get_db_dialect()`, `_convert_to_schema_info()`, `_prepare_tui_data()` | |
| | | - P0-2 섹션: 기존 API 명세 정리, 선택적 `generate_from_intent()` 래퍼 명세 추가 | |
| | | - File Change Summary: 구현 순서 및 우선순위 명시 | |

---

## 12. Critical Issues Resolution Summary

**Architect Feedback (7.2/10 - APPROVED_WITH_MODIFICATIONS):** Addressed

**Critic Feedback (REJECT - 3 Critical Issues):** All Resolved

| Issue ID | Description | Resolution |
|----------|-------------|------------|
| **CI-1** | `parse_analysis_intent(query, schema)` - 잘못된 시그니처 | `parse_analysis_intent(query)` 단일 파라미터로 수정 |
| **CI-2** | `context_manager` import 누락 (기존 코드 버그) | P0-0 섹션에 import 추가 명세 |
| **CI-3** | `_get_db_type()`, `_prepare_tui_data()` 미정의 | 헬퍼 메서드 전체 구현 명세 추가 (+ `_convert_to_schema_info()` 추가) |

**추가 수정:**
- `sql_gen.generate_query()` → `sql_gen.generate_sql_with_validation()` (실제 메서드명)
- `sql_result.query` → `sql_result.sql` (실제 속성명)
- `DatabaseDialect` Enum import 추가
- `SchemaInfo`, `ColumnInfo` 객체 변환 로직 추가

---

**PLAN_READY: .omc/plans/bi-agent-mvp-detailed-design.md**

---

**Prepared by:** Prometheus (Strategic Planning Consultant)
**Date:** 2026-02-02
**Version:** 1.1 (Critic Issues Resolved)
**Status:** READY FOR EXECUTION - All Critical Issues Resolved
