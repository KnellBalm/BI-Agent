"""bi_agent_mcp.tools.ga4 단위 테스트."""
import pytest
from unittest.mock import MagicMock, patch


class TestConnectGa4:
    def teardown_method(self):
        """각 테스트 후 _ga4_connections 초기화."""
        from bi_agent_mcp.tools import ga4
        ga4._ga4_connections.clear()

    def test_missing_client_id_returns_error(self):
        with patch("bi_agent_mcp.tools.ga4.config") as mock_cfg:
            mock_cfg.GOOGLE_CLIENT_ID = None
            mock_cfg.GOOGLE_CLIENT_SECRET = "secret"
            from bi_agent_mcp.tools.ga4 import connect_ga4
            result = connect_ga4("123456789")
        assert "[ERROR]" in result

    def test_missing_client_secret_returns_error(self):
        with patch("bi_agent_mcp.tools.ga4.config") as mock_cfg:
            mock_cfg.GOOGLE_CLIENT_ID = "client_id"
            mock_cfg.GOOGLE_CLIENT_SECRET = None
            from bi_agent_mcp.tools.ga4 import connect_ga4
            result = connect_ga4("123456789")
        assert "[ERROR]" in result

    def test_import_error_returns_error(self):
        mock_creds = MagicMock()
        mock_creds.valid = True
        with patch("bi_agent_mcp.tools.ga4.config") as mock_cfg, \
             patch("bi_agent_mcp.tools.ga4.get_credentials", return_value=mock_creds), \
             patch.dict("sys.modules", {"google.analytics.data.v1beta": None}):
            mock_cfg.GOOGLE_CLIENT_ID = "client_id"
            mock_cfg.GOOGLE_CLIENT_SECRET = "secret"
            from bi_agent_mcp.tools.ga4 import connect_ga4
            result = connect_ga4("123456789")
        assert "[ERROR]" in result

    def test_oauth_exception_returns_error(self):
        with patch("bi_agent_mcp.tools.ga4.config") as mock_cfg, \
             patch("bi_agent_mcp.tools.ga4.get_credentials", side_effect=Exception("oauth failed")):
            mock_cfg.GOOGLE_CLIENT_ID = "client_id"
            mock_cfg.GOOGLE_CLIENT_SECRET = "secret"
            from bi_agent_mcp.tools.ga4 import connect_ga4
            result = connect_ga4("123456789")
        assert "[ERROR]" in result
        assert "GA4" in result

    def test_success_registers_connection(self):
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_client = MagicMock()
        mock_client_cls = MagicMock(return_value=mock_client)

        mock_ga4_module = MagicMock()
        mock_ga4_module.BetaAnalyticsDataClient = mock_client_cls

        with patch("bi_agent_mcp.tools.ga4.config") as mock_cfg, \
             patch("bi_agent_mcp.tools.ga4.get_credentials", return_value=mock_creds), \
             patch.dict("sys.modules", {
                 "google.analytics.data.v1beta": mock_ga4_module,
             }):
            mock_cfg.GOOGLE_CLIENT_ID = "client_id"
            mock_cfg.GOOGLE_CLIENT_SECRET = "secret"
            from bi_agent_mcp.tools import ga4 as ga4_module
            ga4_module._ga4_connections.clear()
            result = ga4_module.connect_ga4("123456789")
        assert "[SUCCESS]" in result
        assert "123456789" in result


