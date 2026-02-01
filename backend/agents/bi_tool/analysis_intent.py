# /backend/agents/bi_tool/analysis_intent.py
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from backend.agents.bi_tool.base_intent import BaseIntent

@dataclass
class AnalysisIntent(BaseIntent):
    """복합 분석 의도의 구조화된 표현.

    AnalysisIntent는 실행 중에 여러 ChartIntent를 생성할 수 있는
    상위 수준의 분석 목표를 나타냅니다.

    관계: AnalysisIntent -> 생성 -> ChartIntent[]
    """
    purpose: str = "trend"  # "performance" | "trend" | "anomaly" | "comparison" | "forecast"
    target_metrics: List[str] = field(default_factory=list)
    time_range: Optional[Dict[str, str]] = None  # {"start": "2024-01-01", "end": "2024-12-31"}
    hypothesis: Optional[str] = None
    expected_output: str = "dashboard"  # "dashboard" | "report" | "insight"
    scope: Optional[str] = None  # "전체", "서울지역" 등
    constraints: List[str] = field(default_factory=list)  # 추가 제약 조건
    kpis: List[str] = field(default_factory=list)  # 주요 성과 지표

    @property
    def intent_type(self) -> str:
        return "analysis"

    def validate(self) -> bool:
        valid_purposes = ["performance", "trend", "anomaly", "comparison", "forecast", "correlation"]
        if self.purpose not in valid_purposes:
            return False
        if not self.datasource:
            return False
        if not self.target_metrics and not self.kpis:
            return False
        return True

    def produces_charts(self) -> List["ChartIntent"]:
        """AnalysisIntent에서 ChartIntent 생성.

        실제 차트 생성은 파이프라인 생성기에서 처리하지만,
        이 메서드는 예상되는 차트 타입의 미리보기를 제공합니다.
        """
        from backend.agents.bi_tool.nl_intent_parser import ChartIntent

        charts = []
        # 목적을 예상 차트 타입으로 매핑
        purpose_chart_map = {
            "trend": "line",
            "comparison": "bar",
            "performance": "bar",
            "anomaly": "scatter",
            "forecast": "line",
            "correlation": "scatter"
        }

        default_type = purpose_chart_map.get(self.purpose, "bar")

        for metric in self.target_metrics[:3]:  # 최대 3개 차트
            charts.append(ChartIntent(
                action="create",
                visual_type=default_type,
                datasource=self.datasource,
                dimensions=[],  # 파이프라인에서 채워짐
                measures=[metric],
                filters=self.filters.copy(),
                title=f"{metric} {self.purpose} 분석"
            ))

        return charts
