from typing import Dict, Any
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Label
from textual.containers import Vertical, Horizontal, Grid
from rich.panel import Panel
from rich.columns import Columns
from backend.orchestrator.components.tui_charts import renderer
import pandas as pd

class VisualAnalysisScreen(Screen):
    """
    분석 결과(KPI, Charts)를 시각화하여 보여주는 전용 스크린입니다.
    """
    CSS = """
    VisualAnalysisScreen {
        background: $boost;
    }
    #analysis-container {
        padding: 1 2;
        height: 100%;
    }
    .chart-panel {
        margin: 1 1;
        height: auto;
    }
    .kpi-row {
        height: 10;
        margin-bottom: 1;
    }
    """

    def __init__(self, data: Dict[str, Any], title: str = "Analysis Insights"):
        super().__init__()
        self.data = data
        self.analysis_title = title

    def compose(self):
        yield Header()
        with Vertical(id="analysis-container"):
            yield Label(f"[bold cyan]📊 {self.analysis_title}[/bold cyan]", id="screen-title")
            
            # KPI 섹션
            metrics = self.data.get("metrics", [])
            if metrics:
                yield Static(renderer.render_kpi_cards(metrics), classes="kpi-row")
            
            # 차트 섹션 (Grid 또는 Vertical)
            with Horizontal():
                charts = self.data.get("charts", [])
                for chart in charts:
                    # 데이터 프레임 변환
                    df = pd.DataFrame(chart["data"])
                    chart_panel = renderer.render_bar_chart(
                        df, 
                        label_col=chart["label_col"], 
                        value_col=chart["value_col"], 
                        title=chart["title"]
                    )
                    yield Static(chart_panel, classes="chart-panel")
        
        yield Footer()

    def on_mount(self) -> None:
        self.bind("escape", "app.pop_screen", description="Close")
        self.bind("q", "app.pop_screen", description="Quit View")
