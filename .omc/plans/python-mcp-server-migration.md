# Python MCP Server Migration Plan

## Context

### Original Request
사용자 질문: "backend/mcp_servers 에 있는 MCP들이 전부 JS로 되어있는데 Python으로 할 수는 없는건가?"

Answer: **Yes, absolutely possible.** The Python MCP SDK (mcp package) provides full protocol parity with the JavaScript SDK via the FastMCP server implementation.

### Current State Analysis

**Existing JavaScript MCP Servers (6 total):**
| Server | File | Tools | Complexity |
|--------|------|-------|------------|
| PostgreSQL | `postgres_server.js` | query, list_tables, describe_table | Medium |
| MySQL | `mysql_server.js` | query, list_tables, describe_table | Medium |
| Excel | `excel_server.js` | read_excel, list_sheets, write_excel | Low |
| BigQuery | `bigquery_server.js` | query, list_datasets, list_tables | Medium |
| Snowflake | `snowflake_server.js` | query, list_tables | Medium |
| GCP Manager | `gcp_manager_server.js` | get_quota_usage, get_billing_info | Low |

**JavaScript SDK Pattern:**
```javascript
const server = new Server({ name, version }, { capabilities: { tools: {} } });
server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: [...] }));
server.setRequestHandler(CallToolRequestSchema, async (request) => { ... });
const transport = new StdioServerTransport();
await server.connect(transport);
```

**Python SDK Equivalent (FastMCP) - ARCHITECT APPROVED PATTERN:**
```python
#!/usr/bin/env python3
import asyncio
import json
import os
import signal
import sys
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("postgres-mcp-server")
_pool = None  # Lazy initialization

async def get_pool():
    """Lazy connection pool initialization"""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            min_size=1,
            max_size=10,
        )
    return _pool

async def cleanup():
    """Graceful shutdown handler"""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
    print("Server shutting down gracefully", file=sys.stderr)

def setup_signal_handlers():
    """Setup SIGTERM/SIGINT handlers for graceful shutdown"""
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(cleanup()))

@mcp.tool()
async def query(sql: str) -> str:
    """Execute a read-only SQL query on PostgreSQL database"""
    if not sql.strip().lower().startswith('select'):
        raise ValueError("Only SELECT queries are allowed")  # FastMCP handles isError automatically
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql)
        return json.dumps({
            "rows": [dict(r) for r in rows],
            "rowCount": len(rows)
        }, indent=2)

if __name__ == "__main__":
    setup_signal_handlers()
    mcp.run(transport="stdio")
```

### Research Findings

| Aspect | JavaScript SDK | Python SDK |
|--------|---------------|------------|
| Package | `@modelcontextprotocol/sdk` | `mcp` (PyPI) |
| Latest Version | 0.5.0 | 1.26.0 (Jan 2026) |
| Minimum Required | - | **1.23.0** (Nov 2025 protocol update) |
| Transport | StdioServerTransport | stdio, SSE, Streamable HTTP |
| Tool Definition | Schema object | Decorator-based |
| Async Support | Native (Promise) | Native (asyncio) |
| Type Safety | TypeScript | Pydantic models |
| Error Handling | Manual `isError: true` | **Automatic via exceptions** |

**Key Advantages of Python Migration:**
1. **Native Integration**: Backend is already Python-based (FastAPI, langgraph, pandas)
2. **Better Type Safety**: Pydantic models provide runtime validation
3. **Simpler Syntax**: Decorator-based tool definition is more Pythonic
4. **Unified Stack**: No need for Node.js runtime dependency
5. **Automatic Error Handling**: FastMCP converts exceptions to `isError: true` automatically
6. **Existing Dependencies**: `mcp>=0.1.0` already in requirements.txt (needs upgrade)

---

## Work Objectives

### Core Objective
Migrate all 6 JavaScript MCP servers to Python using the FastMCP framework while maintaining full backward compatibility with existing MCP client code.

### Deliverables
1. Connection lifecycle management module with signal handlers
2. 6 Python MCP server files (`*_server.py`) with equivalent functionality
3. Updated `mcp_client.py` to support both Python and Node.js servers
4. Updated `mcp_bridge.py` with Python server paths
5. Updated `package.json` with Python server scripts
6. Migration documentation

### Definition of Done
- [ ] All 6 Python servers pass tool listing tests
- [ ] All 6 Python servers pass tool execution tests
- [ ] Existing MCP client can connect to Python servers
- [ ] Graceful shutdown works on SIGTERM/SIGINT
- [ ] No regression in existing functionality
- [ ] Documentation updated

---

## Guardrails

### MUST Have
- Exact tool name parity (query, list_tables, etc.)
- Exact input schema parity (same required/optional parameters)
- Exact output format parity (JSON structure)
- Backward compatible MCP protocol compliance
- **Exception-based error handling** (FastMCP auto-converts to `isError: true`)
- Environment variable support for credentials
- **Graceful shutdown with signal handlers**
- **Lazy connection pool initialization**
- **PYTHONUNBUFFERED=1 and PYTHONIOENCODING=utf-8 environment variables**

### MUST NOT Have
- Breaking changes to tool names or schemas
- Hard-coded credentials in source files
- Removal of JavaScript servers (keep for reference initially)
- Changes to MCP protocol version
- **Manual `isError: true` JSON construction** (use exceptions instead)
- **Hardcoded "python" command** (use `sys.executable`)
- New external dependencies beyond existing requirements.txt (except cloud/db drivers)

---

## Task Flow and Dependencies

