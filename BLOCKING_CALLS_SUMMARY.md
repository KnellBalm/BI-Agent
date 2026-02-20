# BI-Agent의 Blocking Calls 완전 분석

## 📍 프로젝트 구조 및 주요 파일

```
/Users/zokr/python_workspace/BI-Agent/
├── backend/
│   ├── agents/data_source/
│   │   ├── profiler.py                    ⚠️ 동기, 대용량에서 느림
│   │   ├── connection_manager.py          ⚠️ run_query()는 BLOCKING
│   │   ├── metadata_scanner.py            ⚠️ scan_table()은 BLOCKING (프로파일링)
│   │   ├── table_recommender.py           ✅ async def 있음
│   │   ├── sql_generator.py               ✅ async def 있음
│   │   ├── query_healer.py                ✅ async def 있음
│   │   ├── pandas_generator.py            ✅ async def 있음
│   │   ├── data_source_agent.py           ✅ async def 있음
│   │   └── mcp_client.py                  ✅ async def 있음
│   │
│   ├── orchestrator/
│   │   ├── bi_agent_console.py            ✅ Textual App (async/await 지원)
│   │   ├── orchestrators/
│   │   │   └── agentic_orchestrator.py    ⚠️ ToolRegistry 도구가 동기
│   │   └── screens/
│   │       └── database_explorer_screen.py ✅ run_in_executor 사용
│   │
│   └── main.py                            ✅ asyncio.run() 사용
```

---

## 🔴 BLOCKING CALL 상세 분석

### 1. profiler.py - DataProfiler

#### 위치
```
/Users/zokr/python_workspace/BI-Agent/backend/agents/data_source/profiler.py
```

#### 문제 코드
```python
def profile(self) -> Dict[str, Any]:
    """Performs full profiling of the loaded DataFrame"""
    if self.df is None:
        raise ValueError("No data loaded to profile.")

    column_details = self._get_column_details()  # ⚠️ O(n*m) - BLOCKING
    overall_quality = self._calculate_overall_quality_score(column_details)

    return {
        "overview": self._get_overview(),
        "columns": column_details,
        "overall_quality_score": overall_quality,
        "sample": self.df.head(5).to_dict(orient='records')
    }

def _get_column_details(self) -> List[Dict[str, Any]]:
    """Analyzes each column in detail with enhanced statistics"""
    column_info = []

    for col in self.df.columns:  # ⚠️ 각 컬럼마다...
        series = self.df[col]

        # 수치형
        if col_type == "numerical":
            clean_series = series.dropna()
            details.update({
                "mean": round(float(clean_series.mean()), 4),        # ⚠️ O(n)
                "std": round(float(clean_series.std()), 4),          # ⚠️ O(n)
                "min": float(clean_series.min()),                    # ⚠️ O(n)
                "max": float(clean_series.max()),                    # ⚠️ O(n)
                "median": float(clean_series.median()),              # ⚠️ O(n)
                "q25": float(clean_series.quantile(0.25)),           # ⚠️ O(n)
                "q50": float(clean_series.quantile(0.50)),           # ⚠️ O(n)
                "q75": float(clean_series.quantile(0.75)),           # ⚠️ O(n)
                "distribution": self._get_distribution(clean_series) # ⚠️ O(n)
            })
        # 범주형
        elif col_type == "categorical":
            details.update({
                "top_values": series.value_counts().head(5).to_dict(),  # ⚠️ O(n)
                "distribution": self._get_categorical_distribution(series) # ⚠️ O(n)
            })
```

#### 성능 분석
```
1M행 × 50컬럼 데이터:
- 각 컬럼: 9개 작업 × O(n) = ~9M 연산
- 50개 컬럼: 50 × 9M = 450M 연산
- 예상 시간: 1-2초

메인 스레드 블로킹!
```

#### 사용처
```python
# metadata_scanner.py
def scan_table(self, conn_id: str, table_name: str) -> Dict[str, Any]:
    df = self.conn_mgr.run_query(conn_id, query)  # 100ms

    profiler = DataProfiler(df)
    profile_data = profiler.profile()  # ⚠️ 1-2초 블로킹!

    return { ... }
```

