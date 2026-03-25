"""bi_agent_mcp.tools.alerts 단위 테스트."""
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

import bi_agent_mcp.tools.alerts as alerts_module
from bi_agent_mcp.tools.alerts import (
    create_alert,
    check_alerts,
    list_alerts,
    delete_alert,
)
from bi_agent_mcp.tools.db import ConnectionInfo


def _make_conn_info(conn_id: str) -> ConnectionInfo:
    return ConnectionInfo(
        conn_id=conn_id,
        db_type="postgresql",
        host="localhost",
        port=5432,
        database="testdb",
        user="user",
        password="pass",
    )


@pytest.fixture(autouse=True)
def patch_alerts_file(tmp_path, monkeypatch):
    """_ALERTS_FILE을 tmp_path의 파일로 override."""
    tmp_file = tmp_path / "alerts.json"
    monkeypatch.setattr(alerts_module, "_ALERTS_FILE", tmp_file)
    yield tmp_file


class TestCreateAlert:
    def test_create_alert_registers_and_saves(self, patch_alerts_file):
        """정상 등록: 파일에 저장되고 alert_id 반환."""
        result = create_alert(
            conn_id="pg1",
            name="주문수 알림",
            sql="SELECT COUNT(*) FROM orders",
            condition="gt:100",
            message="주문이 100건 초과",
        )
        assert "[ERROR]" not in result
        assert "주문수 알림" in result
        assert patch_alerts_file.exists()
        data = json.loads(patch_alerts_file.read_text())
        assert len(data) == 1
        assert data[0]["name"] == "주문수 알림"
        assert data[0]["conn_id"] == "pg1"


class TestCheckAlerts:
    def test_gt_condition_triggered(self, patch_alerts_file):
        """gt 조건: 값이 임계값 초과 → TRIGGERED."""
        conn_id = "pg_check01"
        create_alert(conn_id=conn_id, name="테스트알림", sql="SELECT 200", condition="gt:100")

        mock_cur = MagicMock()
        mock_cur.description = [("count",)]
        mock_cur.fetchone.return_value = (200,)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur

        fake_connections = {conn_id: _make_conn_info(conn_id)}
        with patch("bi_agent_mcp.tools.db._connections", fake_connections), \
             patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn):
            result = check_alerts()

        assert "TRIGGERED" in result

    def test_lt_condition_ok(self, patch_alerts_file):
        """lt 조건: 값이 임계값 이상일 때 → OK."""
        conn_id = "pg_check02"
        create_alert(conn_id=conn_id, name="lt알림", sql="SELECT 60", condition="lt:50")

        mock_cur = MagicMock()
        mock_cur.description = [("val",)]
        mock_cur.fetchone.return_value = (60,)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur

        fake_connections = {conn_id: _make_conn_info(conn_id)}
        with patch("bi_agent_mcp.tools.db._connections", fake_connections), \
             patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn):
            result = check_alerts()

        assert "OK" in result

    def test_eq_condition_triggered(self, patch_alerts_file):
        """eq 조건: 값이 임계값과 같을 때 → TRIGGERED."""
        conn_id = "pg_check03"
        create_alert(conn_id=conn_id, name="eq알림", sql="SELECT 0", condition="eq:0")

        mock_cur = MagicMock()
        mock_cur.description = [("val",)]
        mock_cur.fetchone.return_value = (0,)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur

        fake_connections = {conn_id: _make_conn_info(conn_id)}
        with patch("bi_agent_mcp.tools.db._connections", fake_connections), \
             patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn):
            result = check_alerts()

        assert "TRIGGERED" in result

    def test_specific_alert_id_check(self, patch_alerts_file):
        """alert_id 지정 시 해당 알림만 평가."""
        conn_id = "pg_check04"
        create_alert(conn_id=conn_id, name="알림A", sql="SELECT 50", condition="gt:100")
        create_alert(conn_id=conn_id, name="알림B", sql="SELECT 200", condition="gt:100")

        data = json.loads(patch_alerts_file.read_text())
        target_id = data[0]["alert_id"]

        mock_cur = MagicMock()
        mock_cur.description = [("val",)]
        mock_cur.fetchone.return_value = (50,)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur

        fake_connections = {conn_id: _make_conn_info(conn_id)}
        with patch("bi_agent_mcp.tools.db._connections", fake_connections), \
             patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn):
            result = check_alerts(alert_id=target_id)

        assert "알림A" in result
        assert "알림B" not in result

    def test_no_alerts_registered(self, patch_alerts_file):
        """등록된 알림 없음 → 안내 메시지."""
        result = check_alerts()
        assert "없습니다" in result


