"""bi_agent_mcp.auth.credentials 단위 테스트."""
import os
from unittest.mock import MagicMock, patch

import pytest

import bi_agent_mcp.auth.credentials as creds_module
from bi_agent_mcp.auth.credentials import (
    delete_secret,
    get_env_or_secret,
    get_secret,
    mask_password,
    store_secret,
)


class TestStoreSecret:
    def test_store_uses_keyring_when_available(self):
        mock_keyring = MagicMock()
        with patch.object(creds_module, "_KEYRING_AVAILABLE", True), \
             patch.object(creds_module, "keyring", mock_keyring, create=True):
            store_secret("svc", "key", "val")
            mock_keyring.set_password.assert_called_once_with("svc", "key", "val")

    def test_store_uses_memory_when_keyring_unavailable(self):
        with patch.object(creds_module, "_KEYRING_AVAILABLE", False):
            creds_module._memory_store.clear()
            store_secret("svc", "key", "val")
            assert creds_module._memory_store.get("svc:key") == "val"


class TestGetSecret:
    def test_get_uses_keyring_when_available(self):
        mock_keyring = MagicMock()
        mock_keyring.get_password.return_value = "stored"
        with patch.object(creds_module, "_KEYRING_AVAILABLE", True), \
             patch.object(creds_module, "keyring", mock_keyring, create=True):
            result = get_secret("svc", "key")
            assert result == "stored"

    def test_get_uses_memory_when_keyring_unavailable(self):
        with patch.object(creds_module, "_KEYRING_AVAILABLE", False):
            creds_module._memory_store["svc:key"] = "mem_val"
            result = get_secret("svc", "key")
            assert result == "mem_val"

    def test_get_returns_none_when_missing(self):
        with patch.object(creds_module, "_KEYRING_AVAILABLE", False):
            creds_module._memory_store.clear()
            result = get_secret("svc", "nonexistent")
            assert result is None


class TestDeleteSecret:
    def test_delete_uses_keyring_when_available(self):
        mock_keyring = MagicMock()
        mock_keyring.errors = MagicMock()
        mock_keyring.errors.PasswordDeleteError = Exception
        with patch.object(creds_module, "_KEYRING_AVAILABLE", True), \
             patch.object(creds_module, "keyring", mock_keyring, create=True):
            delete_secret("svc", "key")
            mock_keyring.delete_password.assert_called_once_with("svc", "key")

    def test_delete_uses_memory_when_keyring_unavailable(self):
        with patch.object(creds_module, "_KEYRING_AVAILABLE", False):
            creds_module._memory_store["svc:key"] = "val"
            delete_secret("svc", "key")
            assert "svc:key" not in creds_module._memory_store

    def test_delete_keyring_password_delete_error_is_ignored(self):
        mock_keyring = MagicMock()
        mock_keyring.errors = MagicMock()
        mock_keyring.errors.PasswordDeleteError = ValueError
        mock_keyring.delete_password.side_effect = ValueError("not found")
        with patch.object(creds_module, "_KEYRING_AVAILABLE", True), \
             patch.object(creds_module, "keyring", mock_keyring, create=True):
            # Should not raise
            delete_secret("svc", "key")


class TestGetEnvOrSecret:
    def test_env_var_takes_priority(self, monkeypatch):
        monkeypatch.setenv("MY_VAR", "from_env")
        with patch.object(creds_module, "_KEYRING_AVAILABLE", False):
            result = get_env_or_secret("MY_VAR", "svc", "key")
        assert result == "from_env"

    def test_falls_back_to_secret_when_env_missing(self, monkeypatch):
        monkeypatch.delenv("MY_VAR", raising=False)
        with patch.object(creds_module, "_KEYRING_AVAILABLE", False):
            creds_module._memory_store["svc:key"] = "from_secret"
            result = get_env_or_secret("MY_VAR", "svc", "key")
        assert result == "from_secret"

    def test_returns_none_when_both_missing(self, monkeypatch):
        monkeypatch.delenv("MY_VAR", raising=False)
        with patch.object(creds_module, "_KEYRING_AVAILABLE", False):
            creds_module._memory_store.clear()
            result = get_env_or_secret("MY_VAR", "svc", "key")
        assert result is None


class TestMaskPassword:
    def test_returns_asterisks(self):
        assert mask_password("super_secret_123") == "****"

    def test_short_value_also_masked(self):
        assert mask_password("x") == "****"

    def test_empty_string_masked(self):
        assert mask_password("") == "****"