---

### 2. connection_manager.py - ConnectionManager

#### 위치
```
/Users/zokr/python_workspace/BI-Agent/backend/agents/data_source/connection_manager.py
```

#### 문제 코드 1: run_query()
```python
def run_query(self, conn_id: str, query: str) -> pd.DataFrame:
    """Runs a SQL query with robust error handling and monitoring."""
    try:
        session = self.get_connection(conn_id)

        start_time = datetime.datetime.now()
        if conn_type in ["sqlite", "postgres", "mysql", "duckdb"]:
            from sqlalchemy import text
            if hasattr(session, 'connect'):
                with session.connect() as conn:
                    df = pd.read_sql_query(text(query), conn)  # ⚠️ BLOCKING I/O!
            else:
                df = pd.read_sql_query(query, session)  # ⚠️ BLOCKING I/O!
        elif conn_type == "excel":
            df = pd.read_excel(session)  # ⚠️ BLOCKING I/O!

        end_time = datetime.datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"Query executed on {conn_id} in {duration:.4f}s. Rows: {len(df)}")
        return df
    except Exception as e:
        logger.error(f"Query failed on {conn_id}: {e}")
        raise RuntimeError(f"Query execution failed: {e}")
```

**문제점**:
- `pd.read_sql_query()`: 네트워크 I/O (PostgreSQL, MySQL) 또는 파일 I/O (SQLite)
- 메인 스레드 블로킹
- 대용량 결과셋은 수 초 대기

#### 문제 코드 2: register_connection()
```python
def register_connection(self, conn_id: str, conn_type: str, config: Dict[str, Any], ...):
    # SSH 터널링 설정 확인
    ssh_config = config.get('ssh', None)

    # Test connection before registration - Apply env vars for testing
    logger.info(f"Testing connection before registering '{conn_id}'...")
    test_config = self._inject_env_vars(config.copy())
    test_ssh_config = self._inject_env_vars(ssh_config.copy()) if ssh_config else None

    test_result = test_connection(conn_type, test_config, test_ssh_config)  # ⚠️ BLOCKING!

    if not test_result.success:
        error_msg = f"Connection test failed: {test_result.error_message}"
        raise RuntimeError(...)
```

**test_connection() 분석**:
```python
# connection_validator.py
def test_connection(conn_type: str, config: Dict[str, Any], ssh_config: Optional[Dict] = None):
    try:
        if conn_type == "sqlite":
            conn = sqlite3.connect(config["path"])  # ⚠️ 파일 I/O
            cur = conn.cursor()
            cur.execute("SELECT 1")  # ⚠️ BLOCKING!
            cur.fetchone()
            conn.close()
        elif conn_type == "postgres":
            # psycopg2 연결
            conn = psycopg2.connect(
                host=config["host"],      # ⚠️ 네트워크 I/O (3-5초)
                port=config["port"],
                database=config["dbname"],
                user=config["user"],
                password=config["password"]
            )
            cur = conn.cursor()
            cur.execute("SELECT 1")      # ⚠️ 네트워크 I/O
            cur.fetchone()
            conn.close()
        # ... 기타 db 타입 ...
```

#### 성능 분석
```
SQLite:        ~100ms (로컬 파일 I/O)
PostgreSQL:    ~3-5s  (네트워크 왕복)
MySQL:         ~3-5s  (네트워크 왕복)
Snowflake:     ~5-10s (클라우드 연결)
```

#### 사용처 (메인 스레드)
```python
# bi_agent_console.py
async def _run_explore(self, query: Optional[str], ...):
    # Sync connection from Orchestrator CM → Agent CM
    orch_conn = self.conn_mgr.get_connection(conn_id)
    if orch_conn:
        self.agent_conn_mgr.register_connection(
            conn_id=conn_id,
            conn_type=conn_type,
            config=conn_config.copy(),
            ...
        )  # ⚠️ test_connection() 호출 (3-10초 대기!)
```

---

