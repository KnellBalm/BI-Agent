# Phase 3a 신규 연동 도구 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redshift(IAM 인증), Airflow(DAG 관리), Metabase 강화(+4개) 3종 도구를 구현하여 MCP 도구 총 190개를 완성한다.

**Architecture:** 기존 httpx 기반 연동 패턴을 따른다. Redshift는 boto3로 IAM 임시 자격증명을 발급받은 후 psycopg2로 연결한다. 각 모듈은 `_connections` 딕셔너리 캐시와 `[OK]`/`[ERROR]` 반환 형식을 사용한다.

**Tech Stack:** Python 3.11, httpx (Airflow/Metabase), boto3 (Redshift IAM), psycopg2-binary (Redshift SQL), pytest + unittest.mock

---

## 파일 맵

| 파일 | 작업 | 신규 함수 |
|------|------|------|
| `bi_agent_mcp/tools/redshift.py` | 신규 | connect_redshift, run_redshift_query, get_redshift_schema, list_redshift_tables |
| `bi_agent_mcp/tools/airflow.py` | 신규 | connect_airflow, list_airflow_dags, get_dag_status, trigger_dag, get_task_logs, list_dag_runs |
| `bi_agent_mcp/tools/metabase.py` | 수정 | +list_metabase_collections, get_metabase_card_data, refresh_metabase_cache, run_metabase_adhoc_sql |
| `bi_agent_mcp/server.py` | 수정 | 14개 등록 |
| `tests/unit/test_redshift.py` | 신규 | 8개 테스트 |
| `tests/unit/test_airflow.py` | 신규 | 9개 테스트 |
| `tests/unit/test_metabase.py` | 수정 | +5개 테스트 |

---

### Task 1: redshift.py — IAM 인증 기반 Redshift 도구 4개

**Files:**
- Create: `bi_agent_mcp/tools/redshift.py`
- Create: `tests/unit/test_redshift.py`
- Modify: `bi_agent_mcp/server.py`

**패턴 참고:** `bi_agent_mcp/tools/metabase.py` (httpx 패턴), `bi_agent_mcp/tools/db.py` (_validate_select)

- [ ] **Step 1: 실패 테스트 파일 작성**

`tests/unit/test_redshift.py`:

```python
"""bi_agent_mcp.tools.redshift 단위 테스트."""
from unittest.mock import MagicMock, patch, call
import pytest


def _make_boto3_mock(temp_user="IAM:testuser", temp_password="AmazonAWS123"):
    mock_client = MagicMock()
    mock_client.get_cluster_credentials.return_value = {
        "DbUser": temp_user,
        "DbPassword": temp_password,
    }
    return mock_client


def _make_psycopg2_mock():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.description = [("id",), ("name",)]
    mock_cursor.fetchall.return_value = [(1, "Alice"), (2, "Bob")]
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn


# ---------------------------------------------------------------------------
# connect_redshift
# ---------------------------------------------------------------------------

def test_connect_redshift_stores_connection():
    mock_boto = _make_boto3_mock()
    mock_conn = _make_psycopg2_mock()

    with patch("bi_agent_mcp.tools.redshift._redshift_connections", {}) as store, \
         patch("bi_agent_mcp.tools.redshift.boto3.client", return_value=mock_boto), \
         patch("bi_agent_mcp.tools.redshift.psycopg2.connect", return_value=mock_conn):
        from bi_agent_mcp.tools.redshift import connect_redshift
        result = connect_redshift("my-cluster", "mydb", "testuser", "ap-northeast-2", "test")

    assert "[OK]" in result
    assert "test" in result


def test_connect_redshift_iam_failure_returns_error():
    mock_boto = MagicMock()
    mock_boto.get_cluster_credentials.side_effect = Exception("AccessDenied")

    with patch("bi_agent_mcp.tools.redshift.boto3.client", return_value=mock_boto):
        from bi_agent_mcp.tools.redshift import connect_redshift
        result = connect_redshift("bad-cluster", "db", "user")

    assert "[ERROR]" in result
    assert "IAM" in result or "자격증명" in result


# ---------------------------------------------------------------------------
# run_redshift_query
# ---------------------------------------------------------------------------

def test_run_redshift_query_returns_markdown_table():
    mock_boto = _make_boto3_mock()
    mock_conn = _make_psycopg2_mock()
    store = {"test": {"cluster_id": "c", "database": "d", "user": "u", "region": "ap-northeast-2"}}

    with patch("bi_agent_mcp.tools.redshift._redshift_connections", store), \
         patch("bi_agent_mcp.tools.redshift.boto3.client", return_value=mock_boto), \
         patch("bi_agent_mcp.tools.redshift.psycopg2.connect", return_value=mock_conn):
        from bi_agent_mcp.tools.redshift import run_redshift_query
        result = run_redshift_query("test", "SELECT id, name FROM users")

    assert "id" in result
    assert "Alice" in result


def test_run_redshift_query_blocks_dml():
    store = {"test": {"cluster_id": "c", "database": "d", "user": "u", "region": "ap-northeast-2"}}
    with patch("bi_agent_mcp.tools.redshift._redshift_connections", store):
        from bi_agent_mcp.tools.redshift import run_redshift_query
        result = run_redshift_query("test", "DELETE FROM users")

    assert "[ERROR]" in result


def test_run_redshift_query_unknown_conn_id_returns_error():
    with patch("bi_agent_mcp.tools.redshift._redshift_connections", {}):
        from bi_agent_mcp.tools.redshift import run_redshift_query
        result = run_redshift_query("not_exist", "SELECT 1")

    assert "[ERROR]" in result


# ---------------------------------------------------------------------------
# get_redshift_schema
# ---------------------------------------------------------------------------

def test_get_redshift_schema_returns_column_info():
    mock_boto = _make_boto3_mock()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.description = [("table_name",), ("column_name",), ("data_type",)]
    mock_cursor.fetchall.return_value = [
        ("orders", "id", "integer"),
        ("orders", "amount", "numeric"),
    ]
    mock_conn.cursor.return_value = mock_cursor
    store = {"test": {"cluster_id": "c", "database": "d", "user": "u", "region": "ap-northeast-2"}}

    with patch("bi_agent_mcp.tools.redshift._redshift_connections", store), \
         patch("bi_agent_mcp.tools.redshift.boto3.client", return_value=mock_boto), \
         patch("bi_agent_mcp.tools.redshift.psycopg2.connect", return_value=mock_conn):
        from bi_agent_mcp.tools.redshift import get_redshift_schema
        result = get_redshift_schema("test", "public")

    assert "orders" in result
    assert "amount" in result


# ---------------------------------------------------------------------------
# list_redshift_tables
# ---------------------------------------------------------------------------

def test_list_redshift_tables_returns_table_list():
    mock_boto = _make_boto3_mock()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.description = [("schemaname",), ("tablename",), ("tableowner",)]
    mock_cursor.fetchall.return_value = [("public", "orders", "admin"), ("public", "users", "admin")]
    mock_conn.cursor.return_value = mock_cursor
    store = {"test": {"cluster_id": "c", "database": "d", "user": "u", "region": "ap-northeast-2"}}

    with patch("bi_agent_mcp.tools.redshift._redshift_connections", store), \
         patch("bi_agent_mcp.tools.redshift.boto3.client", return_value=mock_boto), \
         patch("bi_agent_mcp.tools.redshift.psycopg2.connect", return_value=mock_conn):
        from bi_agent_mcp.tools.redshift import list_redshift_tables
        result = list_redshift_tables("test")

    assert "orders" in result
    assert "users" in result
```

