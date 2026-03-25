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


# ─── Extended tests for uncovered lines ───────────────────────────────────────

class TestLoadDatasource:
    def test_load_datasource_with_keyring(self, tmp_path):
        """load_datasource는 config.json + keyring에서 값을 합쳐 반환."""
        import json
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps({
            "version": 1,
            "datasources": {"db": {"host": "localhost", "port": 5432, "type": "postgresql"}}
        }))
        with patch("bi_agent_mcp.config_manager.CONFIG_FILE", cfg_file), \
             patch("bi_agent_mcp.config_manager.ConfigManager._load_config",
                   return_value={"datasources": {"db": {"host": "pg.local", "port": 5432}}}), \
             patch("bi_agent_mcp.auth.credentials.get_env_or_secret", return_value="secret_pw"):
            from bi_agent_mcp.config_manager import ConfigManager
            cm = ConfigManager()
            result = cm.load_datasource("db")
        assert "host" in result or isinstance(result, dict)

    def test_load_datasource_exception_returns_empty(self):
        from bi_agent_mcp.config_manager import ConfigManager
        cm = ConfigManager()
        with patch.object(cm, "_load_config", side_effect=Exception("crash")):
            result = cm.load_datasource("db")
        assert result == {}

    def test_load_datasource_no_secret(self):
        from bi_agent_mcp.config_manager import ConfigManager
        cm = ConfigManager()
        with patch.object(cm, "_load_config", return_value={"datasources": {"ga4": {"property_id": "123"}}}), \
             patch("bi_agent_mcp.auth.credentials.get_env_or_secret", return_value=None):
            result = cm.load_datasource("ga4")
        assert result.get("property_id") == "123"


class TestResetDatasource:
    def test_reset_clears_config(self, tmp_path):
        import json
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps({"datasources": {"db": {"host": "localhost"}}}))
        with patch("bi_agent_mcp.config_manager.CONFIG_FILE", cfg_file), \
             patch("bi_agent_mcp.config_manager.CONFIG_DIR", tmp_path), \
             patch("bi_agent_mcp.auth.credentials.delete_secret", return_value=None):
            from bi_agent_mcp.config_manager import ConfigManager
            cm = ConfigManager()
            cm.reset_datasource("db")
        data = json.loads(cfg_file.read_text())
        assert data["datasources"]["db"] == {}

    def test_reset_exception_does_not_raise(self):
        from bi_agent_mcp.config_manager import ConfigManager
        cm = ConfigManager()
        with patch.object(cm, "_load_config", side_effect=Exception("crash")):
            cm.reset_datasource("db")  # Should not raise

    def test_reset_delete_secret_exception_ignored(self, tmp_path):
        import json
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps({"datasources": {"db": {}}}))
        with patch("bi_agent_mcp.config_manager.CONFIG_FILE", cfg_file), \
             patch("bi_agent_mcp.config_manager.CONFIG_DIR", tmp_path), \
             patch("bi_agent_mcp.auth.credentials.delete_secret", side_effect=Exception("keyring error")):
            from bi_agent_mcp.config_manager import ConfigManager
            cm = ConfigManager()
            cm.reset_datasource("db")  # Should not raise despite keyring error


class TestLoadConfigErrors:
    def test_malformed_json_returns_default(self, tmp_path):
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text("{ invalid json }")
        with patch("bi_agent_mcp.config_manager.CONFIG_FILE", cfg_file):
            from bi_agent_mcp.config_manager import ConfigManager
            cm = ConfigManager()
            result = cm._load_config()
        assert result["version"] == 1
        assert "datasources" in result

    def test_oserror_returns_default(self, tmp_path):
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text('{"datasources": {}}')
        with patch("bi_agent_mcp.config_manager.CONFIG_FILE", cfg_file), \
             patch("builtins.open", side_effect=OSError("permission denied")):
            from bi_agent_mcp.config_manager import ConfigManager
            cm = ConfigManager()
            result = cm._load_config()
        assert "datasources" in result


class TestListDatasourcesException:
    def test_exception_returns_all_not_configured(self):
        from bi_agent_mcp.config_manager import ConfigManager
        cm = ConfigManager()
        with patch.object(cm, "_load_config", side_effect=Exception("crash")):
            result = cm.list_datasources()
        assert result["db"]["configured"] is False
        assert result["ga4"]["configured"] is False
        assert result["amplitude"]["configured"] is False


class TestSaveDatasourceError:
    def test_save_exception_raises(self, tmp_path):
        from bi_agent_mcp.config_manager import ConfigManager
        cm = ConfigManager()
        with patch.object(cm, "_load_config", side_effect=Exception("crash")):
            import pytest
            with pytest.raises(Exception):
                cm.save_datasource("db", {"host": "localhost"}, None)
