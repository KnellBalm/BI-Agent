import os
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal, Container
from textual.widgets import Label, Input, ListView, ListItem, Static, Header, Footer, DataTable, RichLog, OptionList
from textual.screen import ModalScreen
from textual.binding import Binding

from backend.orchestrator.auth_manager import auth_manager
from backend.orchestrator.quota_manager import quota_manager
from backend.utils.logger_setup import setup_logger
from backend.utils.path_config import path_manager

# Initialize localized logger
logger = setup_logger("tui", "tui.log")

class AuthScreen(ModalScreen):
    """
    환영 메시지와 함께 API 키 설정을 유도하는 모달 스크린
    """
    def compose(self) -> ComposeResult:
        with Vertical(id="auth-modal"):
            yield Label("[bold white]B I  -  A G E N T  Multi-LLM Auth[/bold white]\n", id="auth-title")
            yield Label("에이전트 구동을 위해 다음 중 하나 이상의 계정 연동이 필요합니다.\n")
            yield Label("• [cyan]Gemini (Pro 구독 권장)[/cyan]: AI Studio Key")
            yield Label("• [cyan]Claude 3.5[/cyan]: Anthropic API Key")
            yield Label("• [cyan]ChatGPT[/cyan]: OpenAI API Key\n")
            
            with Horizontal(id="auth-buttons"):
                yield Static("[bold green] 🔑 [1] Gemini/Google [/bold green]", id="btn-gemini")
                yield Static("   ")
                yield Static("[bold blue] 🤖 [2] Claude [/bold blue]", id="btn-claude")
                yield Static("   ")
                yield Static("[bold magenta] 💡 [3] ChatGPT [/bold magenta]", id="btn-openai")
            
            yield Input(id="key-input", placeholder="API Key 입력...", password=True)
            yield Label("\n[dim]※ 입력한 키는 credentials.json 에 안전하게 보관됩니다.[/dim]")
            yield Label("[dim]※ 환경 변수(GEMINI_API_KEY)가 설정되어 있다면 자동으로 적용됩니다.[/dim]")
    
    CSS = """
    #auth-modal {
        width: 60;
        height: 25;
        background: #1e293b;
        border: thick #38bdf8;
        padding: 2;
        align: center middle;
    }
    #auth-title {
        font-size: 150%;
        text-align: center;
    }
    #auth-buttons {
        height: 3;
        align: center middle;
        margin: 1;
    }
    #key-input {
        display: none;
        border: solid #38bdf8;
    }
    #key-input.visible {
        display: block;
    }
    """

    async def on_click(self, event) -> None:
        try:
            self.current_provider = None
            if event.node.id == "btn-gemini":
                self.current_provider = "gemini"
                await auth_manager.login_with_google_oauth()
            elif event.node.id == "btn-claude":
                self.current_provider = "claude"
            elif event.node.id == "btn-openai":
                self.current_provider = "openai"
                
            if self.current_provider:
                self.query_one("#key-input", Input).add_class("visible")
                self.query_one("#key-input", Input).focus()
        except Exception as e:
            logger.error(f"Error in AuthScreen click: {e}")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        key = event.value.strip()
        if key and self.current_provider:
            auth_manager.set_provider_key(self.current_provider, key)
            self.dismiss(True)

class ProjectScreen(ModalScreen):
    """
    Project selection and creation screen.
    """
    def __init__(self, current_project: str):
        super().__init__()
        self.current_project = current_project

    def compose(self) -> ComposeResult:
        with Vertical(id="project-modal"):
            yield Label("[bold white]Project Manager[/bold white]", id="project-title")
            yield Label(f"Current: [cyan]{self.current_project}[/cyan]\n")
            yield Label("Switch to or create a new project:")
            yield ListView(id="project-list")
            yield Input(id="new-project-input", placeholder="Enter new project name to create...")
            yield Label("\n[dim]Esc:Cancel  Enter:Select/Create[/dim]")

    CSS = """
    #project-modal {
        width: 50;
        height: 20;
        background: #1e293b;
        border: thick #10b981;
        padding: 2;
        align: center middle;
    }
    #project-title {
        font-size: 150%;
        text-align: center;
        margin-bottom: 1;
    }
    #project-list {
        height: 8;
        background: #0f172a;
        margin: 1 0;
    }
    """

    def on_mount(self) -> None:
        project_list = self.query_one("#project-list", ListView)
        project_list.clear()
        
        if not path_manager.projects_dir.exists():
            path_manager.projects_dir.mkdir(parents=True, exist_ok=True)
            
        projects = [d.name for d in path_manager.projects_dir.iterdir() if d.is_dir()]
        if not projects:
            projects = ["default"]
            
        self.proj_map = {}
        for idx, p in enumerate(projects):
            label = f"📁 {p}"
            if p == self.current_project:
                label += " [bold cyan](current)[/bold cyan]"
            project_list.append(ListItem(Label(label)))
            self.proj_map[idx] = p

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = self.query_one("#project-list", ListView).index
        if idx in self.proj_map:
            self.dismiss(self.proj_map[idx])

    def on_input_submitted(self, event: Input.Submitted) -> None:
        new_name = event.value.strip()
        if new_name:
            self.dismiss(new_name)