- [ ] **Step 2: 테스트 실행 — ImportError 확인**

```bash
python3 -m pytest tests/unit/test_redshift.py -q --no-header 2>&1 | head -5
```

예상: `ModuleNotFoundError` 또는 `ImportError` (redshift.py 없음)

- [ ] **Step 3: redshift.py 구현**

`bi_agent_mcp/tools/redshift.py`:

```python
"""[Redshift] AWS IAM 임시 자격증명 기반 Redshift 연동 도구."""
import logging
from typing import Dict

import boto3
import psycopg2

from bi_agent_mcp.tools.db import _validate_select

logger = logging.getLogger(__name__)

_redshift_connections: Dict[str, dict] = {}


def _get_redshift_conn(conn_id: str):
    """IAM 임시 자격증명으로 psycopg2 연결 생성."""
    if conn_id not in _redshift_connections:
        raise ValueError(f"연결 ID '{conn_id}'를 찾을 수 없습니다. connect_redshift()를 먼저 호출하세요.")
    info = _redshift_connections[conn_id]

    client = boto3.client("redshift", region_name=info["region"])
    creds = client.get_cluster_credentials(
        DbUser=info["user"],
        DbName=info["database"],
        ClusterIdentifier=info["cluster_id"],
        DurationSeconds=3600,
        AutoCreate=False,
    )

    host = f"{info['cluster_id']}.{info['region']}.redshift.amazonaws.com"
    return psycopg2.connect(
        host=host,
        port=5439,
        database=info["database"],
        user=creds["DbUser"],
        password=creds["DbPassword"],
    )


def connect_redshift(
    cluster_id: str,
    database: str,
    user: str,
    region: str = "ap-northeast-2",
    conn_id: str = "default",
) -> str:
    """[Redshift] AWS IAM 임시 자격증명으로 Redshift에 연결한다.

    Args:
        cluster_id: Redshift 클러스터 ID (예: "my-cluster", 전체 엔드포인트 아님)
        database: 데이터베이스 이름
        user: IAM 사용자명 (boto3 자격증명 환경 필요)
        region: AWS 리전 (기본값: "ap-northeast-2")
        conn_id: 연결 식별자 (기본값: "default")
    """
    try:
        client = boto3.client("redshift", region_name=region)
        creds = client.get_cluster_credentials(
            DbUser=user,
            DbName=database,
            ClusterIdentifier=cluster_id,
            DurationSeconds=3600,
            AutoCreate=False,
        )
        # 연결 검증
        host = f"{cluster_id}.{region}.redshift.amazonaws.com"
        conn = psycopg2.connect(
            host=host,
            port=5439,
            database=database,
            user=creds["DbUser"],
            password=creds["DbPassword"],
        )
        conn.close()
    except Exception as e:
        return f"[ERROR] Redshift IAM 자격증명 발급 또는 연결 실패: {e}"

    _redshift_connections[conn_id] = {
        "cluster_id": cluster_id,
        "database": database,
        "user": user,
        "region": region,
    }
    return f"[OK] Redshift 연결 완료: {conn_id} ({cluster_id}/{database})"


def run_redshift_query(
    conn_id: str,
    sql: str,
    limit: int = 500,
) -> str:
    """[Redshift] Redshift에 SELECT 쿼리를 실행하고 결과를 마크다운 테이블로 반환한다.

    Args:
        conn_id: 연결 식별자
        sql: SELECT 쿼리 (DML 자동 차단)
        limit: 최대 반환 행 수 (기본값: 500)
    """
    err = _validate_select(sql)
    if err:
        return f"[ERROR] {err}"

    if conn_id not in _redshift_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_redshift()를 먼저 호출하세요."

    try:
        conn = _get_redshift_conn(conn_id)
        try:
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM ({sql}) AS _sub LIMIT {limit}")
            rows = cur.fetchall()
            columns = [d[0] for d in cur.description] if cur.description else []
        finally:
            conn.close()
    except Exception as e:
        return f"[ERROR] 쿼리 실행 실패: {e}"

    if not rows:
        return "결과가 없습니다."

    header = " | ".join(columns)
    sep = " | ".join(["---"] * len(columns))
    body = "\n".join(" | ".join(str(v) for v in row) for row in rows)
    return f"| {header} |\n| {sep} |\n" + "\n".join(f"| {' | '.join(str(v) for v in row)} |" for row in rows)


def get_redshift_schema(
    conn_id: str,
    schema: str = "public",
) -> str:
    """[Redshift] Redshift 스키마의 테이블 및 컬럼 정보를 반환한다.

    Args:
        conn_id: 연결 식별자
        schema: 조회할 스키마명 (기본값: "public")
    """
    if conn_id not in _redshift_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    sql = f"""
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = '{schema}'
        ORDER BY table_name, ordinal_position
    """
    try:
        conn = _get_redshift_conn(conn_id)
        try:
            cur = conn.cursor()
            cur.execute(sql)
            rows = cur.fetchall()
        finally:
            conn.close()
    except Exception as e:
        return f"[ERROR] 스키마 조회 실패: {e}"

    if not rows:
        return f"스키마 '{schema}'에 테이블이 없습니다."

    lines = [f"## {schema} 스키마\n"]
    current_table = None
    for table_name, column_name, data_type in rows:
        if table_name != current_table:
            lines.append(f"\n### {table_name}")
            current_table = table_name
        lines.append(f"- {column_name}: {data_type}")

    return "\n".join(lines)


def list_redshift_tables(
    conn_id: str,
    schema: str = "public",
) -> str:
    """[Redshift] Redshift 스키마의 테이블 목록을 반환한다.

    Args:
        conn_id: 연결 식별자
        schema: 조회할 스키마명 (기본값: "public")
    """
    if conn_id not in _redshift_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    sql = f"""
        SELECT schemaname, tablename, tableowner
        FROM pg_tables
        WHERE schemaname = '{schema}'
        ORDER BY tablename
    """
    try:
        conn = _get_redshift_conn(conn_id)
        try:
            cur = conn.cursor()
            cur.execute(sql)
            rows = cur.fetchall()
        finally:
            conn.close()
    except Exception as e:
        return f"[ERROR] 테이블 목록 조회 실패: {e}"

    if not rows:
        return f"스키마 '{schema}'에 테이블이 없습니다."

    lines = [f"## {schema} 테이블 목록\n", "| schema | table | owner |", "| --- | --- | --- |"]
    for schemaname, tablename, tableowner in rows:
        lines.append(f"| {schemaname} | {tablename} | {tableowner} |")

    return "\n".join(lines)
```