```
Phase 1: Foundation (No Dependencies)
    |
    +-- TODO 1.1: Base Module
    +-- TODO 1.2: requirements.txt
    +-- TODO 1.3: Connection Lifecycle Module (NEW)
    |
    v
Phase 2: Database Servers (Depends on Phase 1)
    |
    +-- TODO 2.1: PostgreSQL Server
    +-- TODO 2.2: MySQL Server
    |
    v
Phase 3: Utility Servers (Depends on Phase 1)
    |
    +-- TODO 3.1: Excel Server
    |
    v
Phase 4: Cloud Servers (Depends on Phase 1)
    |
    +-- TODO 4.1: BigQuery Server
    +-- TODO 4.2: Snowflake Server
    +-- TODO 4.3: GCP Manager Server
    |
    v
Phase 5: Integration (Depends on Phases 2-4)
    |
    +-- TODO 5.1: MCP Client Update
    +-- TODO 5.2: MCP Bridge Update
    +-- TODO 5.3: package.json Update
    |
    v
Phase 6: Testing & Documentation (Depends on Phase 5)
    |
    +-- TODO 6.1: Test Suite
    +-- TODO 6.2: Documentation
```

---

## Detailed TODOs

### Phase 1: Foundation Setup

#### TODO 1.1: Create Python MCP Server Base Module
**File:** `backend/mcp_servers/__init__.py`
**Description:** Create shared utilities and base patterns for Python MCP servers

**Acceptance Criteria:**
- [ ] `__init__.py` with common imports
- [ ] Logging configuration (stderr, not stdout)
- [ ] Common JSON serialization helpers
- [ ] Version constant for all servers

**Estimated Effort:** 20 minutes

#### TODO 1.2: Update requirements.txt (CRITIC UPDATED)
**File:** `backend/requirements.txt`
**Description:** Ensure MCP SDK and all cloud/database drivers are pinned appropriately

**Changes Required:**
```diff
- mcp>=0.1.0
+ mcp>=1.23.0  # Required for November 2025 protocol update

+ # Async Database Drivers
+ asyncpg>=0.29.0  # Async PostgreSQL driver
+ aiomysql>=0.2.0  # Async MySQL driver

+ # Cloud Providers (for BigQuery, Snowflake, GCP Manager)
+ google-cloud-bigquery>=3.0.0
+ google-cloud-monitoring>=2.0.0
+ google-cloud-billing>=1.0.0
+ snowflake-connector-python>=3.6.0
```

**Acceptance Criteria:**
- [ ] `mcp>=1.23.0` (CRITICAL: required for November 2025 protocol update)
- [ ] `asyncpg>=0.29.0` for async PostgreSQL
- [ ] `aiomysql>=0.2.0` for async MySQL
- [ ] `google-cloud-bigquery>=3.0.0` for BigQuery
- [ ] `google-cloud-monitoring>=2.0.0` for GCP quota monitoring
- [ ] `google-cloud-billing>=1.0.0` for GCP billing info
- [ ] `snowflake-connector-python>=3.6.0` for Snowflake

**Estimated Effort:** 15 minutes

#### TODO 1.3: Create Connection Lifecycle Management Module (NEW - ARCHITECT REQUIRED)
**File:** `backend/mcp_servers/lifecycle.py`
**Description:** Shared signal handlers and connection pool management utilities

**Implementation:**
```python
#!/usr/bin/env python3
"""
Connection Lifecycle Management for MCP Servers

Provides:
- Signal handlers for graceful shutdown (SIGTERM, SIGINT)
- Lazy connection pool initialization pattern
- Cleanup registry for multiple resources
"""
import asyncio
import signal
import sys
from typing import Callable, List, Awaitable

_cleanup_handlers: List[Callable[[], Awaitable[None]]] = []

def register_cleanup(handler: Callable[[], Awaitable[None]]) -> None:
    """Register a cleanup handler to be called on shutdown"""
    _cleanup_handlers.append(handler)

async def run_cleanup() -> None:
    """Execute all registered cleanup handlers"""
    for handler in _cleanup_handlers:
        try:
            await handler()
        except Exception as e:
            print(f"Cleanup error: {e}", file=sys.stderr)
    print("All cleanup handlers executed", file=sys.stderr)

def setup_signal_handlers() -> None:
    """Setup SIGTERM/SIGINT handlers for graceful shutdown"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.get_event_loop()

    def handle_signal():
        asyncio.create_task(run_cleanup())

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            signal.signal(sig, lambda s, f: asyncio.create_task(run_cleanup()))

def log_startup(server_name: str) -> None:
    """Log server startup to stderr (stdout reserved for MCP protocol)"""
    print(f"{server_name} running on stdio", file=sys.stderr)

def log_error(message: str) -> None:
    """Log error to stderr"""
    print(f"ERROR: {message}", file=sys.stderr)
```

**Acceptance Criteria:**
- [ ] `register_cleanup()` function for registering async cleanup handlers
- [ ] `run_cleanup()` function that executes all handlers
- [ ] `setup_signal_handlers()` for SIGTERM/SIGINT handling
- [ ] `log_startup()` and `log_error()` helpers (stderr only)
- [ ] Cross-platform support (Windows fallback for signal handling)

**Estimated Effort:** 30 minutes

---

### Phase 2: Database Servers (Priority - Most Used)

#### TODO 2.1: Implement PostgreSQL MCP Server in Python
**File:** `backend/mcp_servers/postgres_server.py`
**Description:** Port postgres_server.js to Python using FastMCP

