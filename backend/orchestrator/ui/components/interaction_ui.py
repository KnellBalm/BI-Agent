from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.table import Table
from rich.status import Status
from rich.tree import Tree
from rich import box
from datetime import datetime
import asyncio

class InteractionUI:
    """
    BI-Agent Premium TUI (v2.1)
    Claude/Gemini 스타일의 트리 구조 로그 및 박스 요약 지원.
    """
    def __init__(self):
        self.console = Console()
        self.layout = Layout()
        self.logs = []
        self.current_tree = None
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
            Text("BI-Agent Professional Workspace v2.1", style="bold cyan", justify="center"),
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
        elif level == "SYSTEM": color = "cyan"
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"[{color}][{timestamp}] {message}[/{color}]")
        if len(self.logs) > 20: # 최근 20개 유지
            self.logs.pop(0)

    def build_tree_log(self, root_label: str, steps: list):
        """Claude-style 트리 구조 로그 생성"""
        tree = Tree(f"[bold cyan]{root_label}[/bold cyan]")
        for step in steps:
            tree.add(f"[dim]{step}[/dim]")
        return tree

    def render_side_log(self):
        log_content = "\n".join(self.logs)
        return Panel(
            Text.from_markup(log_content),
            title="[bold yellow]Execution Log[/bold yellow]",
            border_style="yellow",
            padding=(0, 1)
        )

    def display_welcome(self):
        self.console.clear()
        self.console.print(self.render_header())
        self.console.print("\n[bold green]Welcome to the enhanced BI-Agent interface![/bold green]")
        self.console.print("[dim]Claude & Gemini styled UI for better clarity and precision.[/dim]\n")

    def create_data_table(self, data: list, title: str = "Data Result") -> Table:
        if not data:
            return Text("No data to display.")
        
        import pandas as pd
        df = pd.DataFrame(data)
        table = Table(title=f"[bold blue]{title}[/bold blue]", show_header=True, header_style="bold magenta", box=box.ROUNDED)
        for col in df.columns:
            table.add_column(str(col))
        for _, row in df.head(10).iterrows(): # 가독성을 위해 상위 10개만
            table.add_row(*[str(v) for v in row.values])
        return table

    def show_announcement(self, message: str):
        """Gemini-style 박스 공지 (실시간 진행 상황)"""
        self.console.print(Panel(
            Text(f"✻ {message}", style="bold yellow"),
            border_style="yellow",
            expand=False
        ))

    def show_agent_thought(self, agent_name: str, thought: str):
        """에이전트의 사고 과정(CoT) 상세 시각화"""
        thought_panel = Panel(
            Text(thought, style="italic dim"),
            title=f"[bold yellow]🤔 {agent_name} Thinking...[/bold yellow]",
            border_style="yellow"
        )
        self.console.print(thought_panel)

    def render_meta_preview(self, preview_layout: Layout):
        """메인 그리드에 메타 JSON 프리뷰를 렌더링합니다."""
        self.layout["main"].update(preview_layout)

    def show_final_response(self, response: str, title: str = "Final Insight"):
        """최종 결과를 깔끔한 박스로 요약 (Gemini style)"""
        response_panel = Panel(
            Text(response),
            title=f"[bold green]✨ {title}[/bold green]",
            border_style="green",
            padding=(1, 2)
        )
        self.console.print(response_panel)
