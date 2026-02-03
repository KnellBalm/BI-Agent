import os
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal, Container, VerticalScroll
from textual.widgets import Label, Input, ListView, ListItem, Static, Header, Footer, DataTable, RichLog, OptionList, Button, Checkbox
from textual.binding import Binding

from backend.orchestrator import (
    auth_manager,
    quota_manager,
    context_manager,
    HUDStatusLine,
    CommandHistory,
    ErrorViewerScreen,
    MessageBubble,
    ThinkingPanel,
    StreamingMessageView,
    ToolActivityTracker
)
from backend.utils.logger_setup import setup_logger
from backend.utils.path_config import path_manager

# 리팩토링된 모듈들 임포트
from backend.orchestrator.screens import (
    AuthScreen, 
    ConnectionScreen, 
    ProjectScreen, 
    TableSelectionScreen,
    VisualAnalysisScreen
)
from backend.orchestrator.components import SidebarManager, CommandPalette
from backend.orchestrator.handlers import HandlerContext, CommandHandler, InputHandler

# Initialize localized logger
logger = setup_logger("tui", "tui.log")

class BI_AgentConsole(App):
    """
    BI-Agent Console Main Application.
    리팩토링 후: 컴포넌트 및 핸들러 위임을 통한 린(Lean) 아키텍처 구현.
    """
    
    TITLE = "BI-Agent Console"
    SUB_TITLE = "데이터 분석의 새로운 기준"
    
    # CSS_PATH = "bi_agent_console.tcss" # CSS 파일 분리 권장 (추후 작업)
    
    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("v", "show_visual_report", "Visual Report", show=True),
        Binding("ctrl+l", "clear_chat", "Clear Chat", show=True),
        Binding("slash", "focus_input_with_slash", "Command", show=False),
        Binding("f1", "show_help", "Help", show=True),
        Binding("ctrl+e", "show_errors", "Errors", show=False),
    ]

    def __init__(self):
        super().__init__()
        self.registry_path = path_manager.base_dir / "connections.json"
        self.command_history = CommandHistory()
        
        # 컴포넌트 및 핸들러 초기화 (지연 초기화 권장되나 여기선 명확성을 위해 __init__서 수행)
        self.sidebar_manager = SidebarManager(self)
        self.command_palette = CommandPalette(self)
        self.command_handler = CommandHandler(self)
        self.input_handler = InputHandler(self, self.command_palette, self.command_history)
        
        # 상태값
        self.palette_visible = False 
        
        # Legacy 지원용 COMMAND_LIST (CommandPalette와 동기화 필요)
        self.COMMAND_LIST = self.command_palette.commands

    def compose(self) -> ComposeResult:
        """UI 레이아웃 구성"""
        yield Header(show_clock=True)
        
        with Horizontal(id="main-layout"):
            # Left Sidebar
            with Vertical(id="sidebar"):
                yield Label("[bold]PROJECT[/bold]", classes="sidebar-title")
                yield Label("• [dim]default[/dim]", id="lbl-project")
                
                yield Label("\n[bold]STATUS[/bold]", classes="sidebar-title")
                yield Label("• Auth: [red]✘[/red]", id="lbl-auth")
                yield Label("• Context: [red]✘[/red]", id="lbl-context")
                
                yield Label("\n[bold]QUOTA USAGE[/bold]", classes="sidebar-title")
                yield Static("Loading...", id="lbl-quota")
                
                yield Label("\n[bold]CONNECTIONS[/bold]", classes="sidebar-title")
                yield Static("[dim]No sources.[/dim]", id="lbl-connections")
                
                yield Label("\n[bold]JOURNEY PROGRESS[/bold]", classes="sidebar-title")
                yield Static("Launch -> Auth -> Conn", id="lbl-journey")
                
                yield Label("\n[bold]ACTION RECOMMENDATION[/bold]", classes="sidebar-title")
                yield Static("초기 설정을 진행하세요.", id="lbl-recommend")

            # Main Chat Area
            with Vertical(id="chat-area"):
                yield HUDStatusLine(id="hud-status")
                
                with VerticalScroll(id="chat-log"):
                    yield MessageBubble(
                        role="system", 
                        content="[bold cyan]Welcome to BI-Agent Console v2.0![/bold cyan]\n"
                                "데이터 분석을 시작하려면 [b]/login[/b] 후 [b]/connect[/b] 명령어를 실행하세요.\n"
                                "[dim]도움말이 필요하면 F1 키를 누르세요.[/dim]"
                    )
                
                # Command Palette (Floating-like OptionList)
                cp = OptionList(id="command-menu")
                cp.add_class("hidden")
                yield cp
                
                with Horizontal(id="input-container"):
                    yield Input(placeholder="질문을 입력하거나 '/'로 명령어를 시작하세요...", id="user-input")
                    yield Button("Send", id="send-btn", variant="primary")

        yield Footer()

    async def on_mount(self) -> None:
        """초기화 및 배경 작업 시작"""
        # Auth 정보 로드
        auth_manager.load_credentials()
        
        # 10초마다 사이드바/HUD 업데이트
        self.set_timer(0, self._update_sidebar_loop)
        self.set_timer(1, self._update_hud_loop)
        
        # 초기 포커스
        self.query_one("#user-input").focus()
        logger.info("BI-Agent Console started")

    # --- 실시간 상태 업데이트 루프 ---
    
    async def _update_sidebar_loop(self) -> None:
        await self.sidebar_manager.update()
        self.set_timer(10, self._update_sidebar_loop)

    async def _update_hud_loop(self) -> None:
        """HUD 업데이트 (내부 로직 단순화 유지)"""
        try:
            hud = self.query_one("#hud-status", HUDStatusLine)
            model_name = "Ollama"
            for p, name in [("gemini", "Gemini 2.0 Flash"), ("claude", "Claude 3.5 Sonnet"), ("openai", "GPT-4o")]:
                if auth_manager.is_authenticated(p):
                    model_name = name
                    break
            hud.update_model(model_name)
            hud.update_context(20.0)
            self.set_timer(10, self._update_hud_loop)
        except Exception as e:
            logger.error(f"HUD update error: {e}")

    # --- 이벤트 핸들러 ---

    def on_input_changed(self, event: Input.Changed) -> None:
        """입력창 변경 시 팔레트 업데이트"""
        text = event.value
        if text.startswith("/"):
            self.command_palette.update(text)
            self.palette_visible = self.command_palette.visible
        else:
            self.command_palette.hide()
            self.palette_visible = False
        
        if text:
            self.command_history.reset_navigation()

    async def on_key(self, event) -> None:
        """입력 가로채기 및 핸들러 위임"""
        # InputHandler에 위임
        handled = await self.input_handler.handle_key(event)
        if handled:
            event.prevent_default()
            event.stop()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """명령어 선택 처리"""
        if event.option_list.id == "command-menu":
            option_id = event.option.id
            if option_id:
                # 간단한 매핑 후 실행
                cmd_map = {c[2]: c[0] for c in self.COMMAND_LIST}
                cmd = cmd_map.get(option_id, "/" + str(option_id))
                
                user_input = self.query_one("#user-input", Input)
                user_input.value = cmd
                self.command_palette.hide()
                self.palette_visible = False
                user_input.focus()
                
                asyncio.create_task(self.handle_command(cmd))

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """입력 제출 처리"""
        user_text = event.value.strip()
        if not user_text: return
        
        # UI 업데이트
        chat_log = self.query_one("#chat-log", VerticalScroll)
        chat_log.mount(MessageBubble(role="user", content=user_text))
        chat_log.scroll_end(animate=False)
        self.query_one("#user-input", Input).value = ""
        
        # 히스토리 저장
        context = "slash_command" if user_text.startswith("/") else "query"
        self.command_history.add_command(user_text, context=context)
        
        # 라우팅
        if user_text.startswith("/"):
            await self.handle_command(user_text)
        else:
            await self.process_query(user_text)

    # --- 핵심 비즈니스 로직 위임 및 구현 ---

    async def handle_command(self, cmd_text: str) -> None:
        """CommandHandler에 위임"""
        await self.command_handler.handle(cmd_text)

    async def process_query(self, query: str) -> None:
        """에이전트 쿼리 처리 (추후 Orchestrator 위임 대상)"""
        chat_log = self.query_one("#chat-log", VerticalScroll)
        
        # Thinking Panel 표시
        thinking = ThinkingPanel()
        chat_log.mount(thinking)
        chat_log.scroll_end()
        
        try:
            # 시뮬레이션: 실제로는 Orchestrator 호출
            await asyncio.sleep(1)
            thinking.remove()
            
            response = f"[green]'{query}'[/green]에 대한 분석 결과입니다. (데모 버전)"
            chat_log.mount(MessageBubble(role="assistant", content=response))
            
        except Exception as e:
            thinking.remove()
            chat_log.mount(MessageBubble(role="system", content=f"[red]Error: {e}[/red]"))
        
        chat_log.scroll_end()

    # --- 액션 핸들러 (Bindings) ---

    async def action_quit(self) -> None:
        """애플리케이션 종료"""
        self.exit()

    def action_show_help(self) -> None:
        asyncio.create_task(self.handle_command("/help"))

    def action_show_errors(self) -> None:
        self.push_screen(ErrorViewerScreen())

    def action_clear_chat(self) -> None:
        chat_log = self.query_one("#chat-log", VerticalScroll)
        chat_log.remove_children()
        self.notify("Chat cleared")

    def action_show_visual_report(self) -> None:
        # VisualAnalysisScreen은 이미 import됨
        from backend.orchestrator.screens.visual_analysis_screen import VisualAnalysisScreen
        self.push_screen(VisualAnalysisScreen())

    def action_focus_input_with_slash(self) -> None:
        user_input = self.query_one("#user-input", Input)
        user_input.focus()
        if not user_input.value.startswith("/"):
            user_input.value = "/"
        user_input.cursor_position = len(user_input.value)

    # --- 백그라운드 워커 메서드 (CommandHandler 등에서 대리 호출용) ---

    async def _run_scan(self, conn_id: str):
        self.notify(f"Scanning {conn_id}...")
        await asyncio.sleep(2)
        self.notify(f"Scan complete for {conn_id}", severity="information")
        await self.sidebar_manager.update()

    async def _run_explore(self, query: Optional[str]):
        # TableSelectionScreen 연동
        def on_table_selected(table_name: str):
            if table_name:
                self.notify(f"Selected table: {table_name}")
                context_manager.active_table = table_name
                asyncio.create_task(self.sidebar_manager.update())

        self.push_screen(TableSelectionScreen(search_query=query), callback=on_table_selected)

    def action_switch_project(self):
        self.push_screen(ProjectScreen())

def run_app():
    """BI-Agent Console을 실행하는 엔트리 포인트."""
    app = BI_AgentConsole()
    app.run()

if __name__ == "__main__":
    run_app()
