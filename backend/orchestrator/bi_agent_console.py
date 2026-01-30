import os
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal, Container, VerticalScroll
from textual.widgets import Label, Input, ListView, ListItem, Static, Header, Footer, DataTable, RichLog, OptionList, Button
from textual.widgets.option_list import Option
from textual.screen import ModalScreen
from textual.binding import Binding

from backend.orchestrator.auth_manager import auth_manager
from backend.orchestrator.quota_manager import quota_manager
from backend.utils.logger_setup import setup_logger
from backend.utils.path_config import path_manager
from backend.orchestrator.hud_statusline import HUDStatusLine
from backend.orchestrator.message_components import (
    MessageBubble, 
    ThinkingPanel, 
    StreamingMessageView,
    ToolActivityTracker
)

# Initialize localized logger
logger = setup_logger("tui", "tui.log")

class AuthScreen(ModalScreen):
    """
    LLM Provider 설정 안내 화면 (CLI-style)
    사용자에게 환경변수 또는 credentials.json 파일로 API 키를 설정하는 방법을 안내합니다.
    """
    
    CSS = """
    AuthScreen {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }
    #auth-modal {
        width: 70;
        height: auto;
        background: #1a1b1e;
        border: solid #2d2f34;
        padding: 2 4;
    }
    #auth-title {
        text-align: center;
        color: #f8fafc;
        text-style: bold;
        margin-bottom: 1;
    }
    .guide-text {
        color: #94a3b8;
        margin: 1 0;
        text-align: center;
    }
    .credential-path {
        color: #7c3aed;
        text-style: bold italic;
        text-align: center;
    }
    #provider-list {
        height: 5;
        margin: 1 0;
        background: #111214;
        border: solid #2d2f34;
    }
    #detail-container {
        height: auto;
        margin: 1 0;
        padding: 1 2;
        background: #111214;
        border-left: tall #7c3aed;
    }
    #api-key-container {
        margin-top: 1;
        border: solid #2d2f34;
        background: #111214;
        padding: 1;
    }
    #api-key-input {
        background: #1a1b1e;
        border: solid #404040;
        margin-bottom: 1;
        color: #f8fafc;
        width: 100%;
    }
    #api-key-input:focus {
        border: solid #7c3aed;
    }
    #save-key-btn {
        width: 100%;
        background: #7c3aed;
        color: white;
        text-style: bold;
    }
    #save-key-btn:hover {
        background: #6d28d9;
    }
    """
    
    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("1", "select_gemini", "Gemini"),
        ("2", "select_claude", "Claude"),
        ("3", "select_openai", "OpenAI"),
    ]
    
    def __init__(self):
        super().__init__()
        self.selected_provider = None
        logger.debug("AuthScreen initialized (CLI-style)")
    
    def compose(self) -> ComposeResult:
        with Container(id="auth-modal"):
            yield Label("LLM Provider Authentication", id="auth-title")
            
            yield Label("BI-Agent reads API keys automatically from your environment or config file.", classes="guide-text")
            yield Label(f"Config: ~/.bi-agent/credentials.json", classes="credential-path")
            
            yield OptionList(
                Option("🔑 Gemini (Google)", id="gemini"),
                Option("🤖 Claude (Anthropic)", id="claude"),
                Option("💡 ChatGPT (OpenAI)", id="openai"),
                id="provider-list"
            )
            
            yield Container(id="detail-container")
            
            with Vertical(id="api-key-container"):
                yield Label("[dim]Enter API Key manually:[/dim]")
                yield Input(id="api-key-input", placeholder="Paste your API key here...", password=True)
                yield Button("Save & Authenticate", id="save-key-btn")
            
            yield Label("\n[dim]Press ESC to skip if already configured.[/dim]", classes="guide-text")
    
    def on_mount(self) -> None:
        """화면 마운트 시 첫 번째 항목 선택"""
        logger.info("AuthScreen mounted - showing setup instructions")
        option_list = self.query_one("#provider-list", OptionList)
        option_list.focus()
    
    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """사용자가 공급자를 선택했을 때 상세 안내 표시"""
        provider = event.option.id
        logger.info(f"User selected provider: {provider}")
        self.selected_provider = provider
        self._show_provider_details(provider)
    
    def _show_provider_details(self, provider: str) -> None:
        """선택한 공급자의 상세 설정 방법 표시"""
        try:
            detail_container = self.query_one("#detail-container", Container)
            detail_container.remove_children()
            
            details = {
                "gemini": {
                    "name": "Gemini (Google AI Studio)",
                    "env_var": "GEMINI_API_KEY",
                    "api_url": "https://aistudio.google.com/app/apikey",
                    "cred_key": "gemini"
                },
                "claude": {
                    "name": "Claude (Anthropic)",
                    "env_var": "ANTHROPIC_API_KEY",
                    "api_url": "https://console.anthropic.com/",
                    "cred_key": "claude"
                },
                "openai": {
                    "name": "ChatGPT (OpenAI)",
                    "env_var": "OPENAI_API_KEY",
                    "api_url": "https://platform.openai.com/api-keys",
                    "cred_key": "openai"
                }
            }
            
            info = details[provider]
            
            # compose() 외부에서는 with 구문 대신 직접 mount 호출
            detail_container.mount(Label(f"[bold cyan]{info['name']} 설정 방법[/bold cyan]"))
            detail_container.mount(Label(""))
            detail_container.mount(Label(f"[bold]방법 1: 환경변수 설정[/bold]"))
            detail_container.mount(Label(f"  export {info['env_var']}=\"your-api-key-here\""))
            detail_container.mount(Label(""))
            detail_container.mount(Label(f"[bold]방법 2: credentials.json 파일 편집[/bold]"))
            detail_container.mount(Label(f"  파일: ~/.bi-agent/credentials.json"))
            detail_container.mount(Label(f'  {{"providers": {{"{info['cred_key']}": {{"key": "your-api-key-here"}}}}}}'))
            detail_container.mount(Label(""))
            detail_container.mount(Label(f"[bold]API 키 발급:[/bold] {info['api_url']}", classes="api-link"))
            
            logger.debug(f"Displayed setup details for {provider}")
        except Exception as e:
            logger.error(f"Error showing provider details: {e}", exc_info=True)
    
    def action_select_gemini(self) -> None:
        """숫자 키 1로 Gemini 선택"""
        option_list = self.query_one("#provider-list", OptionList)
        option_list.highlighted = 0
        option_list.action_select()
    
    def action_select_claude(self) -> None:
        """숫자 키 2로 Claude 선택"""
        option_list = self.query_one("#provider-list", OptionList)
        option_list.highlighted = 1
        option_list.action_select()
    
    def action_select_openai(self) -> None:
        """숫자 키 3로 OpenAI 선택"""
        option_list = self.query_one("#provider-list", OptionList)
        option_list.highlighted = 2
        option_list.action_select()
    
    def action_dismiss(self) -> None:
        """ESC 키로 모달 닫기"""
        logger.info("AuthScreen dismissed by user")
        self.dismiss(False)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """API 키 저장 버튼 클릭"""
        if event.button.id == "save-key-btn":
            self._save_api_key()
    
    def _save_api_key(self) -> None:
        """입력된 API 키를 credentials.json에 저장"""
        if not self.selected_provider:
            self.notify("먼저 LLM 공급자를 선택해주세요!", severity="warning")
            return
        
        api_key_input = self.query_one("#api-key-input", Input)
        api_key = api_key_input.value.strip()
        
        if not api_key:
            self.notify("API 키를 입력해주세요!", severity="warning")
            return
        
        try:
            # credentials.json 파일 경로
            creds_path = path_manager.home_dir / "credentials.json"
            
            # 기존 credentials 읽기 또는 새로 생성
            if creds_path.exists():
                with open(creds_path, 'r', encoding='utf-8') as f:
                    credentials = json.load(f)
            else:
                credentials = {"providers": {}}
            
            # API 키 저장
            if "providers" not in credentials:
                credentials["providers"] = {}
            
            credentials["providers"][self.selected_provider] = {"key": api_key}
            
            # 파일에 저장
            with open(creds_path, 'w', encoding='utf-8') as f:
                json.dump(credentials, f, indent=2, ensure_ascii=False)
            
            logger.info(f"API key saved for {self.selected_provider}")
            self.notify(f"✅ {self.selected_provider.capitalize()} API 키가 저장되었습니다!", severity="information")
            
            # 입력 필드 초기화
            api_key_input.value = ""
            
            # auth_manager에 즉시 반영
            auth_manager.load_credentials()
            
        except Exception as e:
            logger.error(f"Error saving API key: {e}", exc_info=True)
            self.notify(f"❌ API 키 저장 실패: {e}", severity="error")

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
        background: #0c0c0e;
    }
    #main-container {
        width: 100%;
        height: 100%;
    }
    #content-area {
        height: 1fr;
    }
    #chat-area {
        width: 100%;
        height: 100%;
    }
    #chat-log {
        height: 1fr;
        border: none;
        background: #0c0c0e;
        padding: 1 2;
    }
    #input-bar {
        height: auto;
        margin: 0 1;
        background: #0c0c0e;
        border-top: solid #21262d;
        layout: vertical;
    }
    #command-menu {
        height: auto;
        max-height: 8;
        background: #161b22;
        border: solid #30363d;
        display: none;
        margin: 0 4;
        padding: 0 0;
    }
    #command-menu.visible {
        display: block;
    }
    #command-menu > .option-list--option {
        padding: 0 1;
    }
    #command-menu > .option-list--option-highlighted {
        background: #7c3aed;
        color: #f8fafc;
    }
    #input-container {
        height: 3;
        layout: horizontal;
    }
    #input-bar:focus-within {
        border-top: solid #7c3aed;
    }
    #input-prompt {
        color: #7c3aed;
        padding: 0 1;
        text-style: bold;
    }
    Input {
        background: transparent;
        border: none;
        width: 100%;
        color: #f8fafc;
    }
    #command-palette {
        display: none;
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
            with Horizontal(id="content-area"):
                with Vertical(id="chat-area"):
                    yield VerticalScroll(id="chat-log")
                    
                    with Vertical(id="input-bar"):
                        yield OptionList(
                            Option("/analyze   [dim]데이터 심층 분석[/dim]", id="analyze"),
                            Option("/explore   [dim]데이터 탐색[/dim]", id="explore"),
                            Option("/connect   [dim]소스 연결[/dim]", id="connect"),
                            Option("/project   [dim]프로젝트 전환[/dim]", id="project"),
                            Option("/login     [dim]LLM 인증[/dim]", id="login"),
                            Option("/help      [dim]도움말[/dim]", id="help"),
                            id="command-menu"
                        )
                        with Horizontal(id="input-container"):
                            yield Label("❯", id="input-prompt")
                            yield Input(id="user-input", placeholder="Type a command or ask a question... (Type / to select)")
        yield Footer()

    async def on_mount(self) -> None:
        self.title = "BI-Agent Terminal"
        
        # 채팅 로그를 VerticalScroll로 가져오기
        chat_log = self.query_one("#chat-log", VerticalScroll)

        # 환영 메시지 및 배너 표시
        banner_art = (
            "\n"
            "[bold #7c3aed]   ╔═══════════════════════════════════════╗[/bold #7c3aed]\n"
            "[bold #7c3aed]   ║         ⚡ BI-AGENT TERMINAL          ║[/bold #7c3aed]\n"
            "[bold #7c3aed]   ║   Advanced Autonomous BI Co-pilot     ║[/bold #7c3aed]\n"
            "[bold #7c3aed]   ╚═══════════════════════════════════════╝[/bold #7c3aed]\n"
            "\n"
            "[dim]Welcome back. Everything is ready for analysis.[/dim]\n"
            "[dim]Type [b]/help[/b] to see available commands.[/dim]\n"
        )
        welcome_msg = MessageBubble(
            role="system",
            content=banner_art
        )
        chat_log.mount(welcome_msg)
        
        # 입력 필드에 자동 포커스
        self.set_focus(self.query_one("#user-input", Input))
        
        logger.info("Terminal TUI mounted successfully.")

    async def _update_sidebar(self) -> None:
        """Update the sidebar status information."""
        # Auth status
        auth_lbl = self.query_one("#lbl-auth", Label)
        if auth_manager.is_authenticated("gemini") or auth_manager.is_authenticated("claude") or auth_manager.is_authenticated("openai"):
            auth_lbl.update("• Auth: [green]✔ Connected[/green]")
        else:
            auth_lbl.update("• Auth: [red]✘ Login Required[/red]")
            self.push_screen(AuthScreen())

        # Quota status - 시각화 향상
        quota_lbl = self.query_one("#lbl-quota", Static)
        quota_text = ""
        for p in ["gemini", "claude", "openai", "ollama"]:
            status = quota_manager.get_provider_status(p)
            is_exhausted = status.get("exhausted", False)
            
            usage = status.get('daily_count', 0)
            limit = status.get('limit', 1500)
            
            # 시각적 프로그레스 바
            if limit != "∞" and isinstance(limit, int):
                percent = min(100, int((usage / limit) * 100))
                bar_len = 15
                filled = int(percent / 100 * bar_len)
                bar = "━" * filled + "─" * (bar_len - filled)
                
                # 컬러 코딩
                if percent < 50:
                    color = "green"
                elif percent < 80:
                    color = "yellow"
                else:
                    color = "red"
                
                # 이모지
                emoji = "💎" if p == "gemini" else "🤖" if p == "claude" else "💡" if p == "openai" else "🏠"
                
                quota_text += f"{emoji} [{color}]{bar}[/{color}] {usage}/{limit} ({percent}%)\n"
            else:
                emoji = "💎" if p == "gemini" else "🤖" if p == "claude" else "💡" if p == "openai" else "🏠"
                quota_text += f"{emoji} {p.capitalize()}: {usage}/∞\n"
        
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
    
    async def _update_hud(self) -> None:
        """현재 모델 및 컬텍스트 상태로 HUD 업데이트"""
        try:
            hud = self.query_one("#hud-status", HUDStatusLine)
            
            # 현재 모델 확인 (가장 먼저 인증된 모델)
            if auth_manager.is_authenticated("gemini"):
                hud.update_model("Gemini 2.0 Flash")
            elif auth_manager.is_authenticated("claude"):
                hud.update_model("Claude 3.5 Sonnet")
            elif auth_manager.is_authenticated("openai"):
                hud.update_model("GPT-4o")
            else:
                hud.update_model("Ollama")
            
            # 컬텍스트 사용률 시뮬레이션 (실제로는 LLM API에서 가져와야 함)
            # 여기서는 예시로 20%로 설정
            hud.update_context(20.0)
            
            # 10초마다 업데이트
            self.set_timer(10, self._update_hud)
        except Exception as e:
            logger.error(f"Error updating HUD: {e}")

    def on_input_changed(self, event: Input.Changed) -> None:
        """슬래시(/) 입력 시 세로 메뉴 표시 및 키보드 네비게이션 준비"""
        menu = self.query_one("#command-menu", OptionList)
        if event.value.startswith("/"):
            menu.add_class("visible")
            self.palette_visible = True
            # 첫 번째 항목 선택
            if menu.option_count > 0:
                menu.highlighted = 0
        else:
            menu.remove_class("visible")
            self.palette_visible = False

    def on_key(self, event) -> None:
        """Handle global keys for menu navigation and Tab autocomplete."""
        menu = self.query_one("#command-menu", OptionList)
        user_input = self.query_one("#user-input", Input)
        
        # Tab 자동완성: 입력값이 /로 시작하면 일치하는 명령어 자동완성
        if event.key == "tab" and user_input.has_focus:
            current_text = user_input.value.strip()
            if current_text.startswith("/"):
                commands = ["analyze", "explore", "connect", "project", "login", "help"]
                prefix = current_text[1:].lower()  # / 제거
                
                # 접두사와 일치하는 명령어 찾기
                matches = [cmd for cmd in commands if cmd.startswith(prefix)]
                
                if len(matches) == 1:
                    # 정확히 하나만 일치하면 자동완성
                    user_input.value = "/" + matches[0]
                    user_input.cursor_position = len(user_input.value)
                elif len(matches) > 1:
                    # 여러 개 일치하면 공통 접두사까지 완성
                    common = matches[0]
                    for m in matches[1:]:
                        while not m.startswith(common):
                            common = common[:-1]
                    if len(common) > len(prefix):
                        user_input.value = "/" + common
                        user_input.cursor_position = len(user_input.value)
                
                event.prevent_default()
                return
        
        if self.palette_visible and user_input.has_focus:
            if event.key == "escape":
                menu.remove_class("visible")
                self.palette_visible = False
                event.prevent_default()
            elif event.key == "up":
                # 입력창에서 메뉴 항목 위로 이동
                if menu.highlighted is not None and menu.highlighted > 0:
                    menu.highlighted -= 1
                event.prevent_default()
            elif event.key == "down":
                # 입력창에서 메뉴 항목 아래로 이동
                if menu.highlighted is not None and menu.highlighted < menu.option_count - 1:
                    menu.highlighted += 1
                event.prevent_default()
            elif event.key == "enter":
                # 메뉴에서 선택된 항목 실행
                if menu.highlighted is not None:
                    option = menu.get_option_at_index(menu.highlighted)
                    if option and option.id:
                        command_map = {
                            "analyze": "/analyze",
                            "explore": "/explore",
                            "connect": "/connect",
                            "project": "/project",
                            "login": "/login",
                            "help": "/help"
                        }
                        cmd = command_map.get(option.id, "/" + option.id)
                        user_input.value = ""
                        menu.remove_class("visible")
                        self.palette_visible = False
                        import asyncio
                        asyncio.create_task(self.handle_command(cmd))
                        event.prevent_default()

    def action_hide_palette(self) -> None:
        """Force hide the menu."""
        menu = self.query_one("#command-menu", OptionList)
        menu.remove_class("visible")
        self.palette_visible = False
        self.query_one("#user-input", Input).focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle command palette selection with Enter key"""
        # 명령 팔레트 이벤트가 아닌 경우(예: AuthScreen의 OptionList) 무시
        if event.option_list.id != "command-palette":
            return
            
        import asyncio
        palette = self.query_one("#command-palette", OptionList)
        palette.remove_class("visible")
        self.palette_visible = False
        
        # 선택된 명령어를 입력 필드에 설정
        command_id = event.option.id
        if command_id:
            user_input = self.query_one("#user-input", Input)
            
            # 명령어 매핑
            command_map = {
                "analyze": "/analyze",
                "explore": "/explore",
                "connect": "/connect",
                "project": "/project",
                "login": "/login",
                "report": "/report",
                "help": "/help"
            }
            
            cmd = command_map.get(command_id, "/" + command_id)
            user_input.value = cmd
            
            # 입력으로 포커스 복귀 및 명령 실행
            user_input.focus()
            # Enter를 누른 것처럼 실행
            asyncio.create_task(self.handle_command(cmd))

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle final input execution."""
        user_text = event.value.strip()
        if not user_text:
            return

        chat_log = self.query_one("#chat-log", VerticalScroll)
        
        # 사용자 메시지 추가
        user_msg = MessageBubble(role="user", content=user_text)
        chat_log.mount(user_msg)
        chat_log.scroll_end(animate=False)
        
        self.query_one("#user-input", Input).value = ""
        
        # 크래시 방지: 제거된 HUD 참조 제거
        # (기존 hud = self.query_one("#hud-status") 부분 삭제)
        
        if user_text.startswith("/"):
            await self.handle_command(user_text)
        else:
            await self.process_query(user_text)

    async def handle_command(self, cmd_text: str):
        """Routing for slash commands."""
        parts = cmd_text.split()
        cmd = parts[0]
        chat_log = self.query_one("#chat-log", VerticalScroll)
        
        if cmd == "/connect":
            msg = MessageBubble(role="system", content="[dim]데이터 소스 관리 화면으로 전환합니다... (곧 지원 예정)[/dim]")
            chat_log.mount(msg)
        elif cmd == "/project":
            self.action_switch_project()
        elif cmd == "/login":
            msg = MessageBubble(role="system", content="[dim]인증 및 계정 설정 화면을 엽니다...[/dim]")
            chat_log.mount(msg)
            self.push_screen(AuthScreen())
        elif cmd == "/analyze":
            msg = MessageBubble(role="system", content="[dim]상세 분석 모드로 전환합니다... (곧 지원 예정)[/dim]")
            chat_log.mount(msg)
        elif cmd == "/explore":
            msg = MessageBubble(role="system", content="[dim]데이터 탐색 모드로 전환합니다... (곧 지원 예정)[/dim]")
            chat_log.mount(msg)
        elif cmd == "/help":
            help_content = (
                "[bold cyan]사용 가능한 명령어:[/bold cyan]\n\n"
                "[b]/analyze[/b]: 데이터 심층 분석 모드 실행\n"
                "[b]/explore[/b]: 데이터 탐색 및 프로파일링\n"
                "[b]/connect[/b]: 데이터 소스 관리 및 연결 설정\n"
                "[b]/project[/b]: 현재 분석 프로젝트 전환\n"
                "[b]/login[/b]: LLM 계정 및 API Key 설정\n"
                "[b]/report[/b]: 생성된 리포트 센터 방문\n"
                "[b]/help[/b]: 이 도움말 표시"
            )
            msg = MessageBubble(role="system", content=help_content)
            chat_log.mount(msg)
        else:
            msg = MessageBubble(role="system", content=f"[red]알 수 없는 명령어입니다: {cmd}[/red]")
            chat_log.mount(msg)
        
        chat_log.scroll_end(animate=False)

    async def process_query(self, query: str):
        """Handle natural language queries."""
        chat_log = self.query_one("#chat-log", VerticalScroll)
        thinking_msg = MessageBubble(role="system", content="[dim]분석 에이전트가 사고하는 중...[/dim]")
        chat_log.mount(thinking_msg)
        chat_log.scroll_end(animate=False)
        
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
        chat_log = self.query_one("#chat-log", VerticalScroll)
        agent_msg = MessageBubble(role="agent", content=response)
        chat_log.mount(agent_msg)
        chat_log.scroll_end(animate=False)

    def action_clear_chat(self) -> None:
        chat_log = self.query_one("#chat-log", VerticalScroll)
        # 모든 자식 제거
        chat_log.remove_children()
        # 환영 메시지 다시 추가
        welcome_msg = MessageBubble(
            role="system",
            content=(
                "[bold cyan]어서오세요! BI-Agent Entrance Hall입니다[/bold cyan]\n"
                "분석가의 생산성을 3배 이상 높이는 지능형 조수입니다.\n\n"
                "[dim]명령어: /help 로 시작하거나 질문을 입력하세요.[/dim]"
            )
        )
        chat_log.mount(welcome_msg)

    def action_switch_project(self) -> None:
        def set_project(project_name: str) -> None:
            if project_name:
                # 프로젝트 전환 메시지
                chat_log = self.query_one("#chat-log", VerticalScroll)
                msg = MessageBubble(
                    role="system",
                    content=f"[green]Project switched to '{project_name}'.[/green]"
                )
                chat_log.mount(msg)
                chat_log.scroll_end(animate=False)

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