class TestGetGa4Report:
    def setup_method(self):
        """테스트 전 mock 연결 등록."""
        from bi_agent_mcp.tools import ga4
        self.mock_client = MagicMock()
        ga4._ga4_connections["prop_test"] = {
            "client": self.mock_client,
            "connected": True,
        }

    def teardown_method(self):
        from bi_agent_mcp.tools import ga4
        ga4._ga4_connections.clear()

    def test_not_connected_returns_error(self):
        from bi_agent_mcp.tools.ga4 import get_ga4_report
        result = get_ga4_report("prop_unknown", ["sessions"], ["date"])
        assert "[ERROR]" in result
        assert "connect_ga4" in result

    def test_import_error_returns_error(self):
        with patch.dict("sys.modules", {
            "google.analytics.data.v1beta.types": None,
            "google.api_core.exceptions": None,
        }):
            from bi_agent_mcp.tools.ga4 import get_ga4_report
            result = get_ga4_report("prop_test", ["sessions"], ["date"])
        assert "[ERROR]" in result

    def test_no_rows_returns_info_message(self):
        mock_date_range = MagicMock()
        mock_dimension = MagicMock()
        mock_metric = MagicMock()
        mock_request = MagicMock()
        mock_response = MagicMock()
        mock_response.rows = []

        self.mock_client.run_report.return_value = mock_response

        mock_types = MagicMock()
        mock_types.DateRange = MagicMock(return_value=mock_date_range)
        mock_types.Dimension = MagicMock(return_value=mock_dimension)
        mock_types.Metric = MagicMock(return_value=mock_metric)
        mock_types.RunReportRequest = MagicMock(return_value=mock_request)

        mock_exceptions = MagicMock()
        mock_exceptions.InvalidArgument = Exception
        mock_exceptions.PermissionDenied = Exception
        mock_exceptions.ResourceExhausted = Exception

        with patch("bi_agent_mcp.tools.ga4.config") as mock_cfg, \
             patch.dict("sys.modules", {
                 "google.analytics.data.v1beta.types": mock_types,
                 "google.api_core.exceptions": mock_exceptions,
             }):
            mock_cfg.QUERY_LIMIT = 1000
            from bi_agent_mcp.tools.ga4 import get_ga4_report
            result = get_ga4_report("prop_test", ["sessions"], ["date"])
        assert "데이터가 없습니다" in result

    def test_returns_markdown_table(self):
        mock_row = MagicMock()
        dim_val = MagicMock()
        dim_val.value = "2026-03-01"
        met_val = MagicMock()
        met_val.value = "100"
        mock_row.dimension_values = [dim_val]
        mock_row.metric_values = [met_val]

        mock_response = MagicMock()
        mock_response.rows = [mock_row]
        self.mock_client.run_report.return_value = mock_response

        mock_types = MagicMock()
        mock_types.DateRange = MagicMock()
        mock_types.Dimension = MagicMock()
        mock_types.Metric = MagicMock()
        mock_types.RunReportRequest = MagicMock()

        mock_exceptions = MagicMock()
        mock_exceptions.InvalidArgument = Exception
        mock_exceptions.PermissionDenied = Exception
        mock_exceptions.ResourceExhausted = Exception

        with patch("bi_agent_mcp.tools.ga4.config") as mock_cfg, \
             patch.dict("sys.modules", {
                 "google.analytics.data.v1beta.types": mock_types,
                 "google.api_core.exceptions": mock_exceptions,
             }):
            mock_cfg.QUERY_LIMIT = 1000
            from bi_agent_mcp.tools.ga4 import get_ga4_report
            result = get_ga4_report("prop_test", ["sessions"], ["date"])
        assert "|" in result

    def test_generic_exception_returns_error(self):
        self.mock_client.run_report.side_effect = RuntimeError("unexpected")

        mock_types = MagicMock()
        mock_types.DateRange = MagicMock()
        mock_types.Dimension = MagicMock()
        mock_types.Metric = MagicMock()
        mock_types.RunReportRequest = MagicMock()

        mock_exceptions = MagicMock()
        mock_exceptions.InvalidArgument = type("InvalidArgument", (Exception,), {})
        mock_exceptions.PermissionDenied = type("PermissionDenied", (Exception,), {})
        mock_exceptions.ResourceExhausted = type("ResourceExhausted", (Exception,), {})

        with patch("bi_agent_mcp.tools.ga4.config") as mock_cfg, \
             patch.dict("sys.modules", {
                 "google.analytics.data.v1beta.types": mock_types,
                 "google.api_core.exceptions": mock_exceptions,
             }):
            mock_cfg.QUERY_LIMIT = 1000
            from bi_agent_mcp.tools.ga4 import get_ga4_report
            result = get_ga4_report("prop_test", ["sessions"], ["date"])
        assert "[ERROR]" in result