- [ ] **Step 4: 테스트 실행 — 전부 통과 확인**

```bash
python3 -m pytest tests/unit/test_redshift.py -v --no-header 2>&1 | tail -15
```

예상: `8 passed`

- [ ] **Step 5: server.py에 등록**

`bi_agent_mcp/server.py`의 마지막 `register_tool` 블록 뒤, `if __name__` 앞에 추가:

```python
# redshift tools — AWS IAM 인증 기반 Redshift 연동 (Phase 3a)
from bi_agent_mcp.tools.redshift import (
    connect_redshift,
    run_redshift_query,
    get_redshift_schema,
    list_redshift_tables,
)

register_tool(connect_redshift, is_core=False)
register_tool(run_redshift_query, is_core=False)
register_tool(get_redshift_schema, is_core=False)
register_tool(list_redshift_tables, is_core=False)
```

- [ ] **Step 6: 등록 확인 및 전체 테스트**

```bash
python3 -c "
import os; os.environ['BI_AGENT_LOAD_ALL']='true'
from bi_agent_mcp.server import mcp
tools = list(mcp._tool_manager._tools.keys())
print([t for t in tools if 'redshift' in t])
print('Total:', len(tools))
" && python3 -m pytest tests/unit/ -q --no-header 2>&1 | tail -3
```

예상: `['connect_redshift', 'run_redshift_query', 'get_redshift_schema', 'list_redshift_tables']`, Total: 180

- [ ] **Step 7: 커밋**

```bash
git add bi_agent_mcp/tools/redshift.py tests/unit/test_redshift.py bi_agent_mcp/server.py
git commit -m "feat: [Redshift] IAM 인증 기반 Redshift 연동 도구 4개"
```

---

### Task 2: airflow.py — Airflow REST API 도구 6개

**Files:**
- Create: `bi_agent_mcp/tools/airflow.py`
- Create: `tests/unit/test_airflow.py`
- Modify: `bi_agent_mcp/server.py`

**패턴 참고:** `bi_agent_mcp/tools/redash.py` (httpx Basic Auth 패턴)

- [ ] **Step 1: 실패 테스트 파일 작성**

`tests/unit/test_airflow.py`:

