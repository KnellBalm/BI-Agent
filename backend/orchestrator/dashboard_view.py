from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import box
from datetime import datetime
import os

class DashboardView:
    """
    BI-Agent 'Front Door' Dashboard.
    Renders a comprehensive system overview using Rich Layout.
    """
    def __init__(self, console=None):
        self.console = console or Console()
        self.layout = Layout()
        self._setup_layout()

    def _setup_layout(self):
        """Divides the screen into Header, Body (Status + Tips), and Footer (Activity)"""
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="middle"),
            Layout(name="footer", size=5)
        )
        self.layout["middle"].split_row(
            Layout(name="status", ratio=2),
            Layout(name="tips", ratio=1)
        )

    def render_header(self):
        grid = Table.grid(expand=True)
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="right", ratio=1)
        grid.add_row(
            Text(" ✻ BI-Agent Professional", style="bold cyan"),
            Text(f"v2.1.0 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ", style="dim")
        )
        return Panel(grid, border_style="bright_blue")

    def render_status(self, system_info: dict):
        table = Table(show_header=False, box=box.SIMPLE_HEAD, expand=True)
        table.add_column("Key", style="dim", width=15)
        table.add_column("Value")

        # LLM Status
        llm_type = system_info.get("llm_type", "Unknown")
        llm_style = "green" if "Gemini" in llm_type else "yellow"
        table.add_row("LLM Provider", f"[{llm_style}]{llm_type}[/{llm_style}]")

        # Connection Status
        db_conn = system_info.get("db_connection", "Disconnected")
        conn_style = "green" if db_conn == "Connected" else "red"
        table.add_row("DB Status", f"[{conn_style}]{db_conn}[/{conn_style}]")

        # Quota Info
        quota = system_info.get("quota", "N/A")
        table.add_row("GCP Quota", f"[cyan]{quota}[/cyan]")

        # Workspace Info
        table.add_row("Workspace", f"[white]{os.getcwd()}[/white]")

        return Panel(table, title="[bold yellow]System Status[/bold yellow]", border_style="yellow")

    def render_tips(self):
        tips = Text.from_markup(
            "[bold cyan]/analyze[/bold cyan] : 데이터 프로파일링 실행\n"
            "[bold cyan]/connect[/bold cyan] : DB 연결 관리\n"
            "[bold cyan]/list[/bold cyan]    : 인벤토리 확인\n"
            "[bold cyan]/clear[/bold cyan]   : 화면 정리\n"
            "[bold cyan]/exit[/bold cyan]    : 프로그램 종료"
        )
        return Panel(tips, title="[bold magenta]Quick Commands[/bold magenta]", border_style="magenta")

    def render_activity(self):
        activity = Text("✻ Welcome back! Ready to analyze your business data.\n", style="italic")
        activity.append("Tip: Try asking '매출 데이터 요약을 보여줘' to get started.", style="dim")
        return Panel(activity, title="[bold green]Recent Activity[/bold green]", border_style="green")

    def draw(self, system_info: dict):
        """Updates and prints the full dashboard layout"""
        self.layout["header"].update(self.render_header())
        self.layout["status"].update(self.render_status(system_info))
        self.layout["tips"].update(self.render_tips())
        self.layout["footer"].update(self.render_activity())
        
        self.console.clear()
        self.console.print(self.layout)

if __name__ == "__main__":
    # Self-test
    dv = DashboardView()
    sample_info = {
        "llm_type": "Gemini 1.5 Pro (Failover enabled)",
        "db_connection": "Connected (Postgres)",
        "quota": "85% Remaining (Free Tier)"
    }
    dv.draw(sample_info)