**Implementation Pattern (ARCHITECT APPROVED):**
```python
#!/usr/bin/env python3
"""
PostgreSQL MCP Server

MCP 서버로 PostgreSQL 데이터베이스에 연결하고 쿼리를 실행합니다.
"""
import asyncio
import json
import os
import sys
from mcp.server.fastmcp import FastMCP
import asyncpg
from dotenv import load_dotenv

from lifecycle import setup_signal_handlers, register_cleanup, log_startup

load_dotenv()

mcp = FastMCP("postgres-mcp-server")
_pool = None

async def get_pool():
    """Lazy connection pool initialization"""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            min_size=1,
            max_size=10,
        )
        register_cleanup(cleanup_pool)
    return _pool

async def cleanup_pool():
    """Close connection pool on shutdown"""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None

@mcp.tool()
async def query(sql: str) -> str:
    """Execute a read-only SQL query on PostgreSQL database"""
    # Security: SELECT only
    if not sql.strip().lower().startswith('select'):
        raise ValueError("Only SELECT queries are allowed")

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql)
        return json.dumps({
            "rows": [dict(r) for r in rows],
            "rowCount": len(rows)
        }, indent=2)

@mcp.tool()
async def list_tables() -> str:
    """List all tables in the current PostgreSQL database"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        return json.dumps([r['table_name'] for r in rows], indent=2)

@mcp.tool()
async def describe_table(table_name: str) -> str:
    """Get schema information for a specific table"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = $1
            ORDER BY ordinal_position
        """, table_name)
        return json.dumps([dict(r) for r in rows], indent=2)

if __name__ == "__main__":
    setup_signal_handlers()
    log_startup("PostgreSQL MCP Server")
    mcp.run(transport="stdio")
```

**Acceptance Criteria:**
- [ ] 3 tools: query, list_tables, describe_table
- [ ] Lazy connection pool using `asyncpg`
- [ ] Environment variable configuration
- [ ] SELECT-only validation using `raise ValueError()` (NOT manual isError)
- [ ] JSON output format matching JS version exactly
- [ ] Signal handlers for graceful shutdown
- [ ] Cleanup handler registered for pool

**Estimated Effort:** 1 hour

#### TODO 2.2: Implement MySQL MCP Server in Python (CRITIC UPDATED - COMPLETE IMPLEMENTATION)
**File:** `backend/mcp_servers/mysql_server.py`
**Description:** Port mysql_server.js to Python using FastMCP

**Complete Implementation Pattern (CRITIC APPROVED):**
```python
#!/usr/bin/env python3
"""
MySQL MCP Server

MCP 서버로 MySQL 데이터베이스에 연결하고 쿼리를 실행합니다.
"""
import asyncio
import json
import os
import sys
from mcp.server.fastmcp import FastMCP
import aiomysql
from dotenv import load_dotenv

from lifecycle import setup_signal_handlers, register_cleanup, log_startup

load_dotenv()

mcp = FastMCP("mysql-mcp-server")
_pool = None

async def get_pool():
    """Lazy connection pool initialization for MySQL"""
    global _pool
    if _pool is None:
        _pool = await aiomysql.create_pool(
            host=os.getenv("MYSQL_HOST", "localhost"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            db=os.getenv("MYSQL_DATABASE"),
            minsize=2,
            maxsize=10,
            autocommit=True,
            charset='utf8mb4'
        )
        register_cleanup(cleanup_pool)
    return _pool

async def cleanup_pool():
    """Close connection pool on shutdown"""
    global _pool
    if _pool:
        _pool.close()
        await _pool.wait_closed()
        _pool = None

@mcp.tool()
async def query(sql: str) -> str:
    """Execute a read-only SQL query on MySQL database"""
    # Security: SELECT only
    if not sql.strip().lower().startswith('select'):
        raise ValueError("Only SELECT queries are allowed")

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(sql)
            rows = await cursor.fetchall()
            return json.dumps({
                "rows": rows,
                "rowCount": len(rows)
            }, indent=2, default=str)  # default=str handles datetime, Decimal, etc.

@mcp.tool()
async def list_tables() -> str:
    """List all tables in the current MySQL database"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SHOW TABLES")
            rows = await cursor.fetchall()
            # SHOW TABLES returns tuples like ('table_name',)
            table_names = [row[0] for row in rows]
            return json.dumps(table_names, indent=2)

@mcp.tool()
async def describe_table(table_name: str) -> str:
    """Get schema information for a specific table

    NOTE: MySQL DESCRIBE returns different columns than PostgreSQL information_schema:
    - Field: column name
    - Type: data type with size (e.g., 'varchar(255)')
    - Null: 'YES' or 'NO'
    - Key: 'PRI', 'UNI', 'MUL', or ''
    - Default: default value or None
    - Extra: additional info (e.g., 'auto_increment')
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # Use backticks for table name to handle reserved words
            await cursor.execute(f"DESCRIBE `{table_name}`")
            rows = await cursor.fetchall()
            # DESCRIBE returns: (Field, Type, Null, Key, Default, Extra)
            columns = ['Field', 'Type', 'Null', 'Key', 'Default', 'Extra']
            result = [dict(zip(columns, row)) for row in rows]
            return json.dumps(result, indent=2, default=str)

if __name__ == "__main__":
    setup_signal_handlers()
    log_startup("MySQL MCP Server")
    mcp.run(transport="stdio")
```

**Key Differences from PostgreSQL:**
| Aspect | PostgreSQL | MySQL |
|--------|------------|-------|
| Pool creation | `asyncpg.create_pool()` | `aiomysql.create_pool()` |
| Cursor type | N/A (asyncpg returns dicts) | `aiomysql.DictCursor` for query |
| Table listing | `information_schema.tables` | `SHOW TABLES` |
| Describe table | `information_schema.columns` | `DESCRIBE table_name` |
| Output columns | column_name, data_type, is_nullable, column_default | Field, Type, Null, Key, Default, Extra |
| Identifier escape | `$1` parameter | Backticks for table names |
| Pool close | `await pool.close()` | `pool.close(); await pool.wait_closed()` |

**Acceptance Criteria:**
- [ ] 3 tools: query, list_tables, describe_table
- [ ] Lazy connection pool using `aiomysql.create_pool()`
- [ ] `aiomysql.DictCursor` for query results
- [ ] `SHOW TABLES` for list_tables (NOT information_schema)
- [ ] `DESCRIBE table_name` for describe_table (NOT information_schema)
- [ ] Backtick escaping for table names
- [ ] `default=str` in json.dumps for MySQL types (datetime, Decimal)
- [ ] SELECT-only validation using `raise ValueError()`
- [ ] Signal handlers and cleanup registration

**Estimated Effort:** 1 hour

---

