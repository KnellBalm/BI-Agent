"""bi_agent_mcp.tools.amplitude 단위 테스트."""
import pytest
from unittest.mock import MagicMock, patch


class TestConnectAmplitude:
    def teardown_method(self):
        from bi_agent_mcp.tools import amplitude
        amplitude._amplitude_connections.clear()

    def test_no_keys_no_env_returns_error(self):
        with patch("bi_agent_mcp.tools.amplitude.get_env_or_secret", return_value=None), \
             patch("bi_agent_mcp.tools.amplitude.store_secret"):
            from bi_agent_mcp.tools.amplitude import connect_amplitude
            result = connect_amplitude()
        assert "[ERROR]" in result
        assert "API Key" in result

    def test_http_401_returns_auth_error(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 401

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("bi_agent_mcp.tools.amplitude.get_env_or_secret", return_value=None), \
             patch("bi_agent_mcp.tools.amplitude.store_secret"), \
             patch("bi_agent_mcp.tools.amplitude.httpx.Client", return_value=mock_client):
            from bi_agent_mcp.tools.amplitude import connect_amplitude
            result = connect_amplitude(api_key="bad_key", secret_key="bad_secret")
        assert "[ERROR]" in result
        assert "인증 실패" in result

    def test_http_500_returns_error(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 500

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("bi_agent_mcp.tools.amplitude.get_env_or_secret", return_value=None), \
             patch("bi_agent_mcp.tools.amplitude.store_secret"), \
             patch("bi_agent_mcp.tools.amplitude.httpx.Client", return_value=mock_client):
            from bi_agent_mcp.tools.amplitude import connect_amplitude
            result = connect_amplitude(api_key="key", secret_key="secret")
        assert "[ERROR]" in result

    def test_network_error_returns_error(self):
        import httpx

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = httpx.RequestError("timeout")

        with patch("bi_agent_mcp.tools.amplitude.get_env_or_secret", return_value=None), \
             patch("bi_agent_mcp.tools.amplitude.store_secret"), \
             patch("bi_agent_mcp.tools.amplitude.httpx.Client", return_value=mock_client):
            from bi_agent_mcp.tools.amplitude import connect_amplitude
            result = connect_amplitude(api_key="key", secret_key="secret")
        assert "[ERROR]" in result
        assert "네트워크" in result

    def test_success_registers_connection(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("bi_agent_mcp.tools.amplitude.get_env_or_secret", return_value=None), \
             patch("bi_agent_mcp.tools.amplitude.store_secret"), \
             patch("bi_agent_mcp.tools.amplitude.httpx.Client", return_value=mock_client):
            from bi_agent_mcp.tools import amplitude as amp_module
            amp_module._amplitude_connections.clear()
            result = amp_module.connect_amplitude(api_key="valid_key", secret_key="valid_secret")
        assert "[SUCCESS]" in result
        assert "default" in amp_module._amplitude_connections


class TestGetAmplitudeEvents:
    def setup_method(self):
        from bi_agent_mcp.tools import amplitude
        amplitude._amplitude_connections["default"] = {
            "api_key": "test_key",
            "secret_key": "test_secret",
        }

    def teardown_method(self):
        from bi_agent_mcp.tools import amplitude
        amplitude._amplitude_connections.clear()

    def test_not_connected_returns_error(self):
        from bi_agent_mcp.tools import amplitude
        amplitude._amplitude_connections.clear()
        result = amplitude.get_amplitude_events("Purchase", "20260301", "20260315")
        assert "[ERROR]" in result
        assert "connect_amplitude" in result

    def test_http_401_returns_auth_error(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 401

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("bi_agent_mcp.tools.amplitude.httpx.Client", return_value=mock_client):
            from bi_agent_mcp.tools.amplitude import get_amplitude_events
            result = get_amplitude_events("Purchase", "20260301", "20260315")
        assert "[ERROR]" in result
        assert "인증 실패" in result

    def test_http_429_returns_rate_limit_error(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 429

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("bi_agent_mcp.tools.amplitude.httpx.Client", return_value=mock_client):
            from bi_agent_mcp.tools.amplitude import get_amplitude_events
            result = get_amplitude_events("Purchase", "20260301", "20260315")
        assert "[ERROR]" in result
        assert "Rate Limit" in result

    def test_returns_markdown_table(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": {
                "xValues": ["2026-03-01", "2026-03-02"],
                "series": [[10, 20]],
                "seriesLabels": ["Purchase"],
            }
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("bi_agent_mcp.tools.amplitude.httpx.Client", return_value=mock_client):
            from bi_agent_mcp.tools.amplitude import get_amplitude_events
            result = get_amplitude_events("Purchase", "20260301", "20260315")
        assert "|" in result
        assert "Date" in result
        assert "2026-03-01" in result

    def test_invalid_data_format_returns_message(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"unexpected": "format"}

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("bi_agent_mcp.tools.amplitude.httpx.Client", return_value=mock_client):
            from bi_agent_mcp.tools.amplitude import get_amplitude_events
            result = get_amplitude_events("Purchase", "20260301", "20260315")
        assert "포맷" in result or "[ERROR]" in result

    def test_group_by_adds_param(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": {
                "xValues": ["2026-03-01"],
                "series": [[5]],
                "seriesLabels": ["ios", "android"],
            }
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        captured_params = {}

        def fake_get(url, params=None, auth=None):
            captured_params.update(params or {})
            return mock_resp

        mock_client.get.side_effect = fake_get

        with patch("bi_agent_mcp.tools.amplitude.httpx.Client", return_value=mock_client):
            from bi_agent_mcp.tools.amplitude import get_amplitude_events
            get_amplitude_events("Purchase", "20260301", "20260315", group_by="platform")
        assert "s" in captured_params


class TestGetAmplitudeEventsHttpErrors:
    """HTTP 400 / non-200 오류 응답 경로 (lines 116, 118)."""

    def setup_method(self):
        from bi_agent_mcp.tools import amplitude
        amplitude._amplitude_connections["default"] = {
            "api_key": "test_key",
            "secret_key": "test_secret",
        }

    def teardown_method(self):
        from bi_agent_mcp.tools import amplitude
        amplitude._amplitude_connections.clear()

    def _make_client_mock(self, status_code, text="error body"):
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.text = text
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp
        return mock_client

    def test_http_400_returns_bad_parameter_error(self):
        mock_client = self._make_client_mock(400, "bad param detail")
        with patch("bi_agent_mcp.tools.amplitude.httpx.Client", return_value=mock_client):
            from bi_agent_mcp.tools.amplitude import get_amplitude_events
            result = get_amplitude_events("Purchase", "20260301", "20260315")
        assert "[ERROR]" in result and "잘못된 파라미터" in result

    def test_http_503_returns_generic_error(self):
        mock_client = self._make_client_mock(503, "service unavailable")
        with patch("bi_agent_mcp.tools.amplitude.httpx.Client", return_value=mock_client):
            from bi_agent_mcp.tools.amplitude import get_amplitude_events
            result = get_amplitude_events("Purchase", "20260301", "20260315")
        assert "[ERROR]" in result and "503" in result
