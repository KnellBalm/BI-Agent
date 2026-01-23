"""
Analysis View Component
Renders DataProfiler results using Rich for TUI.
"""
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.columns import Columns
from rich.text import Text
from rich import box
from typing import Dict, Any

class AnalysisView:
    """
    Renders profiling results in a beautiful TUI format.
    """
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def render_full_report(self, profile_data: Dict[str, Any]):
        """Renders the entire profiling report"""
        
        # 1. Header
        self.console.print(Panel(
            Text("📊 데이터 프로파일링 리포트", style="bold cyan", justify="center"),
            border_style="cyan"
        ))
        
        # 2. Overview Table
        self.render_overview(profile_data["overview"])
        
        # 3. Column Details Table
        self.render_columns(profile_data["columns"])
        
        # 4. Sample Data
        self.render_sample(profile_data["sample"])

    def render_overview(self, overview: Dict[str, Any]):
        """Renders high-level dataset overview"""
        table = Table(title="[bold yellow]Dataset Overview[/bold yellow]", box=box.ROUNDED, expand=True)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="bold white")
        
        table.add_row("Rows / Columns", f"{overview['rows']} / {overview['columns']}")
        table.add_row("Missing Cells", f"{overview['missing_cells']} ({overview['missing_percentage']:.1f}%)")
        table.add_row("Duplicate Rows", str(overview['duplicate_rows']))
        table.add_row("Memory Usage", overview['memory_usage'])
        
        self.console.print(table)

    def render_columns(self, column_data: List[Dict[str, Any]]):
        """Renders detailed column analysis"""
        table = Table(title="[bold yellow]Column Analysis[/bold yellow]", box=box.ROUNDED, expand=True)
        table.add_column("Column Name", style="white")
        table.add_column("Type", style="bold green")
        table.add_column("Nulls", style="red")
        table.add_column("Unique", style="blue")
        table.add_column("Stats / Highlights", style="dim")
        
        for col in column_data:
            stats_text = ""
            if col["type"] == "numerical":
                stats_text = f"Mean: {col['mean']:.2f} | Min: {col['min']:.1f} | Max: {col['max']:.1f}"
            elif col["type"] == "categorical":
                # Show top 2 values
                top_items = list(col["top_values"].items())[:2]
                stats_text = "Top: " + ", ".join([f"{k}({v})" for k, v in top_items])
            elif col["type"] == "datetime":
                stats_text = f"Range: {col['min']} ~ {col['max']}"
            
            table.add_row(
                col["name"],
                col["type"].upper(),
                str(col["missing"]),
                str(col["unique"]),
                stats_text
            )
            
        self.console.print(table)

    def render_sample(self, sample: List[Dict[str, Any]]):
        """Renders a sample of the data"""
        if not sample:
            return
            
        table = Table(title="[bold yellow]Data Sample (Top 5)[/bold yellow]", box=box.SIMPLE_HEAD, expand=True)
        for key in sample[0].keys():
            table.add_column(key, style="dim", no_wrap=True)
            
        for row in sample:
            table.add_row(*[str(val) for val in row.values()])
            
        self.console.print(table)

if __name__ == "__main__":
    # Test rendering with dummy data
    from backend.agents.data_source.profiler import DataProfiler
    import pandas as pd
    
    df = pd.DataFrame({
        "Price": [10.5, 20.0, 15.2, 30.1, 12.0],
        "Category": ["A", "B", "A", "C", "B"],
        "Status": ["Active", "Active", "Retired", "Active", "Active"]
    })
    profiler = DataProfiler(df)
    view = AnalysisView()
    view.render_full_report(profiler.profile())