### Phase 3: Utility Servers

#### TODO 3.1: Implement Excel MCP Server in Python (CRITIC UPDATED - COMPLETE IMPLEMENTATION)
**File:** `backend/mcp_servers/excel_server.py`
**Description:** Port excel_server.js to Python using FastMCP

**Complete Implementation Pattern (CRITIC APPROVED):**
```python
#!/usr/bin/env python3
"""
Excel MCP Server

MCP 서버로 Excel 파일을 읽고 쓰기를 수행합니다.
"""
import json
import os
import sys
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter, column_index_from_string

from lifecycle import setup_signal_handlers, log_startup

mcp = FastMCP("excel-mcp-server")


def parse_range(range_str: str) -> tuple:
    """Parse Excel range string like 'A1:D10' into (start_row, start_col, end_row, end_col)"""
    if ':' not in range_str:
        raise ValueError(f"Invalid range format: {range_str}. Expected format: 'A1:D10'")

    start, end = range_str.split(':')

    # Parse start cell (e.g., 'A1' -> col='A', row=1)
    start_col_str = ''.join(c for c in start if c.isalpha())
    start_row = int(''.join(c for c in start if c.isdigit()))
    start_col = column_index_from_string(start_col_str)

    # Parse end cell
    end_col_str = ''.join(c for c in end if c.isalpha())
    end_row = int(''.join(c for c in end if c.isdigit()))
    end_col = column_index_from_string(end_col_str)

    return (start_row, start_col, end_row, end_col)


@mcp.tool()
def read_excel(file_path: str, sheet_name: str = None, range: str = None) -> str:
    """Read data from an Excel file

    Args:
        file_path: Path to the Excel file
        sheet_name: Name of the sheet to read (optional, defaults to first sheet)
        range: Cell range to read (e.g., 'A1:D10', optional)

    Returns:
        JSON with sheet name, rows data, and row count
    """
    # Validate file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # Load workbook
    wb = load_workbook(filename=file_path, read_only=True, data_only=True)

    # Select sheet
    if sheet_name:
        if sheet_name not in wb.sheetnames:
            raise ValueError(f"Sheet not found: {sheet_name}. Available: {wb.sheetnames}")
        ws = wb[sheet_name]
    else:
        ws = wb.active
        sheet_name = ws.title

    # Read data
    if range:
        start_row, start_col, end_row, end_col = parse_range(range)

        # Get headers from first row of range
        headers = []
        for col in range(start_col, end_col + 1):
            cell_value = ws.cell(row=start_row, column=col).value
            headers.append(str(cell_value) if cell_value is not None else f"Column{col}")

        # Read data rows
        rows = []
        for row in range(start_row + 1, end_row + 1):
            row_data = {}
            for col_idx, col in enumerate(range(start_col, end_col + 1)):
                cell_value = ws.cell(row=row, column=col).value
                row_data[headers[col_idx]] = cell_value
            rows.append(row_data)
    else:
        # Read all data - first row as headers
        data = list(ws.iter_rows(values_only=True))
        if not data:
            rows = []
        else:
            headers = [str(h) if h is not None else f"Column{i}" for i, h in enumerate(data[0])]
            rows = [dict(zip(headers, row)) for row in data[1:]]

    wb.close()

    return json.dumps({
        "sheet": sheet_name,
        "rows": rows,
        "rowCount": len(rows)
    }, indent=2, default=str)


@mcp.tool()
def list_sheets(file_path: str) -> str:
    """List all sheet names in an Excel file

    Args:
        file_path: Path to the Excel file

    Returns:
        JSON array of sheet names
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    wb = load_workbook(filename=file_path, read_only=True)
    sheet_names = wb.sheetnames
    wb.close()

    return json.dumps(sheet_names, indent=2)


@mcp.tool()
def write_excel(file_path: str, data: list, sheet_name: str = "Sheet1") -> str:
    """Write data to an Excel file

    Args:
        file_path: Path to save the Excel file
        data: Array of objects to write as rows (first row keys become headers)
        sheet_name: Name of the sheet (optional, defaults to 'Sheet1')

    Returns:
        JSON with success message, file path, and row count
    """
    # Validate data
    if not isinstance(data, list) or len(data) == 0:
        raise ValueError("Data must be a non-empty array")

    # Create directory if it doesn't exist
    dir_path = os.path.dirname(file_path)
    if dir_path:
        Path(dir_path).mkdir(parents=True, exist_ok=True)

    # Create workbook
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name

    # Get headers from first row's keys
    if isinstance(data[0], dict):
        headers = list(data[0].keys())
    else:
        raise ValueError("Data items must be objects/dictionaries")

    # Write headers
    for col_idx, header in enumerate(headers, start=1):
        ws.cell(row=1, column=col_idx, value=header)

    # Write data rows
    for row_idx, row_data in enumerate(data, start=2):
        for col_idx, header in enumerate(headers, start=1):
            value = row_data.get(header)
            ws.cell(row=row_idx, column=col_idx, value=value)

    # Save file
    wb.save(file_path)
    wb.close()

    return json.dumps({
        "message": "Excel file written successfully",
        "file_path": file_path,
        "rowCount": len(data)
    }, indent=2)


if __name__ == "__main__":
    setup_signal_handlers()
    log_startup("Excel MCP Server")
    mcp.run(transport="stdio")
```

**Key Implementation Details:**
| Feature | Implementation |
|---------|----------------|
| Range parsing | `parse_range()` converts 'A1:D10' to row/col indices |
| Cell reference | `column_index_from_string()` from openpyxl.utils |
| Read mode | `read_only=True, data_only=True` for performance |
| Headers | First row becomes dict keys |
| Write mode | Creates directories with `Path.mkdir(parents=True)` |
| JSON serialization | `default=str` for dates and special types |

