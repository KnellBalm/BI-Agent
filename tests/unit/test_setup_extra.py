"""bi_agent_mcp.tools.setup 추가 단위 테스트 — test_datasource, _test_* 함수."""
import pytest
from unittest.mock import MagicMock, patch

from bi_agent_mcp.tools.setup import (
    test_datasource as run_test_datasource,
    configure_datasource,
    check_setup_status,
)


class TestConfigureDatasource:
    def test_invalid_source_type_returns_error(self):
        result = configure_datasource("oracle", {"host": "localhost"})
        assert "유효하지 않은" in result

    def test_postgresql_saves_with_db_key(self, tmp_path):
        mock_cm = MagicMock()
        with patch("bi_agent_mcp.config_manager.ConfigManager", return_value=mock_cm):
            result = configure_datasource("postgresql", {"host": "localhost", "port": 5432}, {"password": "pw"})
        assert "postgresql" in result
        mock_cm.save_datasource.assert_called_once()
        call_args = mock_cm.save_datasource.call_args
        assert call_args[0][0] == "db"
        assert call_args[0][1]["type"] == "postgresql"

    def test_mysql_saves_with_db_key(self, tmp_path):
        mock_cm = MagicMock()
        with patch("bi_agent_mcp.config_manager.ConfigManager", return_value=mock_cm):
            result = configure_datasource("mysql", {"host": "localhost"}, {"password": "pw"})
        assert "mysql" in result
        call_args = mock_cm.save_datasource.call_args
        assert call_args[0][0] == "db"
        assert call_args[0][1]["type"] == "mysql"

    def test_ga4_saves_with_ga4_key(self):
        mock_cm = MagicMock()
        with patch("bi_agent_mcp.config_manager.ConfigManager", return_value=mock_cm):
            result = configure_datasource("ga4", {"property_id": "123"}, {"client_secret": "sec"})
        assert "ga4" in result
        call_args = mock_cm.save_datasource.call_args
        assert call_args[0][0] == "ga4"

    def test_amplitude_saves_with_amplitude_key(self):
        mock_cm = MagicMock()
        with patch("bi_agent_mcp.config_manager.ConfigManager", return_value=mock_cm):
            result = configure_datasource("amplitude", {}, {"api_key": "key", "secret_key": "sec"})
        assert "amplitude" in result

    def test_secret_count_shown_in_result(self):
        mock_cm = MagicMock()
        with patch("bi_agent_mcp.config_manager.ConfigManager", return_value=mock_cm):
            result = configure_datasource("postgresql", {"host": "h"}, {"password": "pw"})
        assert "keyring" in result or "시크릿" in result

    def test_no_secrets_no_security_note(self):
        mock_cm = MagicMock()
        with patch("bi_agent_mcp.config_manager.ConfigManager", return_value=mock_cm):
            result = configure_datasource("bigquery", {"project_id": "proj"}, {})
        assert "✅" in result

    def test_exception_returns_error(self):
        with patch("bi_agent_mcp.config_manager.ConfigManager", side_effect=Exception("DB 오류")):
            result = configure_datasource("postgresql", {"host": "h"})
        assert "❌" in result


