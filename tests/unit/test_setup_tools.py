"""setup.py 및 setup_cli._parse_db_url 단위 테스트."""

from unittest.mock import MagicMock, patch

import pytest

from bi_agent_mcp.tools.setup import check_setup_status, configure_datasource
from bi_agent_mcp.setup_cli import _parse_db_url


class TestCheckSetupStatus:
    def _make_sources(self, db=False, ga4=False, amplitude=False):
        return {
            "db": {"configured": db, "type": "postgresql" if db else None, "host": "localhost" if db else None},
            "ga4": {"configured": ga4, "property_id": "123" if ga4 else None},
            "amplitude": {"configured": amplitude},
        }

    def test_all_not_configured_shows_not_set(self):
        sources = self._make_sources()
        with patch("bi_agent_mcp.config_manager.ConfigManager") as MockCM:
            instance = MockCM.return_value
            instance.list_datasources.return_value = sources
            instance.get_missing_config.return_value = ["db", "ga4", "amplitude"]

            result = check_setup_status()

        assert "❌ 미설정" in result

    def test_db_configured_shows_configured(self):
        sources = self._make_sources(db=True)
        with patch("bi_agent_mcp.config_manager.ConfigManager") as MockCM:
            instance = MockCM.return_value
            instance.list_datasources.return_value = sources
            instance.get_missing_config.return_value = ["ga4", "amplitude"]

            result = check_setup_status()

        assert "✅ 설정됨" in result

    def test_all_configured_no_instructions(self):
        sources = self._make_sources(db=True, ga4=True, amplitude=True)
        with patch("bi_agent_mcp.config_manager.ConfigManager") as MockCM:
            instance = MockCM.return_value
            instance.list_datasources.return_value = sources
            instance.get_missing_config.return_value = []

            result = check_setup_status()

        assert "configure_datasource" not in result
        assert "모든 데이터 소스가 설정되어 있습니다" in result

    def test_result_contains_section_header(self):
        sources = self._make_sources()
        with patch("bi_agent_mcp.config_manager.ConfigManager") as MockCM:
            instance = MockCM.return_value
            instance.list_datasources.return_value = sources
            instance.get_missing_config.return_value = ["db", "ga4", "amplitude"]

            result = check_setup_status()

        assert "BI-Agent 설정 상태" in result


class TestConfigureDatasource:
    def test_invalid_source_type_returns_error(self):
        result = configure_datasource("oracle", {})
        assert "❌" in result
        assert "oracle" in result

    def test_invalid_source_type_lists_valid_types(self):
        result = configure_datasource("unknown_db", {})
        assert "postgresql" in result

    def test_postgresql_normalized_to_db_category(self):
        mock_cm = MagicMock()
        with patch("bi_agent_mcp.config_manager.ConfigManager", return_value=mock_cm):
            configure_datasource("postgresql", {"host": "localhost", "port": 5432})

        call_args = mock_cm.save_datasource.call_args
        assert call_args[0][0] == "db"
        assert call_args[0][1]["type"] == "postgresql"

    def test_mysql_normalized_to_db_category(self):
        mock_cm = MagicMock()
        with patch("bi_agent_mcp.config_manager.ConfigManager", return_value=mock_cm):
            configure_datasource("mysql", {"host": "localhost", "port": 3306})

        call_args = mock_cm.save_datasource.call_args
        assert call_args[0][0] == "db"
        assert call_args[0][1]["type"] == "mysql"

    def test_bigquery_normalized_to_db_category(self):
        mock_cm = MagicMock()
        with patch("bi_agent_mcp.config_manager.ConfigManager", return_value=mock_cm):
            configure_datasource("bigquery", {"project_id": "my-project"})

        call_args = mock_cm.save_datasource.call_args
        assert call_args[0][0] == "db"
        assert call_args[0][1]["type"] == "bigquery"

    def test_ga4_not_normalized(self):
        mock_cm = MagicMock()
        with patch("bi_agent_mcp.config_manager.ConfigManager", return_value=mock_cm):
            configure_datasource("ga4", {"property_id": "12345"})

        call_args = mock_cm.save_datasource.call_args
        assert call_args[0][0] == "ga4"

    def test_success_message_contains_source_type(self):
        mock_cm = MagicMock()
        with patch("bi_agent_mcp.config_manager.ConfigManager", return_value=mock_cm):
            result = configure_datasource("postgresql", {"host": "localhost"})

        assert "postgresql" in result
        assert "✅" in result

    def test_success_message_contains_source_type_amplitude(self):
        mock_cm = MagicMock()
        with patch("bi_agent_mcp.config_manager.ConfigManager", return_value=mock_cm):
            result = configure_datasource("amplitude", {}, secrets={"api_key": "key123"})

        assert "amplitude" in result
        assert "✅" in result

    def test_secrets_passed_to_save_datasource(self):
        mock_cm = MagicMock()
        with patch("bi_agent_mcp.config_manager.ConfigManager", return_value=mock_cm):
            configure_datasource("postgresql", {"host": "localhost"}, secrets={"password": "mypass"})

        call_args = mock_cm.save_datasource.call_args
        assert call_args[0][2] == {"password": "mypass"}

    def test_secret_count_shown_in_message_when_secrets_provided(self):
        mock_cm = MagicMock()
        with patch("bi_agent_mcp.config_manager.ConfigManager", return_value=mock_cm):
            result = configure_datasource("postgresql", {"host": "localhost"}, secrets={"password": "pass"})

        assert "keyring" in result or "시크릿" in result