**Acceptance Criteria:**
- [ ] 3 tools: read_excel, list_sheets, write_excel
- [ ] Range parsing with `parse_range()` function
- [ ] File existence validation with `raise FileNotFoundError()`
- [ ] Sheet name validation with `raise ValueError()`
- [ ] Directory creation for write operations
- [ ] JSON output format matching JS version
- [ ] `default=str` for handling Excel date/time types

**Estimated Effort:** 45 minutes

---

### Phase 4: Cloud Servers

#### TODO 4.1: Implement BigQuery MCP Server in Python
**File:** `backend/mcp_servers/bigquery_server.py`
**Description:** Port bigquery_server.js to Python using FastMCP

**Implementation Notes:**
- Use `google-cloud-bigquery` library
- Client is lazy-initialized per-call (no persistent pool needed)
- Project ID and location from parameters

**Acceptance Criteria:**
- [ ] 3 tools: query, list_datasets, list_tables
- [ ] Project ID configuration via parameter
- [ ] Location parameter support
- [ ] JSON output format matching JS version
- [ ] Use exceptions for errors

**Estimated Effort:** 1 hour

#### TODO 4.2: Implement Snowflake MCP Server in Python (CRITIC UPDATED - SYNC WRAPPER PATTERN)
**File:** `backend/mcp_servers/snowflake_server.py`
**Description:** Port snowflake_server.js to Python using FastMCP

**CRITICAL: Snowflake connector is SYNCHRONOUS - must use asyncio.to_thread()**

**Complete Implementation Pattern (CRITIC APPROVED):**
```python
#!/usr/bin/env python3
"""
Snowflake MCP Server

MCP 서버로 Snowflake 데이터 웨어하우스에 연결하고 쿼리를 실행합니다.

IMPORTANT: snowflake-connector-python is a SYNCHRONOUS library.
All database operations are wrapped with asyncio.to_thread() to avoid blocking.
"""
import asyncio
import json
import os
import sys
from functools import partial
from mcp.server.fastmcp import FastMCP
import snowflake.connector
from dotenv import load_dotenv

from lifecycle import setup_signal_handlers, register_cleanup, log_startup

load_dotenv()

mcp = FastMCP("snowflake-mcp-server")
_conn = None


def get_sync_connection():
    """Get or create synchronous Snowflake connection (called from thread)"""
    global _conn
    if _conn is None or _conn.is_closed():
        _conn = snowflake.connector.connect(
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
            database=os.getenv("SNOWFLAKE_DATABASE"),
            schema=os.getenv("SNOWFLAKE_SCHEMA"),
            role=os.getenv("SNOWFLAKE_ROLE"),
        )
    return _conn


def _execute_sync(sql: str) -> list:
    """Execute SQL synchronously (called from thread pool)"""
    conn = get_sync_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    finally:
        cursor.close()


def _list_tables_sync(database: str, schema: str) -> list:
    """List tables synchronously (called from thread pool)"""
    conn = get_sync_connection()
    cursor = conn.cursor()
    try:
        sql = f"""
            SELECT TABLE_NAME
            FROM {database}.INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = '{schema}'
        """
        cursor.execute(sql)
        rows = cursor.fetchall()
        return [row[0] for row in rows]
    finally:
        cursor.close()


def _close_sync():
    """Close connection synchronously (called from thread pool)"""
    global _conn
    if _conn and not _conn.is_closed():
        _conn.close()
        _conn = None


async def cleanup_connection():
    """Close Snowflake connection on shutdown"""
    await asyncio.to_thread(_close_sync)


@mcp.tool()
async def query(
    sql: str,
    account: str = None,
    username: str = None,
    password: str = None,
    warehouse: str = None,
    database: str = None,
    schema: str = None,
    role: str = None
) -> str:
    """Execute a Snowflake SQL query

    Args:
        sql: The SQL query to execute
        account: Snowflake account (optional, uses env var if not provided)
        username: Snowflake username (optional)
        password: Snowflake password (optional)
        warehouse: Snowflake warehouse (optional)
        database: Snowflake database (optional)
        schema: Snowflake schema (optional)
        role: Snowflake role (optional)
    """
    # Security: SELECT only
    if not sql.strip().lower().startswith('select'):
        raise ValueError("Only SELECT queries are allowed")

    # Override env vars with parameters if provided
    if account:
        os.environ["SNOWFLAKE_ACCOUNT"] = account
    if username:
        os.environ["SNOWFLAKE_USER"] = username
    if password:
        os.environ["SNOWFLAKE_PASSWORD"] = password
    if warehouse:
        os.environ["SNOWFLAKE_WAREHOUSE"] = warehouse
    if database:
        os.environ["SNOWFLAKE_DATABASE"] = database
    if schema:
        os.environ["SNOWFLAKE_SCHEMA"] = schema
    if role:
        os.environ["SNOWFLAKE_ROLE"] = role

    # Run synchronous query in thread pool to avoid blocking
    result = await asyncio.to_thread(_execute_sync, sql)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def list_tables(
    account: str = None,
    username: str = None,
    password: str = None,
    database: str = None,
    schema: str = None
) -> str:
    """List tables in a Snowflake schema

    Args:
        account: Snowflake account
        username: Snowflake username
        password: Snowflake password
        database: Database name
        schema: Schema name
    """
    # Override env vars with parameters if provided
    if account:
        os.environ["SNOWFLAKE_ACCOUNT"] = account
    if username:
        os.environ["SNOWFLAKE_USER"] = username
    if password:
        os.environ["SNOWFLAKE_PASSWORD"] = password

    db = database or os.getenv("SNOWFLAKE_DATABASE")
    sch = schema or os.getenv("SNOWFLAKE_SCHEMA")

    if not db or not sch:
        raise ValueError("database and schema are required")

    # Run synchronous query in thread pool
    result = await asyncio.to_thread(_list_tables_sync, db, sch)
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    register_cleanup(cleanup_connection)
    setup_signal_handlers()
    log_startup("Snowflake MCP Server")
    mcp.run(transport="stdio")
```

