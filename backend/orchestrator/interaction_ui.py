from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.table import Table
from rich.status import Status
from datetime import datetime
import asyncio

class InteractionUI:
    """
    BI-Agent Premium TUI (v2)
    Rich Layout을 사용하여 다중 창 및 실시간 상태를 시각화합니다.
    """
    def __init__(self):
        self.console = Console()
        self.layout = Layout()
        self.logs = []
        self._setup_layout()
        
    def _setup_layout(self):
        """기본 레이아웃 구성: Header, Main, Footer + SideLog"""
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        self.layout["body"].split_row(
            Layout(name="main", ratio=3),
            Layout(name="side", ratio=1)
        )
        
    def render_header(self):
        return Panel(
            Text("BI-Agent Professional Workspace v2", style="bold cyan", justify="center"),
            border_style="bright_blue"
        )
        
    def render_footer(self, status_text="Ready"):
        return Panel(
            Text(f"Status: {status_text} | Time: {datetime.now().strftime('%H:%M:%S')}", style="dim"),
            border_style="dim"
        )

    def add_log(self, message: str, level: str = "INFO"):
        color = "white"
        if level == "AGENT": color = "yellow"
        elif level == "SUCCESS": color = "green"
        elif level == "ERROR": color = "red"
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"[{color}][{timestamp}] {message}[/{color}]")
        if len(self.logs) > 15: # 최근 15개만 유지
            self.logs.pop(0)

    def render_side_log(self):
        log_content = "\n".join(self.logs)
        return Panel(
            Text.from_markup(log_content),
            title="[bold yellow]Agent Activity Log[/bold yellow]",
            border_style="yellow"
        )

    def display_welcome(self):
        self.console.clear()
        self.console.print(self.render_header())
        self.console.print("\n[bold green]Welcome to the enhanced BI-Agent interface![/bold green]")
        self.console.print("[dim]Ask complex questions, modify metadata, and get step-by-step guidance.[/dim]\n")

    def create_data_table(self, data: list, title: str = "Data Result") -> Table:
        if not data:
            return Text("No data to display.")
        
        import pandas as pd
        df = pd.DataFrame(data)
        table = Table(title=f"[bold blue]{title}[/bold blue]", show_header=True, header_style="bold magenta")
        for col in df.columns:
            table.add_column(str(col))
        for _, row in df.head(10).iterrows():
            table.add_row(*[str(v) for v in row.values])
        return table

    def show_agent_thought(self, agent_name: str, thought: str):
        """에이전트의 사고 과정(CoT)을 시각화합니다."""
        thought_panel = Panel(
            Text(thought, style="italic dim"),
            title=f"[bold yellow]{agent_name} Thinking...[/bold yellow]",
            border_style="yellow"
        )
        self.console.print(thought_panel)

    def render_meta_preview(self, preview_layout: Layout):
        """메인 그리드에 메타 JSON 프리뷰를 렌더링합니다."""
        self.layout["main"].update(preview_layout)

    def show_final_response(self, response: str, title: str = "Response"):
        response_panel = Panel(
            Text(response),
            title=f"[bold cyan]{title}[/bold cyan]",
            border_style="cyan"
        )
        self.console.print(response_panel)
