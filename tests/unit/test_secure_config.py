"""SecureConfig 단위 테스트."""
import json
from pathlib import Path
from unittest.mock import patch
import pytest


def test_save_and_load_non_sensitive_fields(tmp_path):
    from bi_agent_mcp.tools.core.secure_config import SecureConfig
    cfg = SecureConfig(config_dir=tmp_path)
    cfg.save_connection("mydb", {"host": "localhost", "port": 5432, "db_type": "postgresql"})
    loaded = cfg.load_connection("mydb")
    assert loaded["host"] == "localhost"
    assert loaded["db_type"] == "postgresql"


def test_sensitive_fields_not_stored_in_json(tmp_path):
    from bi_agent_mcp.tools.core.secure_config import SecureConfig
    cfg = SecureConfig(config_dir=tmp_path)
    with patch.object(cfg, "_keyring_set") as mock_ks:
        cfg.save_connection("mydb", {"host": "localhost", "password": "secret123"})
    config_file = tmp_path / "config.json"
    raw = json.loads(config_file.read_text())
    assert "password" not in raw.get("mydb", {})
    mock_ks.assert_called_once_with("mydb", "password", "secret123")


def test_load_returns_none_for_unknown_conn(tmp_path):
    from bi_agent_mcp.tools.core.secure_config import SecureConfig
    cfg = SecureConfig(config_dir=tmp_path)
    assert cfg.load_connection("unknown") is None


def test_list_connections_returns_all_saved(tmp_path):
    from bi_agent_mcp.tools.core.secure_config import SecureConfig
    cfg = SecureConfig(config_dir=tmp_path)
    cfg.save_connection("db1", {"host": "h1"})
    cfg.save_connection("db2", {"host": "h2"})
    ids = cfg.list_connections()
    assert set(ids) == {"db1", "db2"}


def test_delete_connection(tmp_path):
    from bi_agent_mcp.tools.core.secure_config import SecureConfig
    cfg = SecureConfig(config_dir=tmp_path)
    cfg.save_connection("db1", {"host": "h1"})
    cfg.delete_connection("db1")
    assert cfg.load_connection("db1") is None
