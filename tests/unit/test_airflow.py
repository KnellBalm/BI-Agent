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


def test_get_task_logs_returns_log_text():
    mock_client = _make_http_mock(text="[2026-04-09] INFO - Task completed successfully")
    store = {"test": {"base_url": "http://airflow:8080", "auth": ("admin", "pass")}}

    with patch("bi_agent_mcp.tools.airflow._airflow_connections", store), \
         patch("bi_agent_mcp.tools.airflow.httpx.Client", return_value=mock_client):
        from bi_agent_mcp.tools.airflow import get_task_logs
        result = get_task_logs("test", "daily_mart", "manual__2026-04-09", "run_sql")

    assert "Task completed" in result


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


def test_trigger_dag_invalid_conf_returns_error():
    store = {"test": {"base_url": "http://airflow:8080", "auth": ("admin", "pass")}}
    with patch("bi_agent_mcp.tools.airflow._airflow_connections", store):
        from bi_agent_mcp.tools.airflow import trigger_dag
        result = trigger_dag("test", "daily_mart", conf="not valid json")
    assert "[ERROR]" in result
