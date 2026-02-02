from typing import Dict, List, Any, Optional
import pandas as pd
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.align import Align
from rich.style import Style

class TUIChartRenderer:
    """
    Rich 라이브러리를 사용하여 TUI 내에서 시각화 결과물을 렌더링합니다.
    KPI 카드, 유니코드 기반 막대 차트 등을 지원합니다.
    """
    
    @staticmethod
    def render_kpi_cards(metrics: List[Dict[str, Any]]) -> Columns:
        """
        주요 지표(KPI)를 상단 카드 형태로 렌더링합니다.
        metrics: [{"label": "Total Sales", "value": "1.2M", "delta": "+5%", "color": "green"}, ...]
        """
        cards = []
        for m in metrics:
            label = m.get("label", "Unknown")
            value = str(m.get("value", "0"))
            delta = m.get("delta", "")
            color = m.get("color", "cyan")
            
            content = Text()
            content.append(f"{value}\n", style=f"bold {color} size(20)")
            if delta:
                delta_style = "green" if "+" in delta else "red"
                content.append(f"{delta}", style=delta_style)
            
            card = Panel(
                Align.center(content, vertical="middle"),
                title=f"[bold]{label}[/bold]",
                border_style=color,
                width=24,
                height=7
            )
            cards.append(card)
        
        return Columns(cards, equal=True, expand=True)

    @staticmethod
    def render_bar_chart(df: pd.DataFrame, label_col: str, value_col: str, title: str = "Bar Chart") -> Panel:
        """
        Pandas DataFrame을 기반으로 유니코드 막대 차트를 생성합니다.
        """
        if df.empty:
            return Panel("No data to display", title=title)
            
        max_val = df[value_col].max()
        if max_val == 0: max_val = 1
        
        table = Table(show_header=False, box=None, padding=(0, 1))
        
        # 상위 10개만 표시 (TUI 한계)
        plot_df = df.head(10)
        
        for _, row in plot_df.iterrows():
            label = str(row[label_col])
            val = row[value_col]
            percent = (val / max_val)
            
            bar_len = 30
            filled = int(percent * bar_len)
            bar = "█" * filled + "░" * (bar_len - filled)
            
            table.add_row(
                Text(label, style="bold cyan", overflow="ellipsis"),
                Text(bar, style="green"),
                Text(f"{val:,}", style="yellow")
            )
            
        return Panel(table, title=f"[bold]{title}[/bold]", border_style="blue", padding=(1, 2))

    @staticmethod
    def render_summary_table(df: pd.DataFrame, title: str = "Data Summary") -> Table:
        """
        데이터 프레임의 요약본을 Rich Table로 렌더링합니다.
        """
        table = Table(title=title, header_style="bold magenta", box=None)
        
        for col in df.columns:
            table.add_column(col)
            
        # 최대 5행만 표시
        for _, row in df.head(5).iterrows():
            table.add_row(*[str(val) for val in row])
            
        return table

# Global utility
renderer = TUIChartRenderer()
