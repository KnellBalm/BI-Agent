"""ConfigManager 단위 테스트."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bi_agent_mcp.config_manager import ConfigManager


def _make_manager(tmp_path: Path):
    """tmp_path를 CONFIG_DIR/CONFIG_FILE로 패치한 ConfigManager 반환."""
    config_dir = tmp_path / "bi-agent"
    config_file = config_dir / "config.json"
    with (
        patch("bi_agent_mcp.config_manager.CONFIG_DIR", config_dir),
        patch("bi_agent_mcp.config_manager.CONFIG_FILE", config_file),
    ):
        yield ConfigManager(), config_dir, config_file


class TestConfigManagerSaveDatasource:
    def test_roundtrip_saves_params_to_config_file(self, tmp_path):
        config_dir = tmp_path / "bi-agent"
        config_file = config_dir / "config.json"

        with (
            patch("bi_agent_mcp.config_manager.CONFIG_DIR", config_dir),
            patch("bi_agent_mcp.config_manager.CONFIG_FILE", config_file),
            patch("bi_agent_mcp.auth.credentials.store_secret"),
        ):
            cm = ConfigManager()
            params = {"host": "localhost", "port": 5432, "database": "testdb", "user": "admin", "type": "postgresql"}
            cm.save_datasource("db", params)

            assert config_file.exists()
            data = json.loads(config_file.read_text())
            assert data["datasources"]["db"]["host"] == "localhost"
            assert data["datasources"]["db"]["database"] == "testdb"

    def test_roundtrip_load_config_after_save(self, tmp_path):
        config_dir = tmp_path / "bi-agent"
        config_file = config_dir / "config.json"

        with (
            patch("bi_agent_mcp.config_manager.CONFIG_DIR", config_dir),
            patch("bi_agent_mcp.config_manager.CONFIG_FILE", config_file),
            patch("bi_agent_mcp.auth.credentials.store_secret"),
        ):
            cm = ConfigManager()
            params = {"host": "db.example.com", "port": 3306, "type": "mysql"}
            cm.save_datasource("db", params)

            loaded = cm._load_config()
            assert loaded["datasources"]["db"]["host"] == "db.example.com"
            assert loaded["datasources"]["db"]["type"] == "mysql"

    def test_secrets_delegated_to_store_secret(self, tmp_path):
        config_dir = tmp_path / "bi-agent"
        config_file = config_dir / "config.json"
        mock_store = MagicMock()

        with (
            patch("bi_agent_mcp.config_manager.CONFIG_DIR", config_dir),
            patch("bi_agent_mcp.config_manager.CONFIG_FILE", config_file),
            patch("bi_agent_mcp.auth.credentials.store_secret", mock_store),
        ):
            cm = ConfigManager()
            cm.save_datasource("db", {"host": "localhost"}, secrets={"password": "s3cret"})

            mock_store.assert_called_once_with("bi-agent", "db_password", "s3cret")

    def test_empty_secret_value_not_stored(self, tmp_path):
        config_dir = tmp_path / "bi-agent"
        config_file = config_dir / "config.json"
        mock_store = MagicMock()

        with (
            patch("bi_agent_mcp.config_manager.CONFIG_DIR", config_dir),
            patch("bi_agent_mcp.config_manager.CONFIG_FILE", config_file),
            patch("bi_agent_mcp.auth.credentials.store_secret", mock_store),
        ):
            cm = ConfigManager()
            cm.save_datasource("db", {"host": "localhost"}, secrets={"password": ""})

            mock_store.assert_not_called()


class TestConfigManagerListDatasources:
    def test_db_configured_true_when_host_present(self, tmp_path):
        config_dir = tmp_path / "bi-agent"
        config_file = config_dir / "config.json"

        config_data = {
            "version": 1,
            "datasources": {
                "db": {"host": "localhost", "type": "postgresql"},
                "ga4": {},
                "amplitude": {},
            },
        }
        config_dir.mkdir(parents=True)
        config_file.write_text(json.dumps(config_data))

        with (
            patch("bi_agent_mcp.config_manager.CONFIG_DIR", config_dir),
            patch("bi_agent_mcp.config_manager.CONFIG_FILE", config_file),
            patch("bi_agent_mcp.auth.credentials.get_env_or_secret", return_value=None),
        ):
            cm = ConfigManager()
            result = cm.list_datasources()

        assert result["db"]["configured"] is True
        assert result["db"]["type"] == "postgresql"

    def test_bigquery_configured_true_without_host(self, tmp_path):
        config_dir = tmp_path / "bi-agent"
        config_file = config_dir / "config.json"

        config_data = {
            "version": 1,
            "datasources": {
                "db": {"type": "bigquery", "project_id": "my-project"},
                "ga4": {},
                "amplitude": {},
            },
        }
        config_dir.mkdir(parents=True)
        config_file.write_text(json.dumps(config_data))

        with (
            patch("bi_agent_mcp.config_manager.CONFIG_DIR", config_dir),
            patch("bi_agent_mcp.config_manager.CONFIG_FILE", config_file),
            patch("bi_agent_mcp.auth.credentials.get_env_or_secret", return_value=None),
        ):
            cm = ConfigManager()
            result = cm.list_datasources()

        assert result["db"]["configured"] is True

    def test_all_false_when_nothing_configured(self, tmp_path):
        config_dir = tmp_path / "bi-agent"
        config_file = config_dir / "config.json"

        # config.json이 없는 상태
        with (
            patch("bi_agent_mcp.config_manager.CONFIG_DIR", config_dir),
            patch("bi_agent_mcp.config_manager.CONFIG_FILE", config_file),
            patch("bi_agent_mcp.auth.credentials.get_env_or_secret", return_value=None),
        ):
            cm = ConfigManager()
            result = cm.list_datasources()

        assert result["db"]["configured"] is False
        assert result["ga4"]["configured"] is False
        assert result["amplitude"]["configured"] is False


class TestConfigManagerMisc:
    def test_is_initialized_false_when_empty(self, tmp_path):
        config_dir = tmp_path / "bi-agent"
        config_file = config_dir / "config.json"

        with (
            patch("bi_agent_mcp.config_manager.CONFIG_DIR", config_dir),
            patch("bi_agent_mcp.config_manager.CONFIG_FILE", config_file),
            patch("bi_agent_mcp.auth.credentials.get_env_or_secret", return_value=None),
        ):
            cm = ConfigManager()
            assert cm.is_initialized() is False

    def test_is_initialized_true_when_db_configured(self, tmp_path):
        config_dir = tmp_path / "bi-agent"
        config_file = config_dir / "config.json"

        config_data = {
            "version": 1,
            "datasources": {
                "db": {"host": "localhost", "type": "postgresql"},
                "ga4": {},
                "amplitude": {},
            },
        }
        config_dir.mkdir(parents=True)
        config_file.write_text(json.dumps(config_data))

        with (
            patch("bi_agent_mcp.config_manager.CONFIG_DIR", config_dir),
            patch("bi_agent_mcp.config_manager.CONFIG_FILE", config_file),
            patch("bi_agent_mcp.auth.credentials.get_env_or_secret", return_value=None),
        ):
            cm = ConfigManager()
            assert cm.is_initialized() is True

    def test_get_missing_config_returns_all_when_empty(self, tmp_path):
        config_dir = tmp_path / "bi-agent"
        config_file = config_dir / "config.json"

        with (
            patch("bi_agent_mcp.config_manager.CONFIG_DIR", config_dir),
            patch("bi_agent_mcp.config_manager.CONFIG_FILE", config_file),
            patch("bi_agent_mcp.auth.credentials.get_env_or_secret", return_value=None),
        ):
            cm = ConfigManager()
            missing = cm.get_missing_config()

        assert "db" in missing
        assert "ga4" in missing
        assert "amplitude" in missing

    def test_get_missing_config_excludes_configured(self, tmp_path):
        config_dir = tmp_path / "bi-agent"
        config_file = config_dir / "config.json"

        config_data = {
            "version": 1,
            "datasources": {
                "db": {"host": "localhost", "type": "postgresql"},
                "ga4": {},
                "amplitude": {},
            },
        }
        config_dir.mkdir(parents=True)
        config_file.write_text(json.dumps(config_data))

        with (
            patch("bi_agent_mcp.config_manager.CONFIG_DIR", config_dir),
            patch("bi_agent_mcp.config_manager.CONFIG_FILE", config_file),
            patch("bi_agent_mcp.auth.credentials.get_env_or_secret", return_value=None),
        ):
            cm = ConfigManager()
            missing = cm.get_missing_config()

        assert "db" not in missing
        assert "ga4" in missing

    def test_reset_datasource_clears_config(self, tmp_path):
        config_dir = tmp_path / "bi-agent"
        config_file = config_dir / "config.json"

        config_data = {
            "version": 1,
            "datasources": {
                "db": {"host": "localhost", "type": "postgresql"},
                "ga4": {},
                "amplitude": {},
            },
        }
        config_dir.mkdir(parents=True)
        config_file.write_text(json.dumps(config_data))

        with (
            patch("bi_agent_mcp.config_manager.CONFIG_DIR", config_dir),
            patch("bi_agent_mcp.config_manager.CONFIG_FILE", config_file),
            patch("bi_agent_mcp.auth.credentials.delete_secret"),
        ):
            cm = ConfigManager()
            cm.reset_datasource("db")
            loaded = cm._load_config()

        assert loaded["datasources"]["db"] == {}

    def test_reset_datasource_calls_delete_secret(self, tmp_path):
        config_dir = tmp_path / "bi-agent"
        config_file = config_dir / "config.json"

        config_data = {
            "version": 1,
            "datasources": {"db": {"host": "localhost"}, "ga4": {}, "amplitude": {}},
        }
        config_dir.mkdir(parents=True)
        config_file.write_text(json.dumps(config_data))

        mock_delete = MagicMock()
        with (
            patch("bi_agent_mcp.config_manager.CONFIG_DIR", config_dir),
            patch("bi_agent_mcp.config_manager.CONFIG_FILE", config_file),
            patch("bi_agent_mcp.auth.credentials.delete_secret", mock_delete),
        ):
            cm = ConfigManager()
            cm.reset_datasource("db")

        # db secret key는 "password"
        mock_delete.assert_called_with("bi-agent", "db_password")
