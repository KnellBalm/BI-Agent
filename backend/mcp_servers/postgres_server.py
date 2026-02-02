#!/usr/bin/env python3
"""
PostgreSQL MCP Server

MCP 서버로 PostgreSQL 데이터베이스에 연결하고 쿼리를 실행합니다.
"""
import json
import os
from mcp.server.fastmcp import FastMCP
import asyncpg
from dotenv import load_dotenv

from .lifecycle import setup_signal_handlers, register_cleanup, log_startup

load_dotenv()

mcp = FastMCP("postgres-mcp-server")
_pool = None


async def get_pool():
    """Lazy connection pool initialization."""
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
    """Close connection pool on shutdown."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


@mcp.tool()
async def query(sql: str) -> str:
    """Execute a read-only SQL query on PostgreSQL database.

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
        rows = await conn.fetch(sql)
        return json.dumps({
            "rows": [dict(r) for r in rows],
            "rowCount": len(rows)
        }, indent=2)


@mcp.tool()
async def list_tables() -> str:
    """List all tables in the current PostgreSQL database.

    Returns:
        JSON array of table names
    """
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
    """Get schema information for a specific table.

    Args:
        table_name: Name of the table to describe

    Returns:
        JSON array with column information (column_name, data_type, is_nullable, column_default)
    """
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
