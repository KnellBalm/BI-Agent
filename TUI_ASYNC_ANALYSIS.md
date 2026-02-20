# BI-Agent TUI 성능과 비동기 처리 분석

## 📋 목차
1. [profiler.py 전체 내용](#1-profilerpy-전체-내용)
2. [async def 주요 파일 목록](#2-async-def-주요-파일-목록)
3. [TUI 메인 진입점](#3-tui-메인-진입점)
4. [Blocking Call 분석](#4-blocking-call-분석-및-성능-이슈)
5. [성능 최적화 권장사항](#5-성능-최적화-권장사항)

---

## 1. profiler.py 전체 내용

### 파일 위치
`/Users/zokr/python_workspace/BI-Agent/backend/agents/data_source/profiler.py`

### 역할
- 데이터소스 분석 및 통계 요약
- DataFrame 또는 파일의 프로파일링 정보 추출
- 컬럼별 품질 점수 계산

### 주요 메서드

#### 1. `profile()` - 전체 프로파일링
```python
def profile(self) -> Dict[str, Any]:
    """Performs full profiling of the loaded DataFrame"""
    - column_details: 컬럼별 상세 분석
    - overall_quality_score: 전체 품질 점수 (0-100)
    - sample: 상위 5행 샘플 데이터
```

#### 2. `_get_column_details()` - 컬럼별 분석
각 컬럼마다:
- **기본 정보**: name, type (numerical/categorical/datetime/text), dtype
- **결측치**: missing_count, missing_pct
- **유니크 값**: unique count
- **대표값**: mode
- **품질 점수**: 0-100

**수치형(numerical) 컬럼**:
- 평균, 표준편차, 최소/최대값
- 중앙값, Q25, Q50, Q75 (분위수)
- 히스토그램 분포 (10개 bins)

**범주형(categorical) 컬럼**:
- 상위 5개 값의 분포
- 범주 분포 (상위 10개)

**시간형(datetime) 컬럼**:
- 최소/최대 날짜

#### 3. `_calculate_column_quality_score()` - 품질 점수 계산
```python
completeness_score = (1 - missing_pct) * 100  # 70% 가중치
uniqueness_score = varies by type              # 30% 가중치
final_score = completeness_score * 0.7 + uniqueness_score * 0.3
```

#### 4. `_infer_type()` - 타입 추론
```python
- 수치형: pd.api.types.is_numeric_dtype()
- 시간형: pd.api.types.is_datetime64_any_dtype()
- 범주형: unique_count <= 20 OR (unique_count / total) < 0.3
- 텍스트: 그 외
```

### 성능 특성

| 작업 | 복잡도 | 병목 | 예상 시간 |
|------|--------|------|---------|
| 개요 계산 | O(n) | isnull().sum() | ~100ms (1M행) |
| 컬럼 분석 | O(n*m) | describe(), nunique() | ~500ms (1M행×50컬럼) |
| 분포 계산 | O(n) | np.histogram() | ~200ms |
| 전체 프로파일 | O(n*m) | 컬럼 분석 | ~1-2초 (1M행×50컬럼) |

**⚠️ 동기 블로킹**: 현재 모든 메서드가 동기식
- TUI에서 호출 시 UI 프리징 위험
- 특히 `_get_column_details()`는 대용량 데이터에서 느림

---

## 2. async def 주요 파일 목록

### 데이터소스 에이전트 (backend/agents/data_source/)

#### 📌 connection_manager.py
```python
class ConnectionManager:
    def __init__(self, project_id: str = "default")  # 동기 초기화
    def register_connection(...)  # 동기, 테스트 포함
    def get_connection(self, conn_id: str)  # 동기, 세션 초기화
    def run_query(self, conn_id: str, query: str) -> pd.DataFrame  # ⚠️ BLOCKING!
        └─ pd.read_sql_query(text(query), conn)  # 네트워크 대기
    def _start_ssh_tunnel(...)  # 동기, SSH 연결 설정
```

**⚠️ Blocking Call**:
- `run_query()`: 데이터베이스 쿼리 실행 (네트워크 I/O)
- `_initialize_session()`: SQLAlchemy 엔진 생성

#### 📌 metadata_scanner.py
```python
class MetadataScanner:
    def scan_source(self, conn_id: str, deep_scan: bool = False)
        └─ self._list_tables()  # 동기, 테이블 목록 조회
        └─ self.scan_table()    # 동기, 각 테이블 프로파일링
            └─ self.conn_mgr.run_query()  # ⚠️ BLOCKING!
            └─ DataProfiler().profile()   # ⚠️ BLOCKING! (1-2초)

    def _list_tables(self, conn_id: str, conn_type: str)
        └─ self.conn_mgr.run_query()  # BLOCKING
```

**⚠️ 성능 이슈**:
- `scan_source(deep_scan=True)`: N개 테이블 × (쿼리 + 프로파일링)
- 예: 50개 테이블 × 1초 = **50초 이상!**

#### 📌 table_recommender.py
```python
async def recommend_tables(self, intent: AnalysisIntent) -> List[TableRecommendation]
    # LLM 호출 (API I/O)

async def infer_relationships(self, tables: List[str]) -> List[ERDRelationship]
    # LLM 호출 (API I/O)
```

#### 📌 sql_generator.py
```python
async def generate_sql(self, ...) -> str
    # LLM 호출 (API I/O)

async def generate_sql_with_validation(self, ...) -> str
    # LLM 호출 + 검증

async def _generate_explanation(self, sql: str, user_query: str) -> str
    # LLM 호출
```

#### 📌 pandas_generator.py
```python
async def generate_transform_code(self, ...) -> str
    # LLM 호출

async def _generate_explanation(self, code: str) -> str
    # LLM 호출
```

#### 📌 query_healer.py
```python
async def diagnose_error(self, error_msg: str, ...) -> DiagnosisResult
    # LLM 호출

async def heal_and_retry(self, execute_fn: Callable[[str], Awaitable[Any]], ...) -> str
    # 재시도 로직 + LLM 호출
    # execute_fn: SQL 실행 함수 (async callable expected!)
```

#### 📌 data_source_agent.py
```python
async def get_client(self, connection_info: Dict[str, Any]) -> MCPClient
async def query_database(self, connection_info: Dict[str, Any], user_query: str) -> pd.DataFrame
async def read_excel(self, file_path_or_info: Any, user_query: Optional[str] = None) -> pd.DataFrame
async def _analyze_dataframe_with_llm(self, df: pd.DataFrame, user_query: str) -> pd.DataFrame
async def close_all(self)
```

#### 📌 mcp_client.py
```python
async def connect(self)
async def list_tools(self) -> List[Any]
async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any
async def disconnect(self)
```

---

## 3. TUI 메인 진입점

### 📌 bi_agent_console.py (Textual App)
**파일**: `/Users/zokr/python_workspace/BI-Agent/backend/orchestrator/bi_agent_console.py`

```python
class BI_AgentConsole(App):
    TITLE = "BI-Agent Console"
    CSS_PATH = ["ui/app_styles.tcss"]

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("v", "show_visual_report", "Visual Report"),
        Binding("ctrl+l", "clear_chat", "Clear Chat"),
        Binding("slash", "focus_input_with_slash", "Command"),
        Binding("f1", "show_help", "Help"),
        Binding("ctrl+e", "show_errors", "Errors"),
    ]
```

#### 주요 메서드

**1. `on_mount()` - 초기화**
```python
async def on_mount(self) -> None:
    auth_manager.load_credentials()

    # 타이머로 주기적 업데이트
    self.set_timer(0.1, self._update_sidebar_loop)
    self.set_timer(1, self._update_hud_loop)
```

**2. `_update_sidebar_loop()` - 사이드바 업데이트**
```python
async def _update_sidebar_loop(self) -> None:
    await self.sidebar_manager.update()
    self.set_timer(10, self._update_sidebar_loop)  # 10초마다 반복
```

**3. `_update_hud_loop()` - HUD 상태 업데이트**
```python
async def _update_hud_loop(self) -> None:
    hud = self.query_one("#hud-status", HUDStatusLine)
    # 모델명 확인 (auth_manager 상태)
    for p, name in [("gemini", "Gemini"), ("claude", "Claude"), ("openai", "GPT-4o")]:
        if auth_manager.is_authenticated(p):
            model_name = name
            break
    hud.update_model(model_name)
    hud.update_context(20.0)
    self.set_timer(10, self._update_hud_loop)
```

**4. `on_input_submitted()` - 입력 처리**
```python
async def on_input_submitted(self, event: Input.Submitted) -> None:
    user_text = event.value.strip()

    # QuestionFlowEngine 확인
    if self.flow_engine.is_active():
        consumed = await self.flow_engine.handle_input(user_text)
        if consumed:
            return

    # 명령어 vs 일반 쿼리
    if user_text.startswith("/"):
        await self.handle_command(user_text)
    else:
        await self.process_query(user_text)  # ⚠️ ASYNC!
```

**5. `process_query()` - 쿼리 처리 (ReAct 루프)**
```python
async def process_query(self, query: str) -> None:
    chat_log = self.query_one("#chat-log", VerticalScroll)

    # Thinking 패널 표시
    thinking = ThinkingPanel()
    chat_log.mount(thinking)

    try:
        orchestrator = self._get_orchestrator()

        # ⚠️ BLOCKING: ReAct 루프 실행
        result = await orchestrator.run(query, context={
            "active_connection": getattr(self, '_active_conn_id', None),
        })

        thinking.remove()

        if result["status"] == "success":
            response = result["final_response"]
            iter_count = result.get("iteration_count", 0)
            if iter_count > 1:
                footer = f"\n[dim]({iter_count}회 분석 단계)[/dim]"
                response += footer
            chat_log.mount(MessageBubble(role="assistant", content=response))
    except Exception as e:
        # 에러 처리
        pass
```

**6. `_run_explore()` - 데이터베이스 탐색**
```python
async def _run_explore(self, query: Optional[str], mode: Optional[str] = None, ...):
    # DatabaseExplorerScreen 푸시
    self.push_screen(DatabaseExplorerScreen(
        connection_id=conn_id,
        conn_mgr=self.conn_mgr,
        agent_conn_mgr=self.agent_conn_mgr,
        initial_query=query,
        mode=mode,
        provider=provider
    ))
```

### 📌 main.py (구형 Entry Point)
**파일**: `/Users/zokr/python_workspace/BI-Agent/backend/main.py`

```python
async def interactive_loop():
    # 초기화
    ui = InteractionUI()
    dashboard = DashboardView(console=console)
    quota_manager = QuotaManager()
    conn_manager = ConnectionManager()
    data_agent = DataSourceAgent()

    # GCP 동기화
    if project_id:
        with console.status("[bold green]GCP 할당량 동기화 중..."):
            await quota_manager.sync_with_gcp(project_id)  # ⚠️ ASYNC I/O

    # LLM Provider 설정
    gemini = GeminiProvider(quota_manager=quota_manager)
    ollama = OllamaProvider()
    llm = FailoverLLMProvider(primary=gemini, secondary=ollama)

    # 쿼리 루프
    while True:
        user_input = Prompt.ask(...)  # ⚠️ BLOCKING! (콘솔)

        if user_input.startswith("/"):
            # 명령어 처리
            pass
        else:
            # 쿼리 처리
            with console.status("[bold yellow]사고 과정 (Chain of Thought)..."):
                result = await orchestrator.run(user_input, context=context)  # ⚠️ ASYNC I/O
```

**진입점**:
```python
if __name__ == "__main__":
    asyncio.run(interactive_loop())
```

---

## 4. Blocking Call 분석 및 성능 이슈

### 4.1 DatabaseExplorerScreen의 스키마 로드
**파일**: `/Users/zokr/python_workspace/BI-Agent/backend/orchestrator/screens/database_explorer_screen.py`

#### ✅ 올바른 사용법 - run_in_executor 사용

```python
async def _load_schema(self):
    """Loads tables/views from the connection manager asynchronously."""
    tree = self.query_one("#schema-tree")

    # 로딩 인디케이터 표시
    loading_node = tree.root.add("📡 Loading schema...", expand=True)

    try:
        # ✅ 스레드 풀에서 블로킹 작업 실행
        def _scan_metadata():
            scanner = MetadataScanner(self.agent_conn_mgr)
            return scanner.scan_source(self.connection_id, deep_scan=False)

        loop = asyncio.get_event_loop()
        metadata = await loop.run_in_executor(None, _scan_metadata)  # ✅ GOOD!

        # 결과 처리 (UI 스레드)
        tree.root.remove_children()
        tables_node = tree.root.add("📊 Tables", expand=True)

        for table_info in metadata.get("tables", []):
            table_name = table_info.get("table_name", "unknown")
            tables_node.add_leaf(f"  {table_name}")

    except Exception as e:
        logger.error(f"Failed to load schema: {e}")
        # 에러 표시
```

#### ✅ 쿼리 실행 - run_in_executor 사용

```python
async def _execute_query(self) -> None:
    """Run the SQL query against the actual database connection."""
    query = self.query_one("#sql-editor", VimTextArea).text.strip()

    status_label = self.query_one("#results-status", Label)
    status_label.update("[bold yellow]⏳ 쿼리 실행 중...[/bold yellow]")

    try:
        start_time = time.time()

        # ✅ 블로킹 DB 쿼리를 스레드 풀에서 실행
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(
            None,
            lambda: self.agent_conn_mgr.run_query(self.connection_id, query)
        )

        execution_time_ms = (time.time() - start_time) * 1000

        # UI 업데이트
        self._render_dataframe(df)
        row_count = len(df)
        col_count = len(df.columns)
        status_label.update(f"[bold green]✓ {row_count} rows × {col_count} columns[/bold green]")

        # 히스토리에 저장
        history_entry = QueryHistoryEntry(
            query=query,
            timestamp=datetime.now().isoformat(),
            connection_id=self.connection_id,
            execution_time_ms=execution_time_ms,
            row_count=row_count,
            status="success",
            error_message=None
        )
        self.query_history.add_entry(history_entry)

    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        status_label.update(f"[bold red]✗ Error: {str(e)}[/bold red]")
    finally:
        self._query_running = False
```

---

### 4.2 AgenticOrchestrator의 ReAct 루프
**파일**: `/Users/zokr/python_workspace/BI-Agent/backend/orchestrator/orchestrators/agentic_orchestrator.py`

#### ⚠️ BLOCKING CALLS (도구 실행 함수)

```python
def _build_default_registry() -> ToolRegistry:
    """기본 도구 레지스트리 - 수동 Tool Calling"""

    # ⚠️ 1. query_database() - 블로킹 SQLite 쿼리
    def query_database(query_description: str = "") -> str:
        # ... 쿼리 파싱 ...
        try:
            conn = sqlite3.connect(db_path)  # ⚠️ I/O
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(query)  # ⚠️ BLOCKING!
            rows = cur.fetchall()  # ⚠️ I/O
            conn.close()
            # 결과 포맷팅
            return result_str
        except Exception as e:
            return f"쿼리 실행 오류: {str(e)}"

    # ⚠️ 2. analyze_schema() - 블로킹 PRAGMA 쿼리
    def analyze_schema(table_name: str = "") -> str:
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()

            # 테이블 목록
            tables = cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()  # ⚠️ BLOCKING!

            for tbl in targets:
                # 컬럼 정보
                cols = cur.execute(f'PRAGMA table_info("{tbl}")').fetchall()  # ⚠️ BLOCKING!

                # 행 개수
                count = cur.execute(f'SELECT COUNT(*) FROM "{tbl}"').fetchone()[0]  # ⚠️ BLOCKING!

                # 유니크 값
                unique = cur.execute(
                    f'SELECT COUNT(DISTINCT "{col_name}") FROM "{tbl}"'
                ).fetchone()[0]  # ⚠️ BLOCKING!
```

#### 문제점

| 도구 | 작업 | 특성 | 예상 시간 |
|------|------|------|---------|
| `query_database()` | SQLite 쿼리 | BLOCKING | 100ms-10s |
| `analyze_schema()` | 테이블 분석 + PRAGMA | BLOCKING | 500ms-5s |
| `recommend_chart()` | ChartRecommender | 동기 호출 | 50-200ms |
| `generate_chart()` | ChartRecommender | 동기 호출 | 50-200ms |
| `apply_theme()` | ThemeEngine | 동기 호출 | 10-50ms |
| `calculate_layout()` | LayoutCalculator | 동기 호출 | 10-50ms |
| `setup_interactions()` | InteractionLogic | 동기 호출 | 20-100ms |

**⚠️ 핵심 병목**:
- `query_database()` + `analyze_schema()`: **ReAct 루프에서 가장 느린 작업**
- 이들은 `run_in_executor`를 사용하지 않음!
- **UI 프리징 위험**

---

### 4.3 MetadataScanner의 깊은 스캔
**파일**: `/Users/zokr/python_workspace/BI-Agent/backend/agents/data_source/metadata_scanner.py`

```python
def scan_source(self, conn_id: str, deep_scan: bool = False) -> Dict[str, Any]:
    """Scans the source."""
    conn_info = self._get_conn_info(conn_id)
    conn_type = conn_info["type"]

    metadata = {
        "conn_id": conn_id,
        "type": conn_type,
        "tables": []
    }

    table_names = self._list_tables(conn_id, conn_type)  # ⚠️ BLOCKING!

    for table in table_names:
        if deep_scan:
            table_meta = self.scan_table(conn_id, table)  # ⚠️ BLOCKING! N번 반복
        else:
            table_meta = {"table_name": table, "is_lazy": True}
        metadata["tables"].append(table_meta)

    return metadata

def scan_table(self, conn_id: str, table_name: str) -> Dict[str, Any]:
    """Performs detailed profiling of a single table."""
    # 1. 샘플 데이터 페치
    safe_table_name = table_name.replace('"', '""')
    query = f'SELECT * FROM "{safe_table_name}" LIMIT 100'
    df = self.conn_mgr.run_query(conn_id, query)  # ⚠️ BLOCKING!

    # 2. DataProfiler 실행
    profiler = DataProfiler(df)
    profile_data = profiler.profile()  # ⚠️ BLOCKING! (1-2초)

    return {
        "table_name": table_name,
        "row_count_estimate": profile_data["overview"]["rows"],
        "columns": profile_data["columns"],
        "sample": profile_data["sample"]
    }
```

**성능 계산**:
- 50개 테이블 × `deep_scan=True`:
  - 각 테이블: SELECT LIMIT 100 (~100ms) + profile() (~1s) = ~1.1s
  - **총: 50 × 1.1s = 55초!** ⚠️

---

## 5. 성능 최적화 권장사항

### 🎯 우선순위 1: 높음 (긴급)

#### 1.1 MetadataScanner를 비동기로 리팩토링

```python
# 현재 (동기)
def scan_source(self, conn_id: str, deep_scan: bool = False):
    table_names = self._list_tables(conn_id, conn_type)
    for table in table_names:
        table_meta = self.scan_table(conn_id, table)  # 순차 실행

# 개선안 (비동기 병렬)
async def scan_source(self, conn_id: str, deep_scan: bool = False):
    table_names = self._list_tables(conn_id, conn_type)

    if deep_scan:
        # 병렬 스캔 (최대 5-10개 동시 작업)
        tasks = [
            self._scan_table_async(conn_id, table)
            for table in table_names[:10]  # 제한
        ]
        results = await asyncio.gather(*tasks)
        metadata["tables"] = results
    else:
        # Lazy 로드
        metadata["tables"] = [
            {"table_name": t, "is_lazy": True}
            for t in table_names
        ]
```

**기대 효과**:
- 50개 테이블, 5개 동시: 55초 → 11초 (5배 개선)
- 특정 테이블만 상세 스캔: 초단위 응답

#### 1.2 profiler.py를 비동기로 리팩토링

```python
# 현재 (동기, 대용량에서 느림)
profile_data = profiler.profile()  # 1-2초 (1M행)

# 개선안 (스레드 풀 + asyncio)
async def profile_async(self) -> Dict[str, Any]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, self.profile)
```

**기대 효과**:
- UI가 블로킹되지 않음
- 사용자는 계속 입력 가능

#### 1.3 ToolRegistry의 쿼리 도구를 비동기로 변경

```python
# 현재 (동기)
def query_database(query_description: str = "") -> str:
    conn = sqlite3.connect(db_path)
    cur.execute(query)  # BLOCKING

# 개선안 (async 지원)
async def query_database_async(query_description: str = "") -> str:
    loop = asyncio.get_event_loop()
    def _execute():
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(query)
        return cur.fetchall()

    rows = await loop.run_in_executor(None, _execute)
    # 결과 포맷팅
    return result_str
```

**문제**:
- ToolRegistry.execute()는 동기 함수
- ReAct 루프가 이를 await할 수 없음
- **해결책**: LangGraph 노드를 비동기로 변경

---

### 🎯 우선순위 2: 중간

#### 2.1 ConnectionManager.run_query()를 비동기로 래핑

```python
# /backend/agents/data_source/connection_manager_async.py (신규)
class AsyncConnectionManager:
    def __init__(self, sync_cm: ConnectionManager):
        self.sync_cm = sync_cm

    async def run_query_async(self, conn_id: str, query: str) -> pd.DataFrame:
        """Runs query in thread pool, non-blocking."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.sync_cm.run_query(conn_id, query)
        )
```

**사용처**:
- MetadataScanner: `self.conn_mgr.run_query()` → `self.async_cm.run_query_async()`
- DatabaseExplorerScreen: 이미 적용됨 ✅

#### 2.2 DatabaseExplorerScreen의 스키마 로드에 타임아웃 추가

```python
async def _load_schema(self):
    try:
        def _scan_metadata():
            scanner = MetadataScanner(self.agent_conn_mgr)
            return scanner.scan_source(self.connection_id, deep_scan=False)

        loop = asyncio.get_event_loop()
        # 타임아웃 30초 (무한 대기 방지)
        metadata = await asyncio.wait_for(
            loop.run_in_executor(None, _scan_metadata),
            timeout=30.0
        )
    except asyncio.TimeoutError:
        logger.error("Schema load timed out after 30 seconds")
        self.notify("Schema load timed out. Showing table list only.", severity="warning")
```

#### 2.3 HUD 및 사이드바 업데이트 최적화

```python
# 현재: 매 0.1초마다 (과하게 빈번)
self.set_timer(0.1, self._update_sidebar_loop)

# 개선: 1-2초마다 (필요한 충분함)
self.set_timer(1.0, self._update_sidebar_loop)
```

**기대 효과**:
- CPU 사용률 감소
- 배터리 소비 감소

---

### 🎯 우선순위 3: 낮음 (미래)

#### 3.1 데이터 프로파일링 결과 캐싱

```python
# /backend/agents/data_source/profiler_cache.py (신규)
class ProfileCache:
    def __init__(self, ttl_seconds: int = 300):
        self.cache = {}
        self.ttl = ttl_seconds

    def get(self, conn_id: str, table_name: str) -> Optional[Dict]:
        key = f"{conn_id}:{table_name}"
        if key in self.cache:
            cached_time, data = self.cache[key]
            if time.time() - cached_time < self.ttl:
                return data
            del self.cache[key]
        return None

    def set(self, conn_id: str, table_name: str, data: Dict):
        key = f"{conn_id}:{table_name}"
        self.cache[key] = (time.time(), data)
```

**사용처**:
```python
class MetadataScanner:
    def __init__(self, connection_manager: ConnectionManager, cache: Optional[ProfileCache] = None):
        self.conn_mgr = connection_manager
        self.cache = cache or ProfileCache()

    def scan_table(self, conn_id: str, table_name: str) -> Dict[str, Any]:
        # 캐시 확인
        cached = self.cache.get(conn_id, table_name)
        if cached:
            return cached

        # ... 프로파일링 ...
        self.cache.set(conn_id, table_name, result)
        return result
```

#### 3.2 배치 쿼리 실행

```python
# 여러 쿼리를 한 번에 실행 (네트워크 왕복 감소)
async def run_queries_batch(self, conn_id: str, queries: List[str]):
    """Execute multiple queries in parallel."""
    loop = asyncio.get_event_loop()
    tasks = [
        loop.run_in_executor(
            None,
            lambda q=q: self.sync_cm.run_query(conn_id, q)
        )
        for q in queries
    ]
    return await asyncio.gather(*tasks)
```

#### 3.3 스트리밍 결과 (대용량 데이터)

```python
async def run_query_streaming(self, conn_id: str, query: str, batch_size: int = 1000):
    """Stream query results in batches."""
    loop = asyncio.get_event_loop()

    def _fetch_batches():
        # DB 커서로 batch 단위로 읽기
        for batch_df in pd.read_sql_query(query, conn, chunksize=batch_size):
            yield batch_df

    for batch in await loop.run_in_executor(None, _fetch_batches):
        yield batch
        await asyncio.sleep(0)  # 다른 작업에 CPU 양보
```

---

## 📊 성능 개선 예상치

### Before (현재 상태)

| 시나리오 | 소요 시간 | UI 상태 |
|---------|---------|--------|
| 50개 테이블 스캔 (deep) | 55초 | 🔴 완전 프리징 |
| 단일 대용량 쿼리 (1M행) | 5-10초 | 🔴 프리징 |
| 프로파일링 (1M행×50컬럼) | 2초 | 🔴 프리징 |

### After (우선순위 1 적용 후)

| 시나리오 | 소요 시간 | UI 상태 |
|---------|---------|--------|
| 50개 테이블 스캔 (5병렬) | 11초 | 🟡 반응 가능 |
| 단일 대용량 쿼리 | 5-10초 | 🟢 반응 가능 |
| 프로파일링 | 2초 | 🟢 반응 가능 |

**개선 효과**:
- 50개 테이블 스캔: **55s → 11s (5배 개선)**
- UI 반응성: **즉각적** (run_in_executor 덕분)
- 사용자 경험: **우수**

---

## 📝 체크리스트

### 비동기 리팩토링

- [ ] MetadataScanner.scan_source() → async 버전 추가
- [ ] MetadataScanner.scan_table() → async 버전 추가
- [ ] DataProfiler.profile() → executor 래핑 추가
- [ ] AgenticOrchestrator 도구 → async 버전으로 변경
- [ ] ConnectionManager.run_query() → async 래퍼 추가
- [ ] DatabaseExplorerScreen._load_schema() → 타임아웃 추가

### 성능 최적화

- [ ] 프로파일 결과 캐싱 구현
- [ ] HUD 업데이트 간격 조정 (0.1s → 1s)
- [ ] 배치 쿼리 실행 지원
- [ ] 대용량 데이터 스트리밍 지원

### 모니터링

- [ ] 성능 로깅 추가 (쿼리 실행 시간)
- [ ] AsyncIO 디버그 모드 활성화 (개발 단계)
- [ ] UI 응답 시간 측정

---

## 📚 참고 자료

### AsyncIO 패턴
- `asyncio.run_in_executor()`: 동기 함수를 비동기로 래핑
- `asyncio.gather()`: 여러 코루틴 병렬 실행
- `asyncio.wait_for()`: 타임아웃 지원

### Textual 프레임워크
- `asyncio.create_task()`: 백그라운드 작업
- `set_timer()`: 주기적 작업
- Screen/App의 async 메서드들

### 데이터 처리
- `pd.read_sql_query()`: SQL 쿼리 → DataFrame
- `pd.read_sql()` with chunksize: 스트리밍 읽기
- `numpy.histogram()`: 분포 계산