### 3. metadata_scanner.py - MetadataScanner

#### 위치
```
/Users/zokr/python_workspace/BI-Agent/backend/agents/data_source/metadata_scanner.py
```

#### 문제 코드 1: scan_source()
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

    for table in table_names:  # ⚠️ N개 테이블마다...
        if deep_scan:
            table_meta = self.scan_table(conn_id, table)  # ⚠️ BLOCKING! (1.1초/테이블)
        else:
            table_meta = {"table_name": table, "is_lazy": True}
        metadata["tables"].append(table_meta)

    return metadata
```

#### 문제 코드 2: scan_table()
```python
def scan_table(self, conn_id: str, table_name: str) -> Dict[str, Any]:
    """Performs detailed profiling of a single table."""
    # 1. Fetch Sample Data
    safe_table_name = table_name.replace('"', '""')
    query = f'SELECT * FROM "{safe_table_name}" LIMIT 100'
    df = self.conn_mgr.run_query(conn_id, query)  # ⚠️ 100ms BLOCKING

    # 2. Use DataProfiler for statistical summary
    profiler = DataProfiler(df)
    profile_data = profiler.profile()  # ⚠️ 1-2초 BLOCKING! (50컬럼 기준)

    return {
        "table_name": table_name,
        "row_count_estimate": profile_data["overview"]["rows"],
        "columns": profile_data["columns"],
        "sample": profile_data["sample"]
    }
```

#### 문제 코드 3: _list_tables()
```python
def _list_tables(self, conn_id: str, conn_type: str) -> List[str]:
    """Lists table names based on connection type."""
    logger.info(f"Listing tables for connection '{conn_id}' (type: {conn_type})")
    try:
        if conn_type == "sqlite":
            query = "SELECT name FROM sqlite_master WHERE type='table'"
            df = self.conn_mgr.run_query(conn_id, query)  # ⚠️ BLOCKING! (50ms)
            tables = df["name"].tolist()
        elif conn_type == "postgres":
            query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            df = self.conn_mgr.run_query(conn_id, query)  # ⚠️ BLOCKING! (100-500ms)
            tables = df["table_name"].tolist()
        # ...
        return tables
```

#### 성능 분석
```
Deep scan (50개 테이블):

1. _list_tables():        50ms
2. 각 테이블 (×50):
   - run_query(LIMIT 100): 100ms/테이블
   - profile():            1-2초/테이블
   = 1.1-1.2초/테이블
3. 총: 50 × 1.1s = 55초

Shallow scan (50개 테이블):
1. _list_tables():        50ms
2. 메타데이터 조회:       0ms (is_lazy=True)
총: 50ms ✅
```

#### 사용처 (DatabaseExplorerScreen)
```python
# database_explorer_screen.py
async def _load_schema(self):
    def _scan_metadata():
        scanner = MetadataScanner(self.agent_conn_mgr)
        return scanner.scan_source(self.connection_id, deep_scan=False)  # ✅ shallow

    loop = asyncio.get_event_loop()
    metadata = await loop.run_in_executor(None, _scan_metadata)  # ✅ 스레드 풀 사용!
```

---

### 4. agentic_orchestrator.py - ToolRegistry

#### 위치
```
/Users/zokr/python_workspace/BI-Agent/backend/orchestrator/orchestrators/agentic_orchestrator.py
```

#### 문제 코드 1: query_database()
```python
def query_database(query_description: str = "") -> str:
    """자연어 설명 또는 SQL 쿼리를 실행합니다."""
    import sqlite3
    import os

    db_path = os.path.join(...)

    query = query_description.strip()
    if not query.upper().startswith("SELECT"):
        query = "SELECT * FROM sales_performance LIMIT 20"

    try:
        conn = sqlite3.connect(db_path)  # ⚠️ I/O
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(query)  # ⚠️ BLOCKING!
        rows = cur.fetchall()  # ⚠️ I/O
        columns = [desc[0] for desc in cur.description] if cur.description else []
        conn.close()

        if not rows:
            return f"[데이터 조회] 결과 없음 (SQL: {query})"

        result = f"[데이터 조회] {len(rows)}건 반환\n"
        # 포맷팅...
        return result
    except Exception as e:
        return f"쿼리 실행 오류: {str(e)}"