class TestListAlerts:
    def test_list_alerts_empty(self, patch_alerts_file):
        """빈 목록 → 안내 메시지."""
        result = list_alerts()
        assert "없습니다" in result

    def test_list_alerts_with_entries(self, patch_alerts_file):
        """알림 있는 경우 → 테이블 형태로 반환."""
        create_alert(conn_id="pg1", name="알림1", sql="SELECT COUNT(*) FROM t", condition="gt:10")
        create_alert(conn_id="pg2", name="알림2", sql="SELECT SUM(amount) FROM sales", condition="lt:1000")

        result = list_alerts()
        assert "알림1" in result
        assert "알림2" in result
        assert "pg1" in result


class TestDeleteAlert:
    def test_delete_existing_alert(self, patch_alerts_file):
        """정상 삭제."""
        create_alert(conn_id="pg1", name="삭제알림", sql="SELECT 1", condition="eq:1")
        data = json.loads(patch_alerts_file.read_text())
        alert_id = data[0]["alert_id"]

        result = delete_alert(alert_id)
        assert "[ERROR]" not in result
        assert "삭제알림" in result

        remaining = json.loads(patch_alerts_file.read_text())
        assert len(remaining) == 0

    def test_delete_nonexistent_alert(self, patch_alerts_file):
        """없는 ID → [ERROR]."""
        result = delete_alert("nonexistent-id-1234")
        assert "[ERROR]" in result
        assert "nonexistent-id-1234" in result

    def test_delete_save_exception(self, patch_alerts_file):
        """삭제 중 저장 오류 → [ERROR] 반환 (lines 194-196)."""
        create_alert(conn_id="pg1", name="저장오류알림", sql="SELECT 1", condition="eq:1")
        data = json.loads(patch_alerts_file.read_text())
        alert_id = data[0]["alert_id"]

        with patch.object(alerts_module, "_save_alerts", side_effect=OSError("디스크 오류")):
            result = delete_alert(alert_id)
        assert "[ERROR]" in result


class TestLoadAlertsCorrupt:
    """_load_alerts 예외 처리 테스트."""

    def test_corrupt_json_returns_empty(self, patch_alerts_file):
        """잘못된 JSON 파일 → 빈 목록 반환 (lines 19-21)."""
        patch_alerts_file.write_text("not valid json")
        result = list_alerts()
        assert "없습니다" in result

    def test_create_alert_save_exception(self, patch_alerts_file):
        """create_alert 저장 오류 → [ERROR] 반환 (lines 83-85)."""
        with patch.object(alerts_module, "_save_alerts", side_effect=OSError("권한 없음")):
            result = create_alert(conn_id="pg1", name="알림", sql="SELECT 1", condition="gt:0")
        assert "[ERROR]" in result


