"""bi_tool_guide 단위 테스트."""
import pytest
from bi_agent_mcp.tools.bi_tool_guide import bi_tool_guide


class TestErrors:
    def test_empty_intent_returns_error(self):
        result = bi_tool_guide(intent="")
        assert "[ERROR]" in result
        assert "intent" in result

    def test_unknown_tool_returns_error(self):
        result = bi_tool_guide(intent="차트 만들기", tool="powerpoint")
        assert "[ERROR]" in result
        assert "tableau" in result.lower() or "지원하지 않는" in result

    def test_whitespace_intent_returns_error(self):
        result = bi_tool_guide(intent="   ")
        assert "[ERROR]" in result