**Key Pattern: Wrapping Synchronous Code**
```python
# Pattern 1: Using asyncio.to_thread (Python 3.9+)
result = await asyncio.to_thread(sync_function, arg1, arg2)

# Pattern 2: Using run_in_executor (Python 3.7+)
loop = asyncio.get_event_loop()
result = await loop.run_in_executor(None, partial(sync_function, arg1, arg2))
```

**Why asyncio.to_thread is Required:**
| Issue | Without Wrapper | With Wrapper |
|-------|-----------------|--------------|
| Blocking | Blocks entire event loop | Runs in thread pool |
| Concurrency | One request at a time | Multiple concurrent requests |
| MCP Protocol | May timeout on long queries | Remains responsive |

**Acceptance Criteria:**
- [ ] 2 tools: query, list_tables
- [ ] `asyncio.to_thread()` for ALL synchronous Snowflake operations
- [ ] Lazy connection initialization
- [ ] Parameter-based credential override (matching JS server)
- [ ] SELECT-only validation
- [ ] Proper connection close in cleanup
- [ ] JSON output format matching JS version

**Estimated Effort:** 1 hour

#### TODO 4.3: Implement GCP Manager MCP Server in Python
**File:** `backend/mcp_servers/gcp_manager_server.py`
**Description:** Port gcp_manager_server.js to Python using FastMCP

**Implementation Notes:**
- Use `google-cloud-monitoring` and `google-cloud-billing` libraries
- Clients can be module-level (no credentials in parameters)

**Acceptance Criteria:**
- [ ] 2 tools: get_quota_usage, get_billing_info
- [ ] Project ID parameter support
- [ ] Time series query for last hour
- [ ] JSON output format matching JS version

**Estimated Effort:** 1 hour

---

### Phase 5: Integration Updates

#### TODO 5.1: Update MCP Client for Python Server Support
**File:** `backend/agents/data_source/mcp_client.py`
**Description:** Modify MCPClient to support both Python and Node.js servers

**Changes Required (ARCHITECT APPROVED):**
```python
import sys
import os

class MCPClient:
    def __init__(self, server_path: str, args: List[str] = None, env: Dict[str, str] = None):
        # Detect server type by extension
        if server_path.endswith('.py'):
            command = sys.executable  # Use same Python interpreter as client
            server_env = {
                **os.environ,
                "PYTHONUNBUFFERED": "1",      # Critical for stdio
                "PYTHONIOENCODING": "utf-8",  # Critical for encoding
                **(env or {})
            }
        else:
            command = "node"
            server_env = {**os.environ, **(env or {})}

        self.server_parameters = StdioServerParameters(
            command=command,
            args=[server_path] + (args or []),
            env=server_env
        )
        # ... rest of init
```

**Acceptance Criteria:**
- [ ] Auto-detect `.py` vs `.js` server files
- [ ] Use `sys.executable` for Python servers (NOT hardcoded "python")
- [ ] Set `PYTHONUNBUFFERED=1` for Python servers
- [ ] Set `PYTHONIOENCODING=utf-8` for Python servers
- [ ] Backward compatible with existing JS servers

**Estimated Effort:** 30 minutes

#### TODO 5.2: Update MCP Bridge for Python Servers
**File:** `backend/mcp_bridge.py`
**Description:** Add Python server paths alongside JS paths

**Changes Required:**
```python
# Python servers (default)
server_paths = {
    "postgres": os.path.join(project_root, "backend/mcp_servers/postgres_server.py"),
    "mysql": os.path.join(project_root, "backend/mcp_servers/mysql_server.py"),
    "excel": os.path.join(project_root, "backend/mcp_servers/excel_server.py"),
}

# Optional: JS fallback paths
server_paths_js = {
    "postgres": os.path.join(project_root, "backend/mcp_servers/postgres_server.js"),
    "mysql": os.path.join(project_root, "backend/mcp_servers/mysql_server.js"),
    "excel": os.path.join(project_root, "backend/mcp_servers/excel_server.js"),
}
```

**Acceptance Criteria:**
- [ ] Add Python server path mapping (primary)
- [ ] Keep JS server paths as fallback option
- [ ] Default to Python servers
- [ ] Environment variable to force JS servers if needed

**Estimated Effort:** 30 minutes

#### TODO 5.3: Update package.json Scripts
**File:** `package.json`
**Description:** Add npm scripts for running Python MCP servers

**Changes:**
```json
{
  "scripts": {
    "mcp:postgres": "python backend/mcp_servers/postgres_server.py",
    "mcp:postgres:js": "node backend/mcp_servers/postgres_server.js",
    "mcp:mysql": "python backend/mcp_servers/mysql_server.py",
    "mcp:mysql:js": "node backend/mcp_servers/mysql_server.js",
    "mcp:excel": "python backend/mcp_servers/excel_server.py",
    "mcp:excel:js": "node backend/mcp_servers/excel_server.js",
    "mcp:bigquery": "python backend/mcp_servers/bigquery_server.py",
    "mcp:bigquery:js": "node backend/mcp_servers/bigquery_server.js",
    "mcp:snowflake": "python backend/mcp_servers/snowflake_server.py",
    "mcp:snowflake:js": "node backend/mcp_servers/snowflake_server.js",
    "mcp:gcp": "python backend/mcp_servers/gcp_manager_server.py",
    "mcp:gcp:js": "node backend/mcp_servers/gcp_manager_server.js"
  }
}
```

**Acceptance Criteria:**
- [ ] Python scripts as default (no suffix)
- [ ] JS scripts with `:js` suffix for backward compatibility
- [ ] All 6 servers covered

**Estimated Effort:** 15 minutes

---

### Phase 6: Testing and Documentation

#### TODO 6.1: Create MCP Server Test Suite (CRITIC UPDATED - WITH OUTPUT SCHEMAS)
**File:** `backend/tests/test_mcp_servers.py`
**Description:** Comprehensive tests for all Python MCP servers with output format validation

