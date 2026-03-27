"""공통 pytest fixtures for unit tests."""
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock


def _make_patches(df: pd.DataFrame, module: str):
    """모듈별 _connections, _get_conn, _validate_select, pandas.read_sql을 패치한 리스트 반환."""
    conn_info = MagicMock()
    mock_conn = MagicMock()
    return [
        patch(f"{module}._connections", {"test_conn": conn_info}),
        patch(f"{module}._get_conn", return_value=mock_conn),
        patch(f"{module}._validate_select", return_value=None),
        patch("pandas.read_sql", return_value=df),
    ]


def _with_df(df: pd.DataFrame, module: str, fn, *args, **kwargs):
    """df와 module 경로를 받아 패치 컨텍스트에서 fn을 실행한다."""
    patches = _make_patches(df, module)
    for p in patches:
        p.start()
    try:
        return fn(*args, **kwargs)
    finally:
        for p in patches:
            p.stop()


@pytest.fixture
def with_df_analytics():
    """analytics 모듈용 _with_df 헬퍼를 반환하는 fixture."""
    def _helper(df, fn, *args, **kwargs):
        return _with_df(df, "bi_agent_mcp.tools.analytics", fn, *args, **kwargs)
    return _helper


@pytest.fixture
def with_df_business():
    """business 모듈용 _with_df 헬퍼를 반환하는 fixture."""
    def _helper(df, fn, *args, **kwargs):
        return _with_df(df, "bi_agent_mcp.tools.business", fn, *args, **kwargs)
    return _helper


@pytest.fixture
def with_df_product():
    """product 모듈용 _with_df 헬퍼를 반환하는 fixture."""
    def _helper(df, fn, *args, **kwargs):
        return _with_df(df, "bi_agent_mcp.tools.product", fn, *args, **kwargs)
    return _helper


@pytest.fixture
def with_df_marketing():
    """marketing 모듈용 _with_df 헬퍼를 반환하는 fixture."""
    def _helper(df, fn, *args, **kwargs):
        return _with_df(df, "bi_agent_mcp.tools.marketing", fn, *args, **kwargs)
    return _helper


@pytest.fixture
def with_df_ab_test():
    """ab_test 모듈용 _with_df 헬퍼를 반환하는 fixture."""
    def _helper(df, fn, *args, **kwargs):
        return _with_df(df, "bi_agent_mcp.tools.ab_test", fn, *args, **kwargs)
    return _helper