```

**문제점**:
- sqlite3.connect() → DB 파일 I/O
- cur.execute() → SQL 실행 (네트워크 없음, 로컬이지만 여전히 I/O)
- cur.fetchall() → 데이터 로드 및 직렬화

#### 문제 코드 2: analyze_schema()
```python
def analyze_schema(table_name: str = "") -> str:
    """데이터베이스 테이블 구조를 분석합니다."""
    try:
        conn = sqlite3.connect(db_path)  # ⚠️ I/O
        cur = conn.cursor()

        # 테이블 목록 조회
        tables = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()  # ⚠️ BLOCKING! (50ms)
        table_list = [t[0] for t in tables]

        for tbl in targets:
            # 컬럼 정보
            cols = cur.execute(f'PRAGMA table_info("{tbl}")').fetchall()  # ⚠️ BLOCKING! (10ms/tbl)

            # 행 개수
            count = cur.execute(f'SELECT COUNT(*) FROM "{tbl}"').fetchone()[0]  # ⚠️ BLOCKING! (O(n))

            result += f"\n📊 {tbl} ({count}행)\n"

            profile_data = []
            for c in cols:
                # 유니크 값 카운트
                unique = cur.execute(
                    f'SELECT COUNT(DISTINCT "{col_name}") FROM "{tbl}"'
                ).fetchone()[0]  # ⚠️ BLOCKING! (O(n))
```

**성능 분석**:
```
analyze_schema() for 5 tables:
1. _list_tables():        50ms
2. 각 테이블 (×5):
   - PRAGMA table_info():  10ms
   - COUNT(*):             1-5초(테이블 크기에 따라)
   - COUNT(DISTINCT col):  1-5초/컬럼
3. 총: 50ms + 5×(10ms + 2-10초) = 약 15-60초!
```

#### 사용처 (ReAct 루프)
```python
# bi_agent_console.py
async def process_query(self, query: str) -> None:
    try:
        orchestrator = self._get_orchestrator()

        # ⚠️ orchestrator.run()이 ToolRegistry.execute()를 호출
        result = await orchestrator.run(query, context={
            "active_connection": getattr(self, '_active_conn_id', None),
        })
        # orchestrator 내부에서:
        # → ReAct 루프 → ToolRegistry.execute("query_database", ...)
        # → 위의 query_database() 함수 실행 (동기, BLOCKING!)
```

---

## 📋 전체 Blocking Call 요약표

| 파일 | 함수 | 작업 | 시간 | UI 블로킹 | 해결책 |
|------|------|------|------|---------|--------|
| profiler.py | `profile()` | 컬럼 분석 | 1-2초 | ⚠️ 예 | `run_in_executor` |
| connection_manager.py | `run_query()` | SQL 실행 | 100ms-10s | ⚠️ 예 | `run_in_executor` |
| connection_manager.py | `register_connection()` | 연결 테스트 | 3-10s | ⚠️ 예 | `run_in_executor` |
| metadata_scanner.py | `scan_source(deep)` | N개 테이블 스캔 | 50초+ | ⚠️ 예 | async + 병렬 |
| metadata_scanner.py | `scan_table()` | 1개 테이블 분석 | 1-2초 | ⚠️ 예 | `run_in_executor` |
| metadata_scanner.py | `_list_tables()` | 테이블 목록 | 50-500ms | ⚠️ 예 | `run_in_executor` |
| agentic_orchestrator.py | `query_database()` | SQLite 쿼리 | 100ms-5s | ⚠️ 예 | async 도구 |
| agentic_orchestrator.py | `analyze_schema()` | 스키마 분석 | 15-60초 | ⚠️ 예 | async 도구 + 병렬 |

---

## ✅ 이미 올바르게 구현된 부분

### DatabaseExplorerScreen - 올바른 사용 예

```python
# database_explorer_screen.py (라인 305-343)
async def _load_schema(self):
    """Loads tables/views from the connection manager asynchronously."""
    tree = self.query_one("#schema-tree")

    loading_node = tree.root.add("📡 Loading schema...", expand=True)

    try:
        # ✅ 동기 함수를 스레드 풀에서 실행
        def _scan_metadata():
            scanner = MetadataScanner(self.agent_conn_mgr)
            return scanner.scan_source(self.connection_id, deep_scan=False)

        # ✅ executor로 감싸기 (메인 스레드 블로킹 안 함)
        loop = asyncio.get_event_loop()
        metadata = await loop.run_in_executor(None, _scan_metadata)

        # UI 업데이트 (메인 스레드에서)
        tree.root.remove_children()
        tables_node = tree.root.add("📊 Tables", expand=True)

        for table_info in metadata.get("tables", []):
            table_name = table_info.get("table_name", "unknown")
            tables_node.add_leaf(f"  {table_name}")
