"""
Pytest configuration and shared fixtures for BI-Agent tests.

This file is automatically discovered by pytest and provides:
- Common fixtures used across test suites
- Test data generators
- Mock utilities
- Setup/teardown hooks
"""

import pytest
import pandas as pd
import tempfile
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import Mock, MagicMock


# ============================================================================
# Test Data Generators
# ============================================================================

@pytest.fixture
def sample_sales_data() -> pd.DataFrame:
    """Generate realistic sales dataset for testing."""
    return pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=100),
        'product_category': ['Electronics', 'Clothing', 'Food', 'Books'] * 25,
        'region': ['North', 'South', 'East', 'West'] * 25,
        'sales': [1000 + i * 10 for i in range(100)],
        'quantity': [10 + i % 50 for i in range(100)],
        'profit': [100 + i * 5 for i in range(100)]
    })


@pytest.fixture
def large_sales_data() -> pd.DataFrame:
    """Generate large dataset (100K rows) for performance testing."""
    import numpy as np

    n_rows = 100000
    return pd.DataFrame({
        'date': pd.date_range('2020-01-01', periods=n_rows, freq='H'),
        'product_id': np.random.randint(1, 1000, n_rows),
        'category': np.random.choice(['A', 'B', 'C', 'D', 'E'], n_rows),
        'region': np.random.choice(['North', 'South', 'East', 'West'], n_rows),
        'sales': np.random.uniform(100, 10000, n_rows),
        'quantity': np.random.randint(1, 100, n_rows)
    })


@pytest.fixture
def multi_table_dataset() -> Dict[str, pd.DataFrame]:
    """Generate multiple related tables for join testing."""
    customers = pd.DataFrame({
        'customer_id': [1, 2, 3, 4, 5],
        'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
        'region': ['North', 'South', 'East', 'West', 'North']
    })

    orders = pd.DataFrame({
        'order_id': [101, 102, 103, 104, 105],
        'customer_id': [1, 2, 1, 3, 4],
        'product_id': [1, 2, 3, 1, 2],
        'amount': [100, 200, 150, 300, 250],
        'order_date': pd.date_range('2024-01-01', periods=5)
    })

    products = pd.DataFrame({
        'product_id': [1, 2, 3],
        'product_name': ['Laptop', 'Phone', 'Tablet'],
        'category': ['Electronics', 'Electronics', 'Electronics'],
        'price': [1000, 800, 600]
    })

    return {
        'customers': customers,
        'orders': orders,
        'products': products
    }


@pytest.fixture
def time_series_data() -> pd.DataFrame:
    """Generate time series data with trend and seasonality."""
    import numpy as np

    dates = pd.date_range('2023-01-01', periods=365, freq='D')
    trend = np.linspace(1000, 2000, 365)
    seasonality = 500 * np.sin(np.arange(365) * 2 * np.pi / 365)
    noise = np.random.normal(0, 50, 365)

    return pd.DataFrame({
        'date': dates,
        'value': trend + seasonality + noise,
        'category': ['A', 'B'] * 182 + ['A']
    })


# ============================================================================
# LLM Mocks
# ============================================================================

