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
from mcp.server.fastmcp import FastMCP
import snowflake.connector
from dotenv import load_dotenv

from .lifecycle import setup_signal_handlers, register_cleanup, log_startup

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