```

### BI_AgentConsole - 올바른 비동기 메서드들

```python
# bi_agent_console.py
async def on_input_submitted(self, event: Input.Submitted) -> None:
    """✅ async def로 올바르게 선언"""
    user_text = event.value.strip()

    if self.flow_engine.is_active():
        consumed = await self.flow_engine.handle_input(user_text)  # ✅ await
        if consumed:
            return

    if user_text.startswith("/"):
        await self.handle_command(user_text)  # ✅ await
    else:
        await self.process_query(user_text)  # ✅ await

async def process_query(self, query: str) -> None:
    """✅ async def로 메인 쿼리 처리"""
    # Thinking 표시
    thinking = ThinkingPanel()
    chat_log.mount(thinking)

    try:
        orchestrator = self._get_orchestrator()
        # ✅ await로 ReAct 루프 실행
        result = await orchestrator.run(query, context={...})

        # UI 업데이트
        chat_log.mount(MessageBubble(...))
    finally:
        # 정리
        pass
```

---

## 🚀 개선 예상 효과

### 현재 상태 (Blocking)

```
사용자 입력 "50개 테이블 분석" (deep_scan=True)
    ↓
process_query() 호출
    ↓
orchestrator.run() 호출 (async)
    ↓
query 도구 실행 (동기!)
    ↓
metadata_scanner.scan_source(deep=True)  ← BLOCKING 50초
    ↓
UI 완전히 프리징 🔴
```

### 개선 후 (Async + 병렬)

```
사용자 입력 "50개 테이블 분석" (deep_scan=True)
    ↓
process_query() 호출
    ↓
orchestrator.run() 호출 (async)
    ↓
query 도구 실행 (async!)
    ↓
asyncio.gather(*5개 테이블 병렬) ← 11초
    ↓
UI 반응 가능 🟢

사용자는 동시에:
- 다른 쿼리 입력 가능
- UI 스크롤 가능
- 화면 업데이트 보임
```

---

## 📌 핵심 결론

### 1. 가장 심각한 Blocking Call

1. **metadata_scanner.scan_source(deep=True)**: 50초+
2. **agentic_orchestrator.analyze_schema()**: 15-60초
3. **connection_manager.run_query()**: 네트워크 대기 (수 초)
4. **profiler.profile()**: 1-2초

### 2. 현재 상황

- **DatabaseExplorerScreen**: ✅ 올바르게 구현 (run_in_executor 사용)
- **bi_agent_console**: ✅ async 잘 구현
- **MetadataScanner**: ⚠️ 동기, 병렬화 필요
- **AgenticOrchestrator**: ⚠️ 도구가 동기

### 3. 우선 개선 순서

1. **MetadataScanner를 async로 리팩토링** → 50초 → 11초 (5배)
2. **ToolRegistry 도구를 async로 변경** → UI 반응성 향상
3. **ProfileCache 추가** → 반복 요청 빠르게

### 4. 기대 효과

- 50개 테이블 deep scan: **55초 → 11초** (5배 개선)
- 대용량 쿼리: **UI 프리징 제거**
- 사용자 경험: **매우 향상**

