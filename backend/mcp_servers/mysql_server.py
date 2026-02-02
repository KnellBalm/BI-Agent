#!/usr/bin/env python3
"""
MySQL MCP Server

MCP 서버로 MySQL 데이터베이스에 연결하고 쿼리를 실행합니다.
"""
import json
import os
from mcp.server.fastmcp import FastMCP
import aiomysql
from dotenv import load_dotenv

from .lifecycle import setup_signal_handlers, register_cleanup, log_startup

load_dotenv()

mcp = FastMCP("mysql-mcp-server")
_pool = None


async def get_pool():
    """Lazy connection pool initialization for MySQL."""
    global _pool
    if _pool is None:
        _pool = await aiomysql.create_pool(
            host=os.getenv("MYSQL_HOST", "localhost"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            db=os.getenv("MYSQL_DB"),
            minsize=2,
            maxsize=10,
            autocommit=True,
            charset='utf8mb4'
        )
        register_cleanup(cleanup_pool)
    return _pool


async def cleanup_pool():
    """Close connection pool on shutdown."""
    global _pool
    if _pool:
        _pool.close()
        await _pool.wait_closed()
        _pool = None


@mcp.tool()
async def query(sql: str) -> str:
    """Execute a read-only SQL query on MySQL database.

    Args:
        sql: The SQL query to execute (SELECT only)

    Returns:
        JSON string with rows array and rowCount
    """
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
    """List all tables in the current MySQL database.

    Returns:
        JSON array of table names
    """
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
    """Get schema information for a specific table.

    NOTE: MySQL DESCRIBE returns different columns than PostgreSQL information_schema:
    - Field: column name
    - Type: data type with size (e.g., 'varchar(255)')
    - Null: 'YES' or 'NO'
    - Key: 'PRI', 'UNI', 'MUL', or ''
    - Default: default value or None
    - Extra: additional info (e.g., 'auto_increment')

    Args:
        table_name: Name of the table to describe

    Returns:
        JSON array with column information (Field, Type, Null, Key, Default, Extra)
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # Security: Validate table_name against information_schema to prevent SQL injection
            # Though we use backticks, direct validation is safer
            await cursor.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = %s AND table_name = %s",
                (os.getenv("MYSQL_DB"), table_name)
            )
            exists = await cursor.fetchone()
            if not exists:
                raise ValueError(f"Table '{table_name}' not found or access denied")

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
