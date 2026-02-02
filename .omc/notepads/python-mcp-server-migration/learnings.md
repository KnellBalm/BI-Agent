# Learnings - Python MCP Server Migration

## Phase 1: Foundation Setup

### Date: 2026-02-02

#### Successfully Implemented
1. **Base Module (`__init__.py`)**
   - Created common utilities for JSON response formatting
   - Implemented stderr-only logging functions (log_info, log_error, log_warning)
   - Added success_response() and error_response() helpers
   - Documented that error_response() should rarely be used - prefer raising exceptions with FastMCP

2. **Connection Lifecycle Module (`lifecycle.py`)**
   - Implemented cleanup handler registry pattern with `register_cleanup()`
   - Created `setup_signal_handlers()` with SIGTERM/SIGINT support
   - Added Windows fallback for signal handling (NotImplementedError catch)
   - Included `log_startup()` and `log_error()` for stderr logging
   - All cleanup handlers execute sequentially with error isolation

3. **Updated requirements.txt**
   - Upgraded mcp from >=0.1.0 to >=1.23.0 (November 2025 protocol update - CRITICAL)
   - Added async database drivers:
     - asyncpg>=0.29.0 for PostgreSQL
     - aiomysql>=0.2.0 for MySQL
   - Added cloud provider libraries:
     - google-cloud-bigquery>=3.0.0
     - google-cloud-monitoring>=2.0.0
     - google-cloud-billing>=1.0.0
     - snowflake-connector-python>=3.6.0

#### Key Patterns Discovered
- **Stderr-Only Logging**: stdout must remain clean for MCP protocol JSON messages
- **Lazy Cleanup Registration**: Cleanup handlers are registered when resources are created, not at startup
- **Cross-Platform Signal Handling**: Windows requires fallback from add_signal_handler to signal.signal
- **Version Pinning**: mcp>=1.23.0 is mandatory for protocol compatibility

#### Files Created
- `/Users/zokr/python_workspace/BI-Agent/backend/mcp_servers/__init__.py` (1624 bytes)
- `/Users/zokr/python_workspace/BI-Agent/backend/mcp_servers/lifecycle.py` (2173 bytes, executable)

#### Files Modified
- `/Users/zokr/python_workspace/BI-Agent/backend/requirements.txt` (added 9 new dependencies)

#### Next Steps
Phase 1 is complete and ready for verification. The foundation is now in place for implementing the 6 MCP servers in Phases 2-4.

---

## Phase 2: Database Servers

### Date: 2026-02-02

#### Successfully Implemented
1. **PostgreSQL MCP Server (`postgres_server.py`)**
   - 3 tools: query, list_tables, describe_table
   - Lazy connection pool initialization using asyncpg.create_pool()
   - SELECT-only validation using `raise ValueError()` (FastMCP auto-converts to isError)
   - Pool configuration: min_size=1, max_size=10
   - Cleanup handler registered via `register_cleanup(cleanup_pool)`
   - Output format: query returns {rows, rowCount}, list_tables returns array of strings
   - Uses information_schema.tables and information_schema.columns for metadata

2. **MySQL MCP Server (`mysql_server.py`)**
   - 3 tools: query, list_tables, describe_table
   - Lazy connection pool using aiomysql.create_pool()
   - Key MySQL-specific patterns:
     - Uses `MYSQL_DB` environment variable (not MYSQL_DATABASE) for JS parity
     - Uses `aiomysql.DictCursor` for query results to return dict rows
     - Uses `SHOW TABLES` (not information_schema) for list_tables
     - Uses `DESCRIBE table_name` (not information_schema) for describe_table
     - Backtick escaping for table names to handle reserved words
   - Pool cleanup: `pool.close(); await pool.wait_closed()` (two-step process)
   - JSON serialization: `default=str` to handle MySQL datetime and Decimal types
   - Pool configuration: minsize=2, maxsize=10, autocommit=True, charset='utf8mb4'

#### Key Patterns Discovered
- **Database-Specific Metadata Queries**: PostgreSQL uses information_schema, MySQL uses SHOW/DESCRIBE
- **MySQL Pool Cleanup**: Requires two steps (close() then wait_closed()), unlike asyncpg's single close()
- **DictCursor for MySQL**: aiomysql returns tuples by default, must explicitly use DictCursor for dict rows
- **MySQL vs PostgreSQL describe_table Output Schemas**:
  - PostgreSQL: `{column_name, data_type, is_nullable, column_default}`
  - MySQL: `{Field, Type, Null, Key, Default, Extra}` (completely different structure)
- **JSON Serialization**: MySQL needs `default=str` for datetime/Decimal, PostgreSQL asyncpg handles this automatically

#### Files Created
- `/Users/zokr/python_workspace/BI-Agent/backend/mcp_servers/postgres_server.py` (2973 bytes, executable)
- `/Users/zokr/python_workspace/BI-Agent/backend/mcp_servers/mysql_server.py` (3600 bytes, executable)

#### Next Steps
Phase 2 is complete. Both database servers are ready for verification. Tasks #2 (PostgreSQL) and #3 (MySQL) from the plan are ready for testing.