class TestTestDatasource:
    def test_invalid_source_type_returns_error(self):
        result = run_test_datasource("oracle")
        assert "유효하지 않은" in result

    def test_postgresql_no_config_returns_not_set(self):
        mock_cm = MagicMock()
        mock_cm.load_datasource.return_value = {}
        with patch("bi_agent_mcp.config_manager.ConfigManager", return_value=mock_cm), \
             patch("bi_agent_mcp.config") as mock_cfg:
            mock_cfg.PG_HOST = ""
            mock_cfg.PG_DBNAME = ""
            result = run_test_datasource("postgresql")
        assert "❌" in result

    def test_postgresql_connection_failure(self):
        import psycopg2
        mock_cm = MagicMock()
        mock_cm.load_datasource.return_value = {"host": "h", "database": "db", "user": "u", "password": "p"}
        with patch("bi_agent_mcp.config_manager.ConfigManager", return_value=mock_cm), \
             patch("bi_agent_mcp.config") as mock_cfg, \
             patch("psycopg2.connect", side_effect=Exception("connection refused")):
            mock_cfg.PG_HOST = ""
            mock_cfg.PG_DBNAME = ""
            result = run_test_datasource("postgresql")
        assert "❌" in result

    def test_mysql_no_config_returns_not_set(self):
        mock_cm = MagicMock()
        mock_cm.load_datasource.return_value = {}
        with patch("bi_agent_mcp.config_manager.ConfigManager", return_value=mock_cm), \
             patch("bi_agent_mcp.config") as mock_cfg:
            mock_cfg.MYSQL_HOST = ""
            mock_cfg.MYSQL_DBNAME = ""
            result = run_test_datasource("mysql")
        assert "❌" in result

    def test_bigquery_no_project_returns_not_set(self):
        mock_cm = MagicMock()
        mock_cm.load_datasource.return_value = {}
        with patch("bi_agent_mcp.config_manager.ConfigManager", return_value=mock_cm), \
             patch("bi_agent_mcp.config") as mock_cfg:
            mock_cfg.BQ_PROJECT_ID = ""
            result = run_test_datasource("bigquery")
        assert "❌" in result

    def test_ga4_no_client_id_returns_not_set(self):
        mock_cm = MagicMock()
        mock_cm.load_datasource.return_value = {}
        with patch("bi_agent_mcp.config_manager.ConfigManager", return_value=mock_cm), \
             patch("bi_agent_mcp.config") as mock_cfg:
            mock_cfg.GOOGLE_CLIENT_ID = ""
            result = run_test_datasource("ga4")
        assert "❌" in result

    def test_ga4_with_client_id_returns_ok(self):
        mock_cm = MagicMock()
        mock_cm.load_datasource.return_value = {"client_id": "xxx.apps.googleusercontent.com"}
        with patch("bi_agent_mcp.config_manager.ConfigManager", return_value=mock_cm), \
             patch("bi_agent_mcp.config") as mock_cfg:
            mock_cfg.GOOGLE_CLIENT_ID = ""
            result = run_test_datasource("ga4")
        assert "✅" in result

    def test_amplitude_no_api_key_returns_not_set(self):
        mock_cm = MagicMock()
        mock_cm.load_datasource.return_value = {}
        with patch("bi_agent_mcp.config_manager.ConfigManager", return_value=mock_cm), \
             patch("bi_agent_mcp.config") as mock_cfg:
            mock_cfg.AMPLITUDE_API_KEY = ""
            result = run_test_datasource("amplitude")
        assert "❌" in result

    def test_amplitude_with_api_key_returns_ok(self):
        mock_cm = MagicMock()
        mock_cm.load_datasource.return_value = {"api_key": "mykey"}
        with patch("bi_agent_mcp.config_manager.ConfigManager", return_value=mock_cm), \
             patch("bi_agent_mcp.config") as mock_cfg:
            mock_cfg.AMPLITUDE_API_KEY = ""
            result = run_test_datasource("amplitude")
        assert "✅" in result


class TestCheckSetupStatus:
    def test_exception_returns_error_message(self):
        with patch("bi_agent_mcp.config_manager.ConfigManager", side_effect=Exception("DB 오류")):
            result = check_setup_status()
        assert "오류" in result

    def test_all_configured_shows_all_set(self):
        mock_cm = MagicMock()
        mock_cm.list_datasources.return_value = {
            "db": {"configured": True, "type": "postgresql", "host": "localhost"},
            "ga4": {"configured": True, "property_id": "123"},
            "amplitude": {"configured": True},
        }
        mock_cm.get_missing_config.return_value = []
        with patch("bi_agent_mcp.config_manager.ConfigManager", return_value=mock_cm):
            result = check_setup_status()
        assert "✅" in result