**Expected Output Schemas (CRITIC REQUIRED):**
```python
"""
Expected JSON output schemas for each tool.
Used for automated format validation against JavaScript server outputs.
"""

EXPECTED_SCHEMAS = {
    # PostgreSQL Server
    "postgres.query": {
        "type": "object",
        "properties": {
            "rows": {"type": "array", "items": {"type": "object"}},
            "rowCount": {"type": "integer"}
        },
        "required": ["rows", "rowCount"]
    },
    "postgres.list_tables": {
        "type": "array",
        "items": {"type": "string"}
    },
    "postgres.describe_table": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "column_name": {"type": "string"},
                "data_type": {"type": "string"},
                "is_nullable": {"type": "string"},  # 'YES' or 'NO'
                "column_default": {"type": ["string", "null"]}
            },
            "required": ["column_name", "data_type", "is_nullable"]
        }
    },

    # MySQL Server (DIFFERENT from PostgreSQL!)
    "mysql.query": {
        "type": "object",
        "properties": {
            "rows": {"type": "array", "items": {"type": "object"}},
            "rowCount": {"type": "integer"}
        },
        "required": ["rows", "rowCount"]
    },
    "mysql.list_tables": {
        "type": "array",
        "items": {"type": "string"}
    },
    "mysql.describe_table": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "Field": {"type": "string"},
                "Type": {"type": "string"},
                "Null": {"type": "string"},  # 'YES' or 'NO'
                "Key": {"type": "string"},   # 'PRI', 'UNI', 'MUL', ''
                "Default": {"type": ["string", "null"]},
                "Extra": {"type": "string"}  # 'auto_increment', etc.
            },
            "required": ["Field", "Type", "Null", "Key", "Extra"]
        }
    },

    # Excel Server
    "excel.read_excel": {
        "type": "object",
        "properties": {
            "sheet": {"type": "string"},
            "rows": {"type": "array", "items": {"type": "object"}},
            "rowCount": {"type": "integer"}
        },
        "required": ["sheet", "rows", "rowCount"]
    },
    "excel.list_sheets": {
        "type": "array",
        "items": {"type": "string"}
    },
    "excel.write_excel": {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "file_path": {"type": "string"},
            "rowCount": {"type": "integer"}
        },
        "required": ["message", "file_path", "rowCount"]
    },

    # BigQuery Server
    "bigquery.query": {
        "type": "array",
        "items": {"type": "object"}
    },
    "bigquery.list_datasets": {
        "type": "array",
        "items": {"type": "string"}
    },
    "bigquery.list_tables": {
        "type": "array",
        "items": {"type": "string"}
    },

    # Snowflake Server
    "snowflake.query": {
        "type": "array",
        "items": {"type": "object"}
    },
    "snowflake.list_tables": {
        "type": "array",
        "items": {"type": "string"}
    },

    # GCP Manager Server
    "gcp_manager.get_quota_usage": {
        "type": "object",
        "properties": {
            "service": {"type": "string"},
            "usageData": {"type": "array"},
            "message": {"type": "string"}
        },
        "required": ["service", "usageData"]
    },
    "gcp_manager.get_billing_info": {
        "type": "object"
        # Flexible structure based on GCP Billing API response
    }
}
```

**Test Implementation Pattern:**
```python
import pytest
import json
from jsonschema import validate, ValidationError

@pytest.mark.asyncio
async def test_postgres_query_output_format():
    """Verify PostgreSQL query output matches expected schema"""
    client = MCPClient("backend/mcp_servers/postgres_server.py")
    await client.connect()

    result = await client.call_tool("query", {"sql": "SELECT 1 as test"})
    data = json.loads(result.content[0].text)

    # Validate against expected schema
    validate(instance=data, schema=EXPECTED_SCHEMAS["postgres.query"])

    await client.disconnect()

@pytest.mark.asyncio
async def test_mysql_describe_differs_from_postgres():
    """Verify MySQL describe_table has DIFFERENT columns than PostgreSQL"""
    # MySQL uses: Field, Type, Null, Key, Default, Extra
    # PostgreSQL uses: column_name, data_type, is_nullable, column_default

    mysql_client = MCPClient("backend/mcp_servers/mysql_server.py")
    await mysql_client.connect()
    result = await mysql_client.call_tool("describe_table", {"table_name": "users"})
    data = json.loads(result.content[0].text)

    # Must have MySQL-specific columns
    assert "Field" in data[0], "MySQL should return 'Field', not 'column_name'"
    assert "Key" in data[0], "MySQL should return 'Key' column"

    await mysql_client.disconnect()
```

**Test Cases:**
- Tool listing verification (compare with JS server output)
- Tool execution with valid input
- Tool execution with invalid input (verify exception -> isError)
- **Output format validation (JSON structure matches schema)**
- **MySQL vs PostgreSQL schema difference verification**
- Graceful shutdown test (send SIGTERM, verify cleanup)

**Acceptance Criteria:**
- [ ] `EXPECTED_SCHEMAS` dictionary for ALL tools
- [ ] jsonschema validation in tests
- [ ] Test MySQL describe_table differs from PostgreSQL
- [ ] Test each server's tool listing
- [ ] Test each tool's execution
- [ ] Error case coverage (verify isError: true in response)
- [ ] Signal handling / graceful shutdown test

**Estimated Effort:** 2 hours

#### TODO 6.2: Update Documentation
**File:** `docs/mcp-servers.md` (new)
**Description:** Document Python MCP server usage

**Content:**
- Migration rationale (Python vs JS)
- Environment variables required
- Running Python servers
- Error handling pattern (exceptions -> isError)
- Troubleshooting (PYTHONUNBUFFERED, encoding issues)

**Acceptance Criteria:**
- [ ] Installation instructions
- [ ] Environment variable reference
- [ ] Configuration examples
- [ ] Troubleshooting section for common stdio issues

**Estimated Effort:** 1 hour