```python
"""bi_agent_mcp.tools.airflow 단위 테스트."""
import json
from unittest.mock import MagicMock, patch
import pytest


def _make_http_mock(status=200, json_data=None, text=""):
    mock_resp = MagicMock()
    mock_resp.status_code = status
    mock_resp.json.return_value = json_data or {}
    mock_resp.text = text

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_resp
    mock_client.post.return_value = mock_resp
    return mock_client


# ---------------------------------------------------------------------------
# connect_airflow
# ---------------------------------------------------------------------------

def test_connect_airflow_success():
    mock_client = _make_http_mock(json_data={"metadatabase": {"status": "healthy"}})

    with patch("bi_agent_mcp.tools.airflow._airflow_connections", {}), \
         patch("bi_agent_mcp.tools.airflow.httpx.Client", return_value=mock_client):
        from bi_agent_mcp.tools.airflow import connect_airflow
        result = connect_airflow("http://airflow:8080", "admin", "password", "test")

    assert "[OK]" in result


def test_connect_airflow_auth_failure():
    mock_client = _make_http_mock(status=401)

    with patch("bi_agent_mcp.tools.airflow.httpx.Client", return_value=mock_client):
        from bi_agent_mcp.tools.airflow import connect_airflow
        result = connect_airflow("http://airflow:8080", "bad", "creds")

    assert "[ERROR]" in result


# ---------------------------------------------------------------------------
# list_airflow_dags
# ---------------------------------------------------------------------------

def test_list_airflow_dags_returns_list():
    dags_data = {
        "dags": [
            {"dag_id": "daily_mart", "is_active": True, "is_paused": False, "tags": [{"name": "mart"}]},
            {"dag_id": "weekly_report", "is_active": True, "is_paused": False, "tags": []},
        ],
        "total_entries": 2,
    }
    mock_client = _make_http_mock(json_data=dags_data)
    store = {"test": {"base_url": "http://airflow:8080", "auth": ("admin", "pass")}}

    with patch("bi_agent_mcp.tools.airflow._airflow_connections", store), \
         patch("bi_agent_mcp.tools.airflow.httpx.Client", return_value=mock_client):
        from bi_agent_mcp.tools.airflow import list_airflow_dags
        result = list_airflow_dags("test")

    assert "daily_mart" in result
    assert "weekly_report" in result


# ---------------------------------------------------------------------------
# get_dag_status
# ---------------------------------------------------------------------------

def test_get_dag_status_returns_run_info():
    runs_data = {
        "dag_runs": [
            {
                "dag_run_id": "manual__2026-04-09",
                "state": "success",
                "start_date": "2026-04-09T01:00:00",
                "end_date": "2026-04-09T01:15:00",
            }
        ]
    }
    mock_client = _make_http_mock(json_data=runs_data)
    store = {"test": {"base_url": "http://airflow:8080", "auth": ("admin", "pass")}}

    with patch("bi_agent_mcp.tools.airflow._airflow_connections", store), \
         patch("bi_agent_mcp.tools.airflow.httpx.Client", return_value=mock_client):
        from bi_agent_mcp.tools.airflow import get_dag_status
        result = get_dag_status("test", "daily_mart")

    assert "success" in result
    assert "daily_mart" in result


# ---------------------------------------------------------------------------
# trigger_dag
# ---------------------------------------------------------------------------

def test_trigger_dag_returns_run_id():
    trigger_data = {"dag_run_id": "manual__2026-04-09T10:00:00", "state": "queued"}
    mock_client = _make_http_mock(json_data=trigger_data)
    store = {"test": {"base_url": "http://airflow:8080", "auth": ("admin", "pass")}}

    with patch("bi_agent_mcp.tools.airflow._airflow_connections", store), \
         patch("bi_agent_mcp.tools.airflow.httpx.Client", return_value=mock_client):
        from bi_agent_mcp.tools.airflow import trigger_dag
        result = trigger_dag("test", "daily_mart")

    assert "[OK]" in result
    assert "manual__2026-04-09T10:00:00" in result


# ---------------------------------------------------------------------------
# get_task_logs
# ---------------------------------------------------------------------------

def test_get_task_logs_returns_log_text():
    mock_client = _make_http_mock(text="[2026-04-09] INFO - Task completed successfully")

    store = {"test": {"base_url": "http://airflow:8080", "auth": ("admin", "pass")}}

    with patch("bi_agent_mcp.tools.airflow._airflow_connections", store), \
         patch("bi_agent_mcp.tools.airflow.httpx.Client", return_value=mock_client):
        from bi_agent_mcp.tools.airflow import get_task_logs
        result = get_task_logs("test", "daily_mart", "manual__2026-04-09", "run_sql")

    assert "Task completed" in result


# ---------------------------------------------------------------------------
# list_dag_runs
# ---------------------------------------------------------------------------

def test_list_dag_runs_returns_history():
    runs_data = {
        "dag_runs": [
            {"dag_run_id": "run1", "state": "success", "start_date": "2026-04-08T01:00:00", "end_date": "2026-04-08T01:10:00"},
            {"dag_run_id": "run2", "state": "failed", "start_date": "2026-04-07T01:00:00", "end_date": "2026-04-07T01:05:00"},
        ]
    }
    mock_client = _make_http_mock(json_data=runs_data)
    store = {"test": {"base_url": "http://airflow:8080", "auth": ("admin", "pass")}}

    with patch("bi_agent_mcp.tools.airflow._airflow_connections", store), \
         patch("bi_agent_mcp.tools.airflow.httpx.Client", return_value=mock_client):
        from bi_agent_mcp.tools.airflow import list_dag_runs
        result = list_dag_runs("test", "daily_mart", limit=10)

    assert "success" in result
    assert "failed" in result

def test_list_airflow_dags_unknown_conn_returns_error():
    with patch("bi_agent_mcp.tools.airflow._airflow_connections", {}):
        from bi_agent_mcp.tools.airflow import list_airflow_dags
        result = list_airflow_dags("not_exist")
    assert "[ERROR]" in result
```

- [ ] **Step 2: 테스트 실행 — ImportError 확인**

```bash
python3 -m pytest tests/unit/test_airflow.py -q --no-header 2>&1 | head -5
```

예상: `ModuleNotFoundError` (airflow.py 없음)

- [ ] **Step 3: airflow.py 구현**

`bi_agent_mcp/tools/airflow.py`:

```python
"""[Airflow] Apache Airflow REST API 연동 도구."""
import json
import logging
from typing import Dict, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

_airflow_connections: Dict[str, dict] = {}


def connect_airflow(
    base_url: str,
    username: str,
    password: str,
    conn_id: str = "default",
) -> str:
    """[Airflow] Airflow REST API에 연결한다.

    Args:
        base_url: Airflow 서버 URL (예: "http://airflow.internal:8080")
        username: Airflow 로그인 username
        password: Airflow 로그인 password
        conn_id: 연결 식별자 (기본값: "default")
    """
    base_url = base_url.rstrip("/")
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{base_url}/api/v1/health",
                auth=(username, password),
            )
        if resp.status_code == 401:
            return "[ERROR] Airflow 인증 실패: username 또는 password를 확인하세요."
        if resp.status_code != 200:
            return f"[ERROR] Airflow 연결 실패: HTTP {resp.status_code}"
    except httpx.RequestError as e:
        return f"[ERROR] Airflow 연결 중 네트워크 오류: {e}"

    _airflow_connections[conn_id] = {
        "base_url": base_url,
        "auth": (username, password),
    }
    return f"[OK] Airflow 연결 완료: {conn_id} ({base_url})"


def _get_creds(conn_id: str) -> Tuple[str, Tuple[str, str]]:
    if conn_id not in _airflow_connections:
        raise ValueError(f"연결 ID '{conn_id}'를 찾을 수 없습니다. connect_airflow()를 먼저 호출하세요.")
    info = _airflow_connections[conn_id]
    return info["base_url"], info["auth"]


def list_airflow_dags(
    conn_id: str,
    tags: str = None,
    only_active: bool = True,
    limit: int = 50,
) -> str:
    """[Airflow] DAG 목록과 활성화 상태를 반환한다.

    Args:
        conn_id: 연결 식별자
        tags: 태그 필터 (쉼표 구분, 예: "mart,daily")
        only_active: True이면 활성화된 DAG만 표시
        limit: 최대 반환 수 (기본값: 50)
    """
    if conn_id not in _airflow_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    base_url, auth = _get_creds(conn_id)
    params = {"limit": limit, "only_active": str(only_active).lower()}
    if tags:
        params["tags"] = tags

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(f"{base_url}/api/v1/dags", auth=auth, params=params)
        if resp.status_code != 200:
            return f"[ERROR] DAG 목록 조회 실패: HTTP {resp.status_code}"
        data = resp.json()
    except httpx.RequestError as e:
        return f"[ERROR] 네트워크 오류: {e}"

    dags = data.get("dags", [])
    if not dags:
        return "DAG 목록이 없습니다."

    lines = [f"## DAG 목록 ({data.get('total_entries', len(dags))}개)\n",
             "| DAG ID | 활성화 | 일시정지 | 태그 |",
             "| --- | --- | --- | --- |"]
    for dag in dags:
        tags_str = ", ".join(t.get("name", "") for t in dag.get("tags", []))
        lines.append(f"| {dag['dag_id']} | {dag.get('is_active', '-')} | {dag.get('is_paused', '-')} | {tags_str} |")

    return "\n".join(lines)


def get_dag_status(
    conn_id: str,
    dag_id: str,
) -> str:
    """[Airflow] DAG의 최근 5회 실행 상태를 반환한다.

    Args:
        conn_id: 연결 식별자
        dag_id: DAG ID
    """
    if conn_id not in _airflow_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    base_url, auth = _get_creds(conn_id)
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                f"{base_url}/api/v1/dags/{dag_id}/dagRuns",
                auth=auth,
                params={"limit": 5, "order_by": "-start_date"},
            )
        if resp.status_code == 404:
            return f"[ERROR] DAG '{dag_id}'를 찾을 수 없습니다."
        if resp.status_code != 200:
            return f"[ERROR] DAG 상태 조회 실패: HTTP {resp.status_code}"
        data = resp.json()
    except httpx.RequestError as e:
        return f"[ERROR] 네트워크 오류: {e}"

    runs = data.get("dag_runs", [])
    if not runs:
        return f"DAG '{dag_id}'의 실행 이력이 없습니다."

    lines = [f"## {dag_id} 실행 상태\n",
             "| Run ID | 상태 | 시작 | 종료 |",
             "| --- | --- | --- | --- |"]
    for run in runs:
        lines.append(
            f"| {run.get('dag_run_id', '-')} | {run.get('state', '-')} "
            f"| {run.get('start_date', '-')} | {run.get('end_date', '-')} |"
        )

    return "\n".join(lines)


def trigger_dag(
    conn_id: str,
    dag_id: str,
    conf: str = "{}",
    logical_date: str = None,
) -> str:
    """[Airflow] DAG를 수동으로 트리거한다.

    Args:
        conn_id: 연결 식별자
        dag_id: 트리거할 DAG ID
        conf: DAG 실행 설정 (JSON 문자열, 기본값: "{}")
        logical_date: 논리적 실행 날짜 (ISO 8601, None이면 현재 시각)
    """
    if conn_id not in _airflow_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    base_url, auth = _get_creds(conn_id)
    try:
        conf_dict = json.loads(conf)
    except json.JSONDecodeError:
        return "[ERROR] conf 파라미터가 유효한 JSON이 아닙니다."

    body = {"conf": conf_dict}
    if logical_date:
        body["logical_date"] = logical_date

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                f"{base_url}/api/v1/dags/{dag_id}/dagRuns",
                auth=auth,
                json=body,
            )
        if resp.status_code == 404:
            return f"[ERROR] DAG '{dag_id}'를 찾을 수 없습니다."
        if resp.status_code not in (200, 201):
            return f"[ERROR] DAG 트리거 실패: HTTP {resp.status_code} — {resp.text}"
        data = resp.json()
    except httpx.RequestError as e:
        return f"[ERROR] 네트워크 오류: {e}"

    run_id = data.get("dag_run_id", "-")
    state = data.get("state", "-")
    return f"[OK] DAG 트리거 완료: {run_id} (state: {state})"


def get_task_logs(
    conn_id: str,
    dag_id: str,
    dag_run_id: str,
    task_id: str,
    task_try_number: int = 1,
) -> str:
    """[Airflow] 특정 태스크의 실행 로그를 반환한다.

    Args:
        conn_id: 연결 식별자
        dag_id: DAG ID
        dag_run_id: DAG Run ID (get_dag_status에서 확인)
        task_id: 태스크 ID
        task_try_number: 시도 번호 (기본값: 1)
    """
    if conn_id not in _airflow_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    base_url, auth = _get_creds(conn_id)
    url = (
        f"{base_url}/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}"
        f"/taskInstances/{task_id}/logs/{task_try_number}"
    )

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(url, auth=auth)
        if resp.status_code == 404:
            return f"[ERROR] 태스크 로그를 찾을 수 없습니다: {dag_id}/{task_id}"
        if resp.status_code != 200:
            return f"[ERROR] 로그 조회 실패: HTTP {resp.status_code}"
        return resp.text[:5000]  # 최대 5000자
    except httpx.RequestError as e:
        return f"[ERROR] 네트워크 오류: {e}"


def list_dag_runs(
    conn_id: str,
    dag_id: str,
    limit: int = 10,
) -> str:
    """[Airflow] DAG의 최근 실행 이력을 반환한다.

    Args:
        conn_id: 연결 식별자
        dag_id: DAG ID
        limit: 최대 반환 수 (기본값: 10)
    """
    if conn_id not in _airflow_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    base_url, auth = _get_creds(conn_id)
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                f"{base_url}/api/v1/dags/{dag_id}/dagRuns",
                auth=auth,
                params={"limit": limit, "order_by": "-start_date"},
            )
        if resp.status_code != 200:
            return f"[ERROR] 실행 이력 조회 실패: HTTP {resp.status_code}"
        data = resp.json()
    except httpx.RequestError as e:
        return f"[ERROR] 네트워크 오류: {e}"

    runs = data.get("dag_runs", [])
    if not runs:
        return f"DAG '{dag_id}'의 실행 이력이 없습니다."

    lines = [f"## {dag_id} 최근 {limit}회 실행 이력\n",
             "| Run ID | 상태 | 시작 | 종료 |",
             "| --- | --- | --- | --- |"]
    for run in runs:
        lines.append(
            f"| {run.get('dag_run_id', '-')} | {run.get('state', '-')} "
            f"| {run.get('start_date', '-')} | {run.get('end_date', '-')} |"
        )

    return "\n".join(lines)
```