class TestParsDbUrl:
    def test_postgresql_url_parsed(self):
        result = _parse_db_url("postgresql://admin@localhost/mydb")
        assert result is not None
        db_type, env_params, secrets = result
        assert db_type == "postgresql"
        assert env_params["BI_AGENT_PG_HOST"] == "localhost"
        assert env_params["BI_AGENT_PG_DBNAME"] == "mydb"
        assert env_params["BI_AGENT_PG_USER"] == "admin"

    def test_postgres_scheme_alias(self):
        result = _parse_db_url("postgres://user@localhost/db")
        assert result is not None
        db_type, _, _ = result
        assert db_type == "postgresql"

    def test_mysql_url_parsed(self):
        result = _parse_db_url("mysql://root@127.0.0.1:3306/testdb")
        assert result is not None
        db_type, env_params, secrets = result
        assert db_type == "mysql"
        assert env_params["BI_AGENT_MYSQL_HOST"] == "127.0.0.1"
        assert env_params["BI_AGENT_MYSQL_PORT"] == "3306"
        assert env_params["BI_AGENT_MYSQL_DBNAME"] == "testdb"

    def test_invalid_scheme_returns_none(self):
        result = _parse_db_url("oracle://user@host/db")
        assert result is None

    def test_password_extracted_to_secrets(self):
        result = _parse_db_url("postgresql://user:s3cr3t@localhost/mydb")
        assert result is not None
        _, _, secrets = result
        assert secrets["password"] == "s3cr3t"

    def test_password_empty_string_when_absent(self):
        result = _parse_db_url("postgresql://user@localhost/mydb")
        assert result is not None
        _, _, secrets = result
        assert secrets["password"] == ""

    def test_default_port_used_when_absent_postgresql(self):
        result = _parse_db_url("postgresql://user@localhost/mydb")
        assert result is not None
        _, env_params, _ = result
        assert env_params["BI_AGENT_PG_PORT"] == "5432"

    def test_default_port_used_when_absent_mysql(self):
        result = _parse_db_url("mysql://root@localhost/db")
        assert result is not None
        _, env_params, _ = result
        assert env_params["BI_AGENT_MYSQL_PORT"] == "3306"

    def test_completely_invalid_url_returns_none(self):
        result = _parse_db_url("not-a-url-at-all")
        assert result is None


# ─── Extended tests for test_datasource and private helpers ───────────────────

from bi_agent_mcp.tools.setup import _test_postgresql, _test_mysql, _test_bigquery, _test_ga4, _test_amplitude
from bi_agent_mcp.tools.setup import test_datasource as run_test_datasource