---

## Commit Strategy

| Phase | Commit Message |
|-------|----------------|
| 1 | `feat(mcp): add Python MCP server foundation with lifecycle management` |
| 2 | `feat(mcp): implement PostgreSQL and MySQL servers in Python` |
| 3 | `feat(mcp): implement Excel server in Python` |
| 4 | `feat(mcp): implement BigQuery, Snowflake, and GCP Manager servers in Python` |
| 5 | `refactor(mcp): update client and bridge for Python server support` |
| 6 | `test(mcp): add comprehensive MCP server test suite` |
| Final | `docs(mcp): add Python MCP server migration documentation` |

---

## Success Criteria

### Functional Success
- [ ] All 6 Python MCP servers respond to `list_tools` requests
- [ ] All tools execute correctly with valid inputs
- [ ] **Exceptions automatically convert to `isError: true` responses**
- [ ] Output JSON structure matches JavaScript versions exactly
- [ ] **MySQL describe_table returns Field/Type/Null/Key (NOT column_name/data_type)**

### Integration Success
- [ ] `MCPClient` connects to Python servers using `sys.executable`
- [ ] `mcp_bridge.py` defaults to Python server paths
- [ ] npm scripts execute Python servers correctly
- [ ] **PYTHONUNBUFFERED=1 is set for all Python server processes**

### Performance Success
- [ ] Server startup time < 2 seconds
- [ ] Tool execution time comparable to JS versions
- [ ] No memory leaks in long-running connections
- [ ] **Graceful shutdown completes within 5 seconds on SIGTERM**
- [ ] **Snowflake queries don't block event loop (asyncio.to_thread working)**

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| SDK version incompatibility | Low | High | Pin `mcp>=1.23.0`, test early |
| Output format mismatch | Medium | Medium | Create comparison tests vs JS servers |
| Missing Python libraries | Low | Low | Check requirements.txt early |
| Performance regression | Low | Medium | Benchmark before/after |
| **Stdio buffering issues** | Medium | High | **Always set PYTHONUNBUFFERED=1** |
| **Signal handler not working** | Low | Medium | **Test on both Unix and Windows** |
| **Snowflake blocking event loop** | Medium | High | **Use asyncio.to_thread() for all sync ops** |

---

## Estimated Total Effort

| Phase | Effort |
|-------|--------|
| Phase 1: Foundation | 1 hour 5 minutes |
| Phase 2: Database Servers | 2 hours |
| Phase 3: Utility Servers | 45 minutes |
| Phase 4: Cloud Servers | 3 hours |
| Phase 5: Integration | 1 hour 15 minutes |
| Phase 6: Testing & Docs | 3 hours |
| **Total** | **~12 hours** |

---

## Migration Sequence Recommendation

For minimal risk, migrate in this order:

1. **Foundation + Lifecycle Module** (required by all servers)
2. **Excel Server** (simplest, no external service dependencies)
3. **PostgreSQL Server** (most commonly used, good test case)
4. **MySQL Server** (similar to PostgreSQL but different output schemas)
5. **BigQuery Server** (cloud, but well-documented Python SDK)
6. **GCP Manager Server** (low complexity)
7. **Snowflake Server** (synchronous library, requires async wrapper)

---

## Critical Implementation Notes (ARCHITECT + CRITIC APPROVED)

### Error Handling Pattern
```python
# WRONG - Do NOT do this:
return json.dumps({"error": "Only SELECT queries are allowed", "isError": True})

# CORRECT - FastMCP handles isError automatically:
raise ValueError("Only SELECT queries are allowed")
```

### Environment Variables for Python Servers
```python
# In mcp_client.py - CRITICAL for stdio to work:
server_env = {
    "PYTHONUNBUFFERED": "1",      # Prevents stdout buffering
    "PYTHONIOENCODING": "utf-8",  # Ensures proper encoding
}
```

### Python Interpreter Selection
```python
# WRONG - Do NOT hardcode:
command = "python"

# CORRECT - Use same interpreter as client:
command = sys.executable
```

### Connection Pool Lifecycle
```python
# CORRECT - Lazy initialization with cleanup registration:
_pool = None

async def get_pool():
    global _pool
    if _pool is None:
        _pool = await create_pool(...)
        register_cleanup(cleanup_pool)  # Register for shutdown
    return _pool
```

### Synchronous Library Wrapping (Snowflake)
```python
# CRITICAL - snowflake-connector-python is SYNCHRONOUS
# Must wrap ALL database operations:

# WRONG - Blocks event loop:
result = cursor.execute(sql)

# CORRECT - Run in thread pool:
result = await asyncio.to_thread(_execute_sync, sql)
```

### MySQL vs PostgreSQL describe_table Output
```python
# PostgreSQL output:
[{"column_name": "id", "data_type": "integer", "is_nullable": "NO", "column_default": "nextval(...)"}]

# MySQL output (DIFFERENT!):
[{"Field": "id", "Type": "int(11)", "Null": "NO", "Key": "PRI", "Default": None, "Extra": "auto_increment"}]
```

---

## Notes

- JavaScript servers will NOT be deleted initially - keep for reference and rollback
- Consider adding `MCP_SERVER_LANG=python|node` environment variable for global switching
- The Python MCP SDK's FastMCP is now the recommended approach (incorporated into official SDK)
- Log output MUST go to stderr, not stdout (stdout is reserved for MCP protocol)
- **Minimum SDK version: mcp>=1.23.0** (November 2025 protocol update)
- **Snowflake requires asyncio.to_thread() wrapper** - synchronous library
- **MySQL describe_table has DIFFERENT output schema than PostgreSQL**

---

## References

- [Python MCP SDK GitHub](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Python SDK Documentation](https://modelcontextprotocol.github.io/python-sdk/)
- [FastMCP Guide](https://github.com/jlowin/fastmcp)
- [MCP Protocol Specification](https://modelcontextprotocol.io/docs/develop/build-server)