- [ ] **Step 4: 테스트 실행 — 전부 통과 확인**

```bash
python3 -m pytest tests/unit/test_airflow.py -v --no-header 2>&1 | tail -15
```

예상: `9 passed`

- [ ] **Step 5: server.py에 등록**

`bi_agent_mcp/server.py`의 Redshift 등록 블록 바로 뒤에 추가:

```python
# airflow tools — Airflow REST API 연동 (Phase 3a)
from bi_agent_mcp.tools.airflow import (
    connect_airflow,
    list_airflow_dags,
    get_dag_status,
    trigger_dag,
    get_task_logs,
    list_dag_runs,
)

register_tool(connect_airflow, is_core=False)
register_tool(list_airflow_dags, is_core=False)
register_tool(get_dag_status, is_core=False)
register_tool(trigger_dag, is_core=False)
register_tool(get_task_logs, is_core=False)
register_tool(list_dag_runs, is_core=False)
```

- [ ] **Step 6: 등록 확인 및 전체 테스트**

```bash
python3 -c "
import os; os.environ['BI_AGENT_LOAD_ALL']='true'
from bi_agent_mcp.server import mcp
tools = list(mcp._tool_manager._tools.keys())
print([t for t in tools if 'airflow' in t or 'dag' in t])
print('Total:', len(tools))
" && python3 -m pytest tests/unit/ -q --no-header 2>&1 | tail -3
```

예상: 6개 Airflow 도구 출력, Total: 186

- [ ] **Step 7: 커밋**

```bash
git add bi_agent_mcp/tools/airflow.py tests/unit/test_airflow.py bi_agent_mcp/server.py
git commit -m "feat: [Airflow] Airflow REST API 연동 도구 6개 (DAG 관리, 트리거, 로그)"
```

---

### Task 3: Metabase 강화 — 기존 metabase.py에 4개 함수 추가

**Files:**
- Modify: `bi_agent_mcp/tools/metabase.py`
- Modify: `tests/unit/test_metabase.py`
- Modify: `bi_agent_mcp/server.py`

**주의:** `tests/unit/test_metabase.py`가 이미 존재한다. 기존 테스트를 건드리지 않고 파일 끝에 새 테스트를 추가한다. `metabase.py`도 기존 4개 함수를 건드리지 않고 새 함수를 파일 끝에 추가한다.

- [ ] **Step 1: test_metabase.py 끝에 새 테스트 추가**

`tests/unit/test_metabase.py` 파일 끝에 추가:

```python
# ---------------------------------------------------------------------------
# Phase 3a: 신규 4개 함수 테스트
# ---------------------------------------------------------------------------

from bi_agent_mcp.tools.metabase import (
    list_metabase_collections,
    get_metabase_card_data,
    refresh_metabase_cache,
    run_metabase_adhoc_sql,
)


def _make_mb_mock(status=200, json_data=None, text=""):
    mock_resp = MagicMock()
    mock_resp.status_code = status
    mock_resp.json.return_value = json_data or {}
    mock_resp.text = text

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_resp
    mock_client.post.return_value = mock_resp
    return mock_client


def test_list_metabase_collections_returns_collection_list():
    data = {
        "data": [
            {"id": 1, "name": "Our analytics", "location": "/"},
            {"id": 5, "name": "Marketing", "location": "/1/"},
        ]
    }
    mock_client = _make_mb_mock(json_data=data)
    store = {"test": {"url": "http://mb:3000", "token": "abc123"}}

    with patch("bi_agent_mcp.tools.metabase._metabase_connections", store), \
         patch("bi_agent_mcp.tools.metabase.httpx.Client", return_value=mock_client):
        result = list_metabase_collections("test")

    assert "Our analytics" in result
    assert "Marketing" in result


def test_get_metabase_card_data_returns_table():
    data = {
        "data": {
            "cols": [{"display_name": "date"}, {"display_name": "revenue"}],
            "rows": [["2026-04-01", 1000000], ["2026-04-02", 1200000]],
        }
    }
    mock_client = _make_mb_mock(json_data=data)
    store = {"test": {"url": "http://mb:3000", "token": "abc123"}}

    with patch("bi_agent_mcp.tools.metabase._metabase_connections", store), \
         patch("bi_agent_mcp.tools.metabase.httpx.Client", return_value=mock_client):
        result = get_metabase_card_data("test", 42)

    assert "date" in result
    assert "1000000" in result or "1,000,000" in result or "revenue" in result


def test_refresh_metabase_cache_returns_ok():
    mock_client = _make_mb_mock(status=202)
    store = {"test": {"url": "http://mb:3000", "token": "abc123"}}

    with patch("bi_agent_mcp.tools.metabase._metabase_connections", store), \
         patch("bi_agent_mcp.tools.metabase.httpx.Client", return_value=mock_client):
        result = refresh_metabase_cache("test", 42)

    assert "[OK]" in result


def test_run_metabase_adhoc_sql_returns_results():
    data = {
        "data": {
            "cols": [{"display_name": "cnt"}],
            "rows": [[99]],
        }
    }
    mock_client = _make_mb_mock(json_data=data)
    store = {"test": {"url": "http://mb:3000", "token": "abc123"}}

    with patch("bi_agent_mcp.tools.metabase._metabase_connections", store), \
         patch("bi_agent_mcp.tools.metabase.httpx.Client", return_value=mock_client):
        result = run_metabase_adhoc_sql("test", 1, "SELECT COUNT(*) AS cnt FROM orders")

    assert "99" in result or "cnt" in result


def test_run_metabase_adhoc_sql_blocks_dml():
    store = {"test": {"url": "http://mb:3000", "token": "abc123"}}
    with patch("bi_agent_mcp.tools.metabase._metabase_connections", store):
        result = run_metabase_adhoc_sql("test", 1, "DROP TABLE orders")
    assert "[ERROR]" in result
```

- [ ] **Step 2: 테스트 실행 — 새 테스트만 실패 확인**

```bash
python3 -m pytest tests/unit/test_metabase.py -k "collections or card_data or cache or adhoc" -q --no-header 2>&1 | head -10
```

예상: `ImportError` (새 함수들 없음)

- [ ] **Step 3: metabase.py 끝에 4개 함수 추가**

`bi_agent_mcp/tools/metabase.py` 파일 끝에 추가 (기존 함수 건드리지 않음):

