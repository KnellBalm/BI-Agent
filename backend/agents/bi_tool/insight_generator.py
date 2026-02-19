"""
Insight Generator - thin alias module re-exporting from summary_generator.

Provides backward-compatible imports for tests and callers that reference
the insight_generator module name.
"""

from backend.agents.bi_tool.summary_generator import (
    SummaryGenerator,
    AnalysisSummary,
)

__all__ = ["SummaryGenerator", "AnalysisSummary"]