class BI_AgentConsole(App):
    """
    분석가를 위한 지능형 관문 (Entrance Hall).
    대화형 인터페이스와 슬래시 명령어(/)를 통해 필요한 에이전트를 호출합니다.
    """
    CSS = """
    Screen {
        background: #0f172a;
    }
    #main-container {
        width: 100%;
        height: 100%;
    }
    #logo-banner {
        width: 100%;
        height: 6;
        content-align: center middle;
        text-style: bold;
        color: #38bdf8;
        background: #1e293b;
        border-bottom: tall #334155;
    }
    #content-area {
        height: 1fr;
    }
    #chat-area {
        width: 70%;
        height: 100%;
        border-right: vertical #334155;
    }
    #status-sidebar {
        width: 30%;
        height: 100%;
        background: #1e293b;
        padding: 1 2;
    }
    #chat-log {
        height: 1fr;
        border: none;
        background: #0f172a;
    }
    #input-bar {
        height: 3;
        margin: 0 1;
        background: #1e293b;
        border: solid #38bdf8;
    }
    Input {
        background: transparent;
        border: none;
        width: 100%;
    }
    .status-title {
        text-style: bold;
        color: #38bdf8;
        margin-top: 1;
    }
    .skill-item {
        color: #94a3b8;
        margin-left: 2;
    }
    .skill-active {
        color: #10b981;
    }
    #command-palette {
        width: 40;
        height: 12;
        background: #1e293b;
        border: thick #38bdf8;
        display: none;
        layer: top;
        position: absolute;
        bottom: 4;
        left: 2;
    }
    #command-palette.visible {
        display: block;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("escape", "hide_palette", "Close Palette", show=False),
        Binding("ctrl+l", "clear_chat", "Clear", show=True),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_project = "default"
        self._init_orchestrator(self.current_project)
        self.palette_visible = False

    def _init_orchestrator(self, project_id: str):
        try:
            from backend.orchestrator.collaborative_orchestrator import CollaborativeOrchestrator
            self.orchestrator = CollaborativeOrchestrator(project_id)
            self.conn_mgr = self.orchestrator.conn_mgr
            # Path Manager is already imported at top level
            self.registry_path = path_manager.get_project_path(project_id) / "registry.json"
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="main-container"):
            yield Static(
                "\n[bold cyan] ⚡ BI - AGENT [/bold cyan]\n" +
                "[dim] Advanced Analyst Co-pilot Interface [/dim]",
                id="logo-banner"
            )
            with Horizontal(id="content-area"):
                with Vertical(id="chat-area"):
                    yield RichLog(id="chat-log", markup=True, wrap=True)
                    yield OptionList(
                        "📈 /analyze - 스마트 데이터 분석",
                        "🔗 /connect - 데이터 소스 연결 관리",
                        "📂 /project - 프로젝트 전환 및 생성",
                        "🔑 /login   - LLM 계정 설정 및 인증",
                        "📄 /report  - 최신 리포트 보기",
                        "❓ /help    - 에이전트 사용 가이드",
                        id="command-palette"
                    )
                    with Horizontal(id="input-bar"):
                        yield Input(id="user-input", placeholder="무엇을 도와드릴까요? (/를 입력하여 명령어 탐색)")
                
                with Vertical(id="status-sidebar"):
                    yield Label("S Y S T E M  S T A T U S", classes="status-title")
                    yield Label(f"• Project: [cyan]{self.current_project}[/cyan]", id="lbl-project")
                    yield Label("• Auth: [yellow]Checking...[/yellow]", id="lbl-auth")
                    
                    yield Label("\nS K I L L S  (Active)", classes="status-title")
                    yield Label("• [green]✔[/green] Data Source Agent", classes="skill-item")
                    yield Label("• [green]✔[/green] BI Tool Agent", classes="skill-item")
                    yield Label("• [green]✔[/green] Insight Agent", classes="skill-item")
                    
                    yield Label("\nQ U O T A  S T A T U S", classes="status-title")
                    yield Static("[dim]할당량 정보를 불러오는 중...[/dim]", id="lbl-quota")
                    
                    yield Label("\nC O N N E C T I O N S", classes="status-title")
                    yield Static("[dim]연결된 소스가 없습니다.[/dim]", id="lbl-connections")
                    
                    yield Label("\n[dim]Press [b]Ctrl+L[/b] to clear chat[/dim]")
        yield Footer()

    async def on_mount(self) -> None:
        self.title = "BI-Agent Analyst Co-pilot"
        
        chat_log = self.query_one("#chat-log", RichLog)

        # Show initial greeting
        chat_log.write("\n" + " " * 4 + "[bold cyan]Welcome to BI-Agent Entrance Hall[/bold cyan]")
        chat_log.write(" " * 4 + "[dim]분석가의 생산성을 3배 이상 높이는 지능형 조수입니다.[/dim]\n")
        
        # Initial checks
        self.call_after_refresh(self._update_sidebar)
        logger.info("TUI mounted successfully.")

    async def _update_sidebar(self) -> None:
        """Update the sidebar status information."""
        # Auth status
        auth_lbl = self.query_one("#lbl-auth", Label)
        if auth_manager.is_authenticated("gemini") or auth_manager.is_authenticated("claude") or auth_manager.is_authenticated("openai"):
            auth_lbl.update("• Auth: [green]✔ Connected[/green]")
        else:
            auth_lbl.update("• Auth: [red]✘ Login Required[/red]")
            self.push_screen(AuthScreen())

        # Quota status
        quota_lbl = self.query_one("#lbl-quota", Static)
        quota_text = ""
        for p in ["gemini", "claude", "openai", "ollama"]:
            status = quota_manager.get_provider_status(p)
            color = "green" if not status.get("exhausted") else "red"
            emoji = "💎" if p == "gemini" else "🤖" if p == "claude" else "💡" if p == "openai" else "🏠"
            
            usage_str = f"{status.get('daily_count', 0)}/{status.get('limit', '∞')}"
            quota_text += f"• {emoji} {p.capitalize()}: [{color}]{usage_str}[/{color}]\n"
        
        quota_lbl.update(quota_text.strip())

        # Connection status
        conn_lbl = self.query_one("#lbl-connections", Static)
        if os.path.exists(self.registry_path):
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            if registry:
                conn_list = "\n".join([f"• {name} ([dim]{info['type']}[/dim])" for name, info in registry.items()])
                conn_lbl.update(conn_list)
            else:
                conn_lbl.update("[dim]연결된 소스가 없습니다.[/dim]")

        # Schedule next update
        self.set_timer(10, self._update_sidebar)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Detect slash to show command palette."""
        palette = self.query_one("#command-palette", OptionList)
        if event.value == "/":
            palette.add_class("visible")
            self.palette_visible = True
            logger.debug("Slash detected, showing palette.")
        elif not event.value.startswith("/"):
            palette.remove_class("visible")
            self.palette_visible = False

    def on_key(self, event) -> None:
        """Handle global keys for palette navigation."""
        if self.palette_visible and event.key == "down":
            inp = self.query_one("#user-input", Input)
            if inp.has_focus:
                palette = self.query_one("#command-palette", OptionList)
                palette.focus()
                event.prevent_default()

    def action_hide_palette(self) -> None:
        """Force hide the palette."""
        palette = self.query_one("#command-palette", OptionList)
        palette.remove_class("visible")
        self.palette_visible = False
        self.query_one("#user-input", Input).focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle command selection from palette."""
        prompt = str(event.option.prompt)
        # Extract command part (e.g., "/login")
        import re
        match = re.search(r"(/[a-z]+)", prompt)
        if match:
            cmd = match.group(1)
            inp = self.query_one("#user-input", Input)
            inp.value = cmd + " "
            self.action_hide_palette()
            inp.focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle final input execution."""
        user_text = event.value.strip()
        if not user_text:
            return

        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.write(f"\n[bold green]You:[/bold green] {user_text}")
        self.query_one("#user-input", Input).value = ""
        
        if user_text.startswith("/"):
            await self.handle_command(user_text)
        else:
            await self.process_query(user_text)

    async def handle_command(self, cmd_text: str):
        """Routing for slash commands."""
        parts = cmd_text.split()
        cmd = parts[0]
        chat_log = self.query_one("#chat-log", RichLog)
        
        if cmd == "/connect":
            chat_log.write("[dim]데이터 소스 관리 화면으로 전환합니다... (곧 지원 예정)[/dim]")
        elif cmd == "/project":
            self.action_switch_project()
        elif cmd == "/login":
            chat_log.write("[dim]인증 및 계정 설정 화면을 엽니다...[/dim]")
            self.push_screen(AuthScreen())
        elif cmd == "/analyze":
            chat_log.write("[dim]상세 분석 모드로 전환합니다... (곧 지원 예정)[/dim]")
        elif cmd == "/help":
            chat_log.write("\n[bold cyan]사용 가능한 명령어:[/bold cyan]")
            chat_log.write("- [b]/analyze[/b]: 데이터 심층 분석 모드 실행")
            chat_log.write("- [b]/connect[/b]: 데이터 소스 관리 및 연결 설정")
            chat_log.write("- [b]/project[/b]: 현재 분석 프로젝트 전환")
            chat_log.write("- [b]/login[/b]: LLM 계정 및 API Key 설정")
            chat_log.write("- [b]/report[/b]: 생성된 리포트 센터 방문")
            chat_log.write("- [b]/help[/b]: 이 도움말 표시\n")
        else:
            chat_log.write(f"[red]알 수 없는 명령어입니다: {cmd}[/red]")

    async def process_query(self, query: str):
        """Handle natural language queries."""
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.write("\n[dim]분석 에이전트가 사고하는 중...[/dim]")
        
        try:
            # Check for active connection
            if not os.path.exists(self.registry_path):
                 chat_log.write("[yellow]연결된 데이터 소스가 없습니다. /connect 를 입력해 소스를 추가해 주세요.[/yellow]")
                 return

            # Execute via worker to keep UI alive
            self.run_worker(self._run_analysis(query))
        except Exception as e:
            chat_log.write(f"\n[bold red]Error:[/bold red] {e}")

    async def _run_analysis(self, query: str):
        """Orchestrator execution in background."""
        try:
            # For simplicity in this demo, we pick the first connection
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            conn_id = list(registry.keys())[0] if registry else None
            
            if not conn_id:
                self.call_from_thread(self.show_response, "연결된 소스가 없어 분석을 진행할 수 없습니다.")
                return

            result = await self.orchestrator.run(query, conn_id=conn_id)
            response = result.get('final_response', "분석 결과를 생성하지 못했습니다.")
            self.call_from_thread(self.show_response, response)
        except Exception as e:
            self.call_from_thread(self.show_response, f"에러 발생: {e}")

    def show_response(self, response: str):
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.write(f"\n[bold cyan]Agent:[/bold cyan] {response}\n")

    def action_clear_chat(self) -> None:
        self.query_one("#chat-log", RichLog).clear()

    def action_switch_project(self) -> None:
        def set_project(project_name: str) -> None:
            if project_name:
                self.current_project = project_name
                self._init_orchestrator(project_name)
                self.query_one("#chat-log", RichLog).write(f"\n[green]프로젝트가 '{project_name}'으로 전환되었습니다.[/green]")

        self.push_screen(ProjectScreen(self.current_project), set_project)

    async def action_quit(self) -> None:
        try:
            self.conn_mgr.close_all()
        except: pass
        self.exit()

def run_app():
    from backend.utils.pre_flight import run_pre_flight
    
    # Phase 0: Pre-flight Check (TUI 진입 전 선행 검사)
    try:
        if not run_pre_flight():
            # 의존성이나 인증이 안되었을 때 종료할지 여부는 checker에서 결정했으나,
            # 최소한 발자국은 남김
            pass
    except Exception as e:
        print(f"Pre-flight check failed: {e}")

    try:
        app = BI_AgentConsole()
        app.run()
    except Exception as e:
        logger.critical(f"App crashed on startup: {e}")
        print(f"CRITICAL ERROR: {e}\nCheck logs/tui.log for details.")

if __name__ == "__main__":
    run_app()