```python
# ---------------------------------------------------------------------------
# Phase 3a 강화: Tableau 수준 기능 (+4개)
# ---------------------------------------------------------------------------

from bi_agent_mcp.tools.db import _validate_select as _validate_sql


def list_metabase_collections(
    conn_id: str = "default",
) -> str:
    """[Metabase] 컬렉션(폴더) 목록과 구조를 반환한다.

    Args:
        conn_id: 연결 식별자 (기본값: "default")
    """
    if conn_id not in _metabase_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. connect_metabase()를 먼저 호출하세요."

    creds = _metabase_connections[conn_id]
    headers = {"X-Metabase-Session": creds["token"]}

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(f"{creds['url']}/api/collection", headers=headers)
        if resp.status_code != 200:
            return f"[ERROR] 컬렉션 조회 실패: HTTP {resp.status_code}"
        data = resp.json()
    except httpx.RequestError as e:
        return f"[ERROR] 네트워크 오류: {e}"

    collections = data.get("data", data) if isinstance(data, dict) else data
    if not collections:
        return "컬렉션이 없습니다."

    lines = ["## Metabase 컬렉션 목록\n", "| ID | 이름 | 경로 |", "| --- | --- | --- |"]
    for col in collections:
        lines.append(f"| {col.get('id', '-')} | {col.get('name', '-')} | {col.get('location', '/')} |")

    return "\n".join(lines)


def get_metabase_card_data(
    conn_id: str,
    card_id: int,
    parameters: str = "[]",
) -> str:
    """[Metabase] 카드(질문)의 실제 데이터를 조회한다. Tableau get_view_data에 해당.

    Args:
        conn_id: 연결 식별자
        card_id: Metabase 카드 ID
        parameters: 필터 파라미터 (JSON 배열 문자열, 기본값: "[]")
    """
    if conn_id not in _metabase_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    try:
        params_list = json.loads(parameters)
    except json.JSONDecodeError:
        return "[ERROR] parameters가 유효한 JSON 배열이 아닙니다."

    creds = _metabase_connections[conn_id]
    headers = {"X-Metabase-Session": creds["token"]}

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{creds['url']}/api/card/{card_id}/query/json",
                headers=headers,
                json={"parameters": params_list},
            )
        if resp.status_code == 404:
            return f"[ERROR] 카드 ID {card_id}를 찾을 수 없습니다."
        if resp.status_code != 200:
            return f"[ERROR] 카드 데이터 조회 실패: HTTP {resp.status_code}"
        data = resp.json()
    except httpx.RequestError as e:
        return f"[ERROR] 네트워크 오류: {e}"

    inner = data.get("data", data)
    cols = [c.get("display_name", c.get("name", "?")) for c in inner.get("cols", [])]
    rows = inner.get("rows", [])[:500]

    if not rows:
        return "데이터가 없습니다."

    header = " | ".join(cols)
    sep = " | ".join(["---"] * len(cols))
    body = "\n".join(f"| {' | '.join(str(v) for v in row)} |" for row in rows)
    return f"| {header} |\n| {sep} |\n{body}\n\n총 {len(rows)}행 반환"


def refresh_metabase_cache(
    conn_id: str,
    card_id: int,
) -> str:
    """[Metabase] 카드의 쿼리 캐시를 강제 새로고침한다.

    Args:
        conn_id: 연결 식별자
        card_id: Metabase 카드 ID
    """
    if conn_id not in _metabase_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    creds = _metabase_connections[conn_id]
    headers = {"X-Metabase-Session": creds["token"]}

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{creds['url']}/api/card/{card_id}/query",
                headers=headers,
                json={"ignore_cache": True},
            )
        if resp.status_code == 404:
            return f"[ERROR] 카드 ID {card_id}를 찾을 수 없습니다."
        if resp.status_code not in (200, 202):
            return f"[ERROR] 캐시 새로고침 실패: HTTP {resp.status_code}"
    except httpx.RequestError as e:
        return f"[ERROR] 네트워크 오류: {e}"

    return f"[OK] 카드 {card_id} 캐시 새로고침 완료"


def run_metabase_adhoc_sql(
    conn_id: str,
    database_id: int,
    sql: str,
    limit: int = 500,
) -> str:
    """[Metabase] Metabase에 연결된 데이터베이스에 Native SQL을 직접 실행한다.

    Args:
        conn_id: 연결 식별자
        database_id: Metabase 데이터베이스 ID
        sql: 실행할 SELECT 쿼리 (DML 자동 차단)
        limit: 최대 반환 행 수 (기본값: 500)
    """
    err = _validate_sql(sql)
    if err:
        return f"[ERROR] {err}"

    if conn_id not in _metabase_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    creds = _metabase_connections[conn_id]
    headers = {"X-Metabase-Session": creds["token"]}

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{creds['url']}/api/dataset",
                headers=headers,
                json={
                    "database": database_id,
                    "type": "native",
                    "native": {"query": sql},
                    "parameters": [],
                },
            )
        if resp.status_code != 202 and resp.status_code != 200:
            return f"[ERROR] SQL 실행 실패: HTTP {resp.status_code} — {resp.text[:200]}"
        data = resp.json()
    except httpx.RequestError as e:
        return f"[ERROR] 네트워크 오류: {e}"

    inner = data.get("data", data)
    cols = [c.get("display_name", c.get("name", "?")) for c in inner.get("cols", [])]
    rows = inner.get("rows", [])[:limit]

    if not rows:
        return "결과가 없습니다."

    header = " | ".join(cols)
    sep = " | ".join(["---"] * len(cols))
    body = "\n".join(f"| {' | '.join(str(v) for v in row)} |" for row in rows)
    return f"| {header} |\n| {sep} |\n{body}\n\n총 {len(rows)}행 반환"
```

- [ ] **Step 4: 테스트 실행 — 전부 통과 확인**

```bash
python3 -m pytest tests/unit/test_metabase.py -v --no-header 2>&1 | tail -15
```

예상: 기존 테스트 + 신규 5개 = 모두 통과

- [ ] **Step 5: server.py에 신규 4개 등록**

`bi_agent_mcp/server.py`의 기존 metabase 등록 블록 (`register_tool(list_metabase_dashboards, ...)`) 바로 뒤에 추가:

```python
# metabase 강화 — Phase 3a (Tableau 수준 기능)
from bi_agent_mcp.tools.metabase import (
    list_metabase_collections,
    get_metabase_card_data,
    refresh_metabase_cache,
    run_metabase_adhoc_sql,
)

register_tool(list_metabase_collections, is_core=False)
register_tool(get_metabase_card_data, is_core=False)
register_tool(refresh_metabase_cache, is_core=False)
register_tool(run_metabase_adhoc_sql, is_core=False)
```

- [ ] **Step 6: 최종 확인**

```bash
python3 -c "
import os; os.environ['BI_AGENT_LOAD_ALL']='true'
from bi_agent_mcp.server import mcp
tools = list(mcp._tool_manager._tools.keys())
new_tools = [t for t in tools if t in ['list_metabase_collections','get_metabase_card_data','refresh_metabase_cache','run_metabase_adhoc_sql']]
print('New Metabase tools:', new_tools)
print('Total:', len(tools))
" && python3 -m pytest tests/unit/ -q --no-header 2>&1 | tail -3
```

예상: 4개 Metabase 신규 도구, Total: 190, 모든 테스트 통과

- [ ] **Step 7: 커밋**

```bash
git add bi_agent_mcp/tools/metabase.py tests/unit/test_metabase.py bi_agent_mcp/server.py
git commit -m "feat: [Metabase] 강화 4개 (컬렉션/카드데이터/캐시새로고침/AdHoc SQL) — Tableau 수준"
```

---

## 최종 검증

- [ ] **전체 테스트 재실행**

```bash
python3 -m pytest tests/unit/ -q --no-header 2>&1 | tail -5
```

예상: 1270+ passed, 커버리지 80%+

- [ ] **도구 수 확인**

```bash
python3 -c "
import os; os.environ['BI_AGENT_LOAD_ALL']='true'
from bi_agent_mcp.server import mcp
print('Total tools:', len(mcp._tool_manager._tools))
"
```

예상: 190