class TestTestDatasource:
    def test_invalid_type_returns_error(self):
        result = run_test_datasource("invalid_db")
        assert "❌" in result
        assert "유효하지 않은" in result

    def test_postgresql_routing(self):
        with patch("bi_agent_mcp.tools.setup._test_postgresql", return_value="✅ PG OK") as mock_fn:
            result = run_test_datasource("postgresql")
        assert result == "✅ PG OK"

    def test_mysql_routing(self):
        with patch("bi_agent_mcp.tools.setup._test_mysql", return_value="✅ MySQL OK"):
            result = run_test_datasource("mysql")
        assert result == "✅ MySQL OK"

    def test_bigquery_routing(self):
        with patch("bi_agent_mcp.tools.setup._test_bigquery", return_value="✅ BQ OK"):
            result = run_test_datasource("bigquery")
        assert result == "✅ BQ OK"

    def test_ga4_routing(self):
        with patch("bi_agent_mcp.tools.setup._test_ga4", return_value="✅ GA4 OK"):
            result = run_test_datasource("ga4")
        assert result == "✅ GA4 OK"

    def test_amplitude_routing(self):
        with patch("bi_agent_mcp.tools.setup._test_amplitude", return_value="✅ Amp OK"):
            result = run_test_datasource("amplitude")
        assert result == "✅ Amp OK"

    def test_exception_returns_error(self):
        with patch("bi_agent_mcp.tools.setup._test_postgresql", side_effect=RuntimeError("crash")):
            result = run_test_datasource("postgresql")
        assert "❌" in result


class TestTestPostgresql:
    def test_import_error_returns_message(self):
        with patch.dict("sys.modules", {"psycopg2": None}):
            result = _test_postgresql()
        assert "psycopg2" in result or "❌" in result

    def test_no_config_returns_message(self):
        with patch("bi_agent_mcp.tools.setup.psycopg2" if False else "builtins.__import__", side_effect=ImportError):
            pass
        mock_psycopg2 = MagicMock()
        mock_psycopg2.connect.side_effect = Exception("connection refused")
        with patch.dict("sys.modules", {"psycopg2": mock_psycopg2}), \
             patch("bi_agent_mcp.config_manager.ConfigManager") as MockCM:
            instance = MockCM.return_value
            instance.load_datasource.return_value = {}
            with patch("bi_agent_mcp.config.PG_HOST", ""), \
                 patch("bi_agent_mcp.config.PG_DBNAME", ""):
                result = _test_postgresql()
        assert "설정이 없습니다" in result or "❌" in result

    def test_connection_success(self):
        mock_psycopg2 = MagicMock()
        mock_conn = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        with patch.dict("sys.modules", {"psycopg2": mock_psycopg2}), \
             patch("bi_agent_mcp.config.PG_HOST", "localhost"), \
             patch("bi_agent_mcp.config.PG_DBNAME", "mydb"), \
             patch("bi_agent_mcp.config.PG_USER", "admin"), \
             patch("bi_agent_mcp.config.PG_PASSWORD", "pass"), \
             patch("bi_agent_mcp.config.PG_PORT", 5432):
            result = _test_postgresql()
        assert "✅" in result

    def test_connection_failure(self):
        mock_psycopg2 = MagicMock()
        mock_psycopg2.connect.side_effect = Exception("timeout")
        with patch.dict("sys.modules", {"psycopg2": mock_psycopg2}), \
             patch("bi_agent_mcp.config.PG_HOST", "localhost"), \
             patch("bi_agent_mcp.config.PG_DBNAME", "mydb"), \
             patch("bi_agent_mcp.config.PG_USER", "admin"), \
             patch("bi_agent_mcp.config.PG_PASSWORD", "pass"), \
             patch("bi_agent_mcp.config.PG_PORT", 5432):
            result = _test_postgresql()
        assert "❌" in result and "실패" in result


