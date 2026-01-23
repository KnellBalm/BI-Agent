from rich.panel import Panel
from rich.syntax import Syntax
from rich.layout import Layout
from rich.table import Table
from rich.text import Text
import json
import os

class TUI_MetaPreview:
    """
    Tableau Meta JSON 결과를 TUI 상에서 미리보고 저장하는 패널.
    Premium TUI v2의 메인 영역에 통합됩니다.
    """
    def __init__(self, output_dir: str = "backend/data/outputs"):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def render_preview(self, meta_json: dict) -> Layout:
        """
        JSON 데이터를 시각화한 레이아웃을 반환합니다.
        보통 Summary Table + JSON Syntax View로 구성됩니다.
        """
        layout = Layout()
        layout.split_column(
            Layout(name="summary", size=6),
            Layout(name="content")
        )

        # 1. Summary 구성
        summary_table = Table(title="[bold cyan]Tableau Meta Summary[/bold cyan]", border_style="cyan")
        summary_table.add_column("Property", style="dim")
        summary_table.add_column("Count / Value", style="bold white")

        summary_table.add_row("Dimensions", str(len(meta_json.get("dimensions", []))))
        summary_table.add_row("Measures", str(len(meta_json.get("measures", []))))
        summary_table.add_row("Filters", str(len(meta_json.get("filters", []))))
        summary_table.add_row("Chart Type", meta_json.get("chart_type", "Unknown").upper())

        layout["summary"].update(Panel(summary_table, border_style="cyan"))

        # 2. Syntax Content 구성
        json_str = json.dumps(meta_json, indent=2, ensure_ascii=False)
        syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
        layout["content"].update(Panel(syntax, title="[bold yellow]Generated Meta JSON[/bold yellow]", border_style="yellow"))

        return layout

    def save_json(self, meta_json: dict, filename: str = "tableau_meta.json") -> str:
        """JSON 내용을 파일로 저장합니다."""
        target_path = os.path.join(self.output_dir, filename)
        try:
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(meta_json, f, indent=2, ensure_ascii=False)
            return f"[green]Successfully saved to {target_path}[/green]"
        except Exception as e:
            return f"[red]Save failed: {str(e)}[/red]"