class TestEvaluateConditionEdgeCases:
    """_evaluate_condition 엣지 케이스."""

    def test_invalid_condition_format_returns_false(self, patch_alerts_file):
        """잘못된 condition 형식 → False (lines 37-38)."""
        conn_id = "pg_eval_bad"
        create_alert(conn_id=conn_id, name="잘못된조건", sql="SELECT 50", condition="invalid_no_colon")

        mock_cur = MagicMock()
        mock_cur.description = [("val",)]
        mock_cur.fetchone.return_value = (50,)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur

        fake_connections = {conn_id: _make_conn_info(conn_id)}
        with patch("bi_agent_mcp.tools.db._connections", fake_connections), \
             patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn):
            result = check_alerts()
        assert "OK" in result  # False → not triggered → OK

    def test_ne_condition(self, patch_alerts_file):
        """ne 조건: 값이 임계값과 다를 때 → TRIGGERED (line 47-48)."""
        conn_id = "pg_ne01"
        create_alert(conn_id=conn_id, name="ne알림", sql="SELECT 5", condition="ne:0")

        mock_cur = MagicMock()
        mock_cur.description = [("val",)]
        mock_cur.fetchone.return_value = (5,)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur

        fake_connections = {conn_id: _make_conn_info(conn_id)}
        with patch("bi_agent_mcp.tools.db._connections", fake_connections), \
             patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn):
            result = check_alerts()
        assert "TRIGGERED" in result

    def test_gte_condition(self, patch_alerts_file):
        """gte 조건: 값이 임계값 이상 → TRIGGERED (lines 49-50)."""
        conn_id = "pg_gte01"
        create_alert(conn_id=conn_id, name="gte알림", sql="SELECT 100", condition="gte:100")

        mock_cur = MagicMock()
        mock_cur.description = [("val",)]
        mock_cur.fetchone.return_value = (100,)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur

        fake_connections = {conn_id: _make_conn_info(conn_id)}
        with patch("bi_agent_mcp.tools.db._connections", fake_connections), \
             patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn):
            result = check_alerts()
        assert "TRIGGERED" in result

    def test_lte_condition(self, patch_alerts_file):
        """lte 조건: 값이 임계값 이하 → TRIGGERED (lines 51-52)."""
        conn_id = "pg_lte01"
        create_alert(conn_id=conn_id, name="lte알림", sql="SELECT 30", condition="lte:50")

        mock_cur = MagicMock()
        mock_cur.description = [("val",)]
        mock_cur.fetchone.return_value = (30,)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur

        fake_connections = {conn_id: _make_conn_info(conn_id)}
        with patch("bi_agent_mcp.tools.db._connections", fake_connections), \
             patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn):
            result = check_alerts()
        assert "TRIGGERED" in result

    def test_unknown_operator_returns_false(self, patch_alerts_file):
        """알 수 없는 연산자 → False (line 53 return False)."""
        conn_id = "pg_unk01"
        create_alert(conn_id=conn_id, name="unk알림", sql="SELECT 50", condition="xyz:50")

        mock_cur = MagicMock()
        mock_cur.description = [("val",)]
        mock_cur.fetchone.return_value = (50,)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur

        fake_connections = {conn_id: _make_conn_info(conn_id)}
        with patch("bi_agent_mcp.tools.db._connections", fake_connections), \
             patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn):
            result = check_alerts()
        assert "OK" in result


class TestCheckAlertsErrorPaths:
    """check_alerts 에러 경로 테스트."""

    def test_unknown_alert_id_returns_error(self, patch_alerts_file):
        """존재하지 않는 alert_id → [ERROR] (lines 107-108)."""
        create_alert(conn_id="pg1", name="존재알림", sql="SELECT 1", condition="gt:0")
        result = check_alerts(alert_id="non-existent-uuid")
        assert "[ERROR]" in result

    def test_invalid_sql_validation_error(self, patch_alerts_file):
        """SELECT가 아닌 SQL → 검증 오류 (lines 122-123)."""
        create_alert(conn_id="pg1", name="DROP알림", sql="DROP TABLE orders", condition="gt:0")
        result = check_alerts()
        assert "[ERROR]" in result

    def test_conn_id_not_found_in_connections(self, patch_alerts_file):
        """연결 ID 없음 → 오류 행 (lines 127-128)."""
        create_alert(conn_id="nonexistent_conn", name="없는연결", sql="SELECT 1", condition="gt:0")
        with patch("bi_agent_mcp.tools.db._connections", {}):
            result = check_alerts()
        assert "없음" in result or "[ERROR]" in result

    def test_db_execution_exception(self, patch_alerts_file):
        """DB 실행 예외 → 오류 행 (lines 138-140)."""
        conn_id = "pg_exec_err"
        create_alert(conn_id=conn_id, name="실행오류", sql="SELECT 1", condition="gt:0")

        mock_conn = MagicMock()
        mock_conn.cursor.side_effect = Exception("쿼리 실패")

        fake_connections = {conn_id: _make_conn_info(conn_id)}
        with patch("bi_agent_mcp.tools.db._connections", fake_connections), \
             patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn):
            result = check_alerts()
        assert "[ERROR]" in result

    def test_fetchone_returns_none(self, patch_alerts_file):
        """fetchone 결과 없음 → 오류 행 (lines 143-144)."""
        conn_id = "pg_none_row"
        create_alert(conn_id=conn_id, name="빈결과", sql="SELECT 1", condition="gt:0")

        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur

        fake_connections = {conn_id: _make_conn_info(conn_id)}
        with patch("bi_agent_mcp.tools.db._connections", fake_connections), \
             patch("bi_agent_mcp.tools.db._get_conn", return_value=mock_conn):
            result = check_alerts()
        assert "결과 없음" in result or "[ERROR]" in result