class TestTestMysql:
    def test_import_error(self):
        with patch.dict("sys.modules", {"pymysql": None}):
            result = _test_mysql()
        assert "pymysql" in result or "❌" in result

    def test_no_config_returns_message(self):
        mock_pymysql = MagicMock()
        mock_pymysql.connect.side_effect = Exception("no db")
        with patch.dict("sys.modules", {"pymysql": mock_pymysql}), \
             patch("bi_agent_mcp.config_manager.ConfigManager") as MockCM:
            instance = MockCM.return_value
            instance.load_datasource.return_value = {}
            with patch("bi_agent_mcp.config.MYSQL_HOST", ""), \
                 patch("bi_agent_mcp.config.MYSQL_DBNAME", ""):
                result = _test_mysql()
        assert "설정이 없습니다" in result or "❌" in result

    def test_connection_success(self):
        mock_pymysql = MagicMock()
        mock_conn = MagicMock()
        mock_pymysql.connect.return_value = mock_conn
        with patch.dict("sys.modules", {"pymysql": mock_pymysql}), \
             patch("bi_agent_mcp.config.MYSQL_HOST", "localhost"), \
             patch("bi_agent_mcp.config.MYSQL_DBNAME", "testdb"), \
             patch("bi_agent_mcp.config.MYSQL_USER", "root"), \
             patch("bi_agent_mcp.config.MYSQL_PASSWORD", "pw"), \
             patch("bi_agent_mcp.config.MYSQL_PORT", 3306):
            result = _test_mysql()
        assert "✅" in result


class TestTestBigquery:
    def test_import_error(self):
        with patch.dict("sys.modules", {"google.cloud": None, "google.cloud.bigquery": None}):
            result = _test_bigquery()
        assert "❌" in result

    def test_no_project_id_returns_message(self):
        mock_bq = MagicMock()
        with patch.dict("sys.modules", {"google.cloud": MagicMock(), "google.cloud.bigquery": mock_bq}), \
             patch("bi_agent_mcp.config.BQ_PROJECT_ID", ""), \
             patch("bi_agent_mcp.config_manager.ConfigManager") as MockCM:
            instance = MockCM.return_value
            instance.load_datasource.return_value = {}
            result = _test_bigquery()
        assert "설정이 없습니다" in result or "❌" in result


class TestTestGa4:
    def test_no_client_id_returns_message(self):
        with patch("bi_agent_mcp.config.GOOGLE_CLIENT_ID", ""), \
             patch("bi_agent_mcp.config_manager.ConfigManager") as MockCM:
            instance = MockCM.return_value
            instance.load_datasource.return_value = {}
            result = _test_ga4()
        assert "설정이 없습니다" in result or "❌" in result

    def test_client_id_exists_returns_ok(self):
        with patch("bi_agent_mcp.config.GOOGLE_CLIENT_ID", "client_123.apps.googleusercontent.com"):
            result = _test_ga4()
        assert "✅" in result


class TestTestAmplitude:
    def test_no_api_key_returns_message(self):
        with patch("bi_agent_mcp.config.AMPLITUDE_API_KEY", ""), \
             patch("bi_agent_mcp.config_manager.ConfigManager") as MockCM:
            instance = MockCM.return_value
            instance.load_datasource.return_value = {}
            result = _test_amplitude()
        assert "설정이 없습니다" in result or "❌" in result

    def test_api_key_in_config(self):
        with patch("bi_agent_mcp.config.AMPLITUDE_API_KEY", "my_api_key_123"):
            result = _test_amplitude()
        assert "✅" in result


class TestConfigureDatasourceExtended:
    def test_save_exception_returns_error(self):
        with patch("bi_agent_mcp.config_manager.ConfigManager") as MockCM:
            instance = MockCM.return_value
            instance.save_datasource.side_effect = Exception("keyring error")
            result = configure_datasource("postgresql", {"host": "localhost"}, {"password": "pw"})
        assert "❌" in result
        assert "오류" in result


class TestCheckSetupStatusExtended:
    def test_exception_returns_error_message(self):
        with patch("bi_agent_mcp.config_manager.ConfigManager", side_effect=Exception("init error")):
            result = check_setup_status()
        assert "오류" in result