class MockLLMProvider:
    """Mock LLM provider for testing without API calls."""

    def __init__(self, responses: Dict[str, str] = None):
        self.responses = responses or {}
        self.call_count = 0
        self.last_prompt = None

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate mock response based on prompt keywords."""
        self.call_count += 1
        self.last_prompt = prompt

        # Pattern matching for different types of prompts
        if 'insight' in prompt.lower() or 'summary' in prompt.lower():
            return self._generate_insight_response()
        elif 'chart' in prompt.lower() or 'visualization' in prompt.lower():
            return self._generate_chart_recommendation()
        elif 'trend' in prompt.lower():
            return "데이터에서 상승 추세가 관찰됩니다. 전월 대비 15% 증가했습니다."
        else:
            return self.responses.get('default', 'Mock LLM response')

    def _generate_insight_response(self) -> str:
        """Generate mock insight summary."""
        return """
        ## 주요 인사이트

        1. **매출 성장**: 전월 대비 15% 증가
        2. **지역별 분포**: 북부 지역이 전체 매출의 40% 차지
        3. **카테고리 트렌드**: Electronics 카테고리가 가장 높은 성장률 기록

        ## 권장 사항

        - 북부 지역 마케팅 강화 권장
        - Electronics 재고 확보 필요
        """

    def _generate_chart_recommendation(self) -> str:
        """Generate mock chart recommendation."""
        return '{"chart_type": "line", "title": "Sales Trend", "x_axis": "date", "y_axis": "sales"}'


@pytest.fixture
def mock_llm_provider():
    """Provide mock LLM for testing."""
    return MockLLMProvider()


@pytest.fixture
def mock_llm_with_responses():
    """Provide mock LLM with custom responses."""
    responses = {
        'chart_recommendation': '{"chart_type": "bar", "x": "category", "y": "sales"}',
        'insight_summary': '주요 트렌드: 매출 증가',
        'default': 'Mock response'
    }
    return MockLLMProvider(responses)


# ============================================================================
# File System Fixtures
# ============================================================================

@pytest.fixture
def temp_output_dir(tmp_path) -> Path:
    """Create temporary directory for test outputs."""
    output_dir = tmp_path / "test_outputs"
    output_dir.mkdir(exist_ok=True)
    return output_dir


@pytest.fixture
def temp_export_dir(tmp_path) -> Path:
    """Create temporary directory for export testing."""
    export_dir = tmp_path / "exports"
    export_dir.mkdir(exist_ok=True)
    return export_dir


@pytest.fixture
def sample_json_config() -> Dict[str, Any]:
    """Generate sample dashboard configuration."""
    return {
        'title': 'Test Dashboard',
        'components': [
            {
                'id': 'chart1',
                'type': 'line',
                'title': 'Sales Trend',
                'x': 0,
                'y': 0,
                'width': 600,
                'height': 400,
                'data': {'Jan': 1000, 'Feb': 1200, 'Mar': 1500}
            }
        ],
        'theme': {
            'colors': ['#1f77b4', '#ff7f0e', '#2ca02c'],
            'font': 'Arial'
        },
        'filters': [],
        'interactions': []
    }


# ============================================================================
# Mock Components
# ============================================================================

@pytest.fixture
def mock_chart_config() -> Dict[str, Any]:
    """Generate mock chart configuration."""
    return {
        'chart_type': 'bar',
        'title': 'Sales by Category',
        'x_axis': 'category',
        'y_axis': 'sales',
        'config': {
            'color': '#1f77b4',
            'orientation': 'vertical'
        }
    }


@pytest.fixture
def mock_layout_components() -> List[Dict[str, Any]]:
    """Generate mock layout components."""
    return [
        {'id': 'chart1', 'type': 'bar', 'priority': 1, 'min_width': 400, 'min_height': 300},
        {'id': 'chart2', 'type': 'line', 'priority': 2, 'min_width': 400, 'min_height': 300},
        {'id': 'kpi1', 'type': 'kpi_card', 'priority': 3, 'min_width': 200, 'min_height': 150},
    ]


@pytest.fixture
def mock_drilldown_hierarchy() -> Dict[str, Any]:
    """Generate mock drilldown hierarchy."""
    return {
        'levels': [
            {'name': 'category', 'column': 'product_category'},
            {'name': 'region', 'column': 'region'},
            {'name': 'product', 'column': 'product_id'}
        ],
        'filters': []
    }


# ============================================================================
# Performance Monitoring
# ============================================================================

@pytest.fixture
def performance_tracker():
    """Track performance metrics during tests."""
    import time
    import psutil
    import os

    class PerformanceTracker:
        def __init__(self):
            self.start_time = None
            self.start_memory = None
            self.metrics = {}

        def start(self):
            """Start tracking."""
            self.start_time = time.time()
            process = psutil.Process(os.getpid())
            self.start_memory = process.memory_info().rss / 1024 / 1024  # MB

        def stop(self, label: str = "operation"):
            """Stop tracking and record metrics."""
            if self.start_time is None:
                raise RuntimeError("Must call start() before stop()")

            elapsed = time.time() - self.start_time
            process = psutil.Process(os.getpid())
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_delta = current_memory - self.start_memory

            self.metrics[label] = {
                'elapsed_seconds': elapsed,
                'memory_mb': memory_delta
            }

            return self.metrics[label]

    return PerformanceTracker()


# ============================================================================
# Pytest Hooks
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "llm: Tests requiring LLM")
    config.addinivalue_line("markers", "tui: TUI interaction tests")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Auto-mark based on file path
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
            item.add_marker(pytest.mark.slow)
        elif "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Mark LLM-dependent tests
        if "llm" in item.name.lower() or "insight" in item.name.lower():
            item.add_marker(pytest.mark.llm)
