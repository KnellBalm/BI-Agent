import os
import sys
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

import click
from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal, Container, VerticalScroll
from textual.widgets import Label, Input, ListView, ListItem, Static, Header, Footer, DataTable, RichLog, OptionList, Button, Checkbox
from textual.binding import Binding

from backend.orchestrator import (
    auth_manager,
    quota_manager,
    context_manager,
    ConnectionManager,
    HUDStatusLine,
    CommandHistory,
    ErrorViewerScreen,
    MessageBubble,
    ThinkingPanel,
    StreamingMessageView,
    ToolActivityTracker,
    ResultBlock
)
from backend.agents.data_source.connection_manager import ConnectionManager as AgentConnectionManager
from backend.orchestrator.orchestrators.agentic_orchestrator import AgenticOrchestrator
from backend.utils.logger_setup import setup_logger
from backend.utils.path_config import path_manager

# 리팩토링된 모듈들 임포트
from backend.orchestrator.screens import (
    ProjectScreen,
    TableSelectionScreen,
    VisualAnalysisScreen,
    DatabaseExplorerScreen
)
from backend.orchestrator.components import SidebarManager, CommandPalette
from backend.orchestrator.handlers import HandlerContext, CommandHandler, InputHandler
from backend.orchestrator.ui.components.schema_explorer_sidebar import SchemaExplorerSidebar

# Initialize localized logger
logger = setup_logger("tui", "tui.log")

class BI_AgentConsole(App):
    """
    BI-Agent Console Main Application.
    리팩토링 후: 컴포넌트 및 핸들러 위임을 통한 린(Lean) 아키텍처 구현.
    """
    
    TITLE = "BI-Agent Console"
    SUB_TITLE = "데이터 분석의 새로운 기준"
    
    CSS_PATH = ["ui/app_styles.tcss"]
    
    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("v", "show_visual_report", "Visual Report", show=True),
        Binding("ctrl+l", "clear_chat", "Clear Chat", show=True),
        Binding("slash", "focus_input_with_slash", "Command", show=False),
        Binding("f1", "show_help", "Help", show=True),
        Binding("ctrl+e", "toggle_explore", "Explore", show=True),
    ]

    def __init__(self):
        super().__init__()
        # Use the same registry path as AgentConnectionManager for consistency
        self.registry_path = path_manager.get_project_path("default") / "connections.json"

        # Orchestrator's ConnectionManager (for UI and config management)
        self.conn_mgr = ConnectionManager(str(self.registry_path))

        # Agent's ConnectionManager (for schema scanning and query execution)
        # Uses project_id="default" to match the same registry path
        self.agent_conn_mgr = AgentConnectionManager(project_id="default")

        self.command_history = CommandHistory()

        # 컴포넌트 및 핸들러 초기화 (지연 초기화 권장되나 여기선 명확성을 위해 __init__서 수행)
        self.sidebar_manager = SidebarManager(self)
        self.command_palette = CommandPalette(self)
        self.command_handler = CommandHandler(self)
        self.input_handler = InputHandler(self, self.command_palette, self.command_history)

        # QuestionFlowEngine 초기화 (chat_log는 on_mount에서 설정)
        from backend.orchestrator.services.question_flow import QuestionFlowEngine
        self.flow_engine = QuestionFlowEngine(app=self)

        # AgenticOrchestrator (lazy init — LLM 키 설정 후 초기화)
        self._orchestrator: Optional[AgenticOrchestrator] = None

        # 상태값
        self.palette_visible = False

        # Legacy 지원용 COMMAND_LIST (CommandPalette와 동기화 필요)
        self.COMMAND_LIST = self.command_palette.commands

    def compose(self) -> ComposeResult:
        """UI 레이아웃 구성: 하단 고정 프롬프트 + 좌측 스키마 사이드바 + 상단 스크롤 히스토리"""
        
        # 보이지 않는 상태 사이드바 (기존 로직이 깨지지 않게 DOM에만 유지)
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

        # 메인 영역
        yield Header(show_clock=True)
        yield HUDStatusLine(id="hud-status", classes="hud-docked")

        # 인라인 스키마 탐색기 사이드바 (좌측 도킹, 기본 숨김)
        yield SchemaExplorerSidebar(
            agent_conn_mgr=self.agent_conn_mgr,
            id="schema-sidebar"
        )
        
        with VerticalScroll(id="chat-log"):
            yield MessageBubble(
                role="system",
                content="""[bold cyan]    ____  ____     ___                    __
   / __ )/  _/    /   | ____ ____  ____  / /_
  / __  |/ /_____/ /| |/ __ `/ _ \\/ __ \\/ __/
 / /_/ // /_____/ ___ / /_/ /  __/ / / / /_  
/_____/___/    /_/  |_\\__, /\\___/_/ /_/\\__/  
                     /____/                  [/bold cyan]

[dim]v0.1.0 · /help 로 도움말 | Ctrl+E 스키마 탐색[/dim]"""
            )

        # 명령어 팔레트 (드롭업 컨셉으로 입력창 위에 띄움)
        cp = OptionList(id="command-menu")
        cp.display = False
        yield cp

        # 고정 프롬프트 입력창 (화면 하단)
        with Horizontal(id="input-container"):
            yield Input(placeholder="> 질문을 입력하세요... ('/' 로 명령어 특수 기능 제공)", id="user-input")
            yield Button("Send", id="send-btn", variant="primary")
            
        yield Footer()

    async def on_mount(self) -> None:
        """초기화 및 배경 작업 시작"""
        # Auth 정보 로드
        auth_manager.load_credentials()

        # QuestionFlowEngine에 chat_log 참조 설정
        chat_log = self.query_one("#chat-log")
        self.flow_engine.chat_log = chat_log

        # 0.1초마다 사이드바/HUD 업데이트 (간격을 0으로 하면 최신 Textual에서 ZeroDivisionError 발생 가능)
        self.set_timer(0.1, self._update_sidebar_loop)
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

        # If flow is not active, ignore empty submissions
        if not user_text and not self.flow_engine.is_active():
            return

        # Clear input field first
        self.query_one("#user-input", Input).value = ""

        # CRITICAL: Check flow BEFORE mounting user bubble (for password masking)
        if self.flow_engine.is_active():
            consumed = await self.flow_engine.handle_input(user_text)
            if consumed:
                return  # Flow handled it (rendered its own answer bubble)
            # If not consumed (e.g., /help), fall through to normal routing
            if not user_text:
                return  # Still ignore empty after passthrough commands

        # Normal flow: route command or query
        chat_log = self.query_one("#chat-log", VerticalScroll)
        
        # 히스토리 저장
        context = "slash_command" if user_text.startswith("/") else "query"
        self.command_history.add_command(user_text, context=context)

        # 라우팅
        if user_text.startswith("/"):
            chat_log.mount(MessageBubble(role="user", content=user_text))
            chat_log.scroll_end(animate=False)
            await self.handle_command(user_text)
        else:
            block = ResultBlock(query=user_text)
            chat_log.mount(block)
            chat_log.scroll_end(animate=False)
            await self.process_query(user_text, block)

    # --- 핵심 비즈니스 로직 위임 및 구현 ---

    async def handle_command(self, cmd_text: str) -> None:
        """CommandHandler에 위임"""
        await self.command_handler.handle(cmd_text)

    def _get_orchestrator(self) -> AgenticOrchestrator:
        """AgenticOrchestrator 인스턴스를 지연 생성합니다."""
        if self._orchestrator is None:
            try:
                self._orchestrator = AgenticOrchestrator(
                    connection_manager=self.conn_mgr,
                    use_checkpointer=False,
                )
                logger.info("AgenticOrchestrator initialized successfully")
            except Exception as e:
                logger.error(f"AgenticOrchestrator init failed: {e}")
                raise
        return self._orchestrator

    async def process_query(self, query: str, block: ResultBlock) -> None:
        """에이전트 쿼리 처리 — AgenticOrchestrator ReAct 루프 실행"""
        chat_log = self.query_one("#chat-log", VerticalScroll)

        # Thinking Panel 표시
        thinking = ThinkingPanel()
        chat_log.mount(thinking)
        chat_log.scroll_end()

        try:
            orchestrator = self._get_orchestrator()

            # ReAct 루프 실행
            result = await orchestrator.run(query, context={
                "active_connection": getattr(self, '_active_conn_id', None),
            })

            thinking.remove()

            if result["status"] == "success":
                response = result["final_response"]
                iter_count = result.get("iteration_count", 0)
                if iter_count > 1:
                    footer = f"\n[dim]*({iter_count} reasoning iterations)*[/dim]"
                    response += footer
                
                block.update_response(response)
            else:
                block.update_response(f"**[Error]** {result.get('final_response', 'Unknown error')}")

        except Exception as e:
            thinking.remove()
            logger.error(f"process_query error: {e}", exc_info=True)
            if "API key" in str(e) or "authentication" in str(e).lower():
                msg = "LLM API 키가 설정되지 않았습니다. `/login` 명령어로 먼저 설정해주세요."
            else:
                msg = f"쿼리 처리 중 오류가 발생했습니다: {e}"
            block.update_response(msg)

        chat_log.scroll_end()

    # --- 액션 핸들러 (Bindings) ---

    async def action_quit(self) -> None:
        """애플리케이션 종료"""
        self.exit()

    def action_show_help(self) -> None:
        asyncio.create_task(self.handle_command("/help"))

    def action_toggle_explore(self) -> None:
        """Ctrl+E: 스키마 탐색기 사이드바 토글"""
        sidebar = self.query_one("#schema-sidebar", SchemaExplorerSidebar)
        if sidebar.display:
            sidebar.hide_sidebar()
        else:
            conn_id = getattr(self, '_active_conn_id', None) or context_manager.active_conn_id
            if conn_id:
                self._sync_connection(conn_id)
                sidebar.show_for_connection(conn_id)
            else:
                self.notify("활성화된 연결이 없습니다. /connect 를 먼저 실행하세요.", severity="warning")

    def action_clear_chat(self) -> None:
        chat_log = self.query_one("#chat-log", VerticalScroll)
        chat_log.remove_children()
        self.notify("Chat cleared")

    def action_show_visual_report(self) -> None:
        from backend.orchestrator.screens.visual_analysis_screen import VisualAnalysisScreen
        # VisualAnalysisScreen requires analysis data; show placeholder if none available
        if hasattr(self, '_last_analysis_data') and self._last_analysis_data:
            self.push_screen(VisualAnalysisScreen(data=self._last_analysis_data))
        else:
            self.notify("분석 데이터가 없습니다. 먼저 /analyze 명령어를 실행하세요.", severity="warning")

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

    async def _handle_analyze_command(self, intent: str):
        """Handle the /analyze command or analysis requests from Explorer."""
        chat_log = self.query_one("#chat-log", VerticalScroll)
        
        # Create a new ResultBlock in the chat log for the analysis
        block = ResultBlock()
        block.query = f"[Analysis Intent] {intent}"
        chat_log.mount(block)
        chat_log.scroll_end(animate=False)
        
        # Process the query using the standard ReAct flow
        await self.process_query(intent, block)

    def _sync_connection(self, conn_id: str) -> None:
        """Orchestrator CM → Agent CM 연결 동기화"""
        try:
            orch_conn = self.conn_mgr.get_connection(conn_id)
            if orch_conn:
                conn_type = orch_conn.get("type", "sqlite")
                conn_config = orch_conn.get("config", {})
                self.agent_conn_mgr.register_connection(
                    conn_id=conn_id,
                    conn_type=conn_type,
                    config=conn_config.copy(),
                    name=orch_conn.get("name", conn_id),
                    category=orch_conn.get("category", "DB")
                )
                logger.info(f"연결 동기화 완료: '{conn_id}' ({conn_type})")
            else:
                logger.warning(f"Orchestrator CM에 '{conn_id}' 연결을 찾을 수 없습니다.")
        except Exception as e:
            logger.error(f"연결 동기화 실패: {e}", exc_info=True)
            self.notify(f"연결 동기화 실패: {str(e)}", severity="warning")

    async def _run_explore(self, query: Optional[str] = None, mode: Optional[str] = None, provider: Optional[str] = None):
        """인라인 스키마 사이드바를 토글합니다 (화면 전환 없음)."""
        conn_id = context_manager.active_conn_id

        # 활성화된 연결이 없으면 첫 번째 사용 가능한 연결 사용
        if not conn_id:
            try:
                available_conns = self.conn_mgr.list_connections()
                if available_conns:
                    conn_id = available_conns[0]["id"]
                    logger.info(f"활성화된 연결 없음, 첫 번째 사용 가능: {conn_id}")
                else:
                    self.notify("사용 가능한 연결이 없습니다. /connect 를 먼저 실행하세요.", severity="error")
                    return
            except Exception as e:
                logger.error(f"연결 목록 가져오기 실패: {e}")
                self.notify("연결 목록을 확인할 수 없습니다.", severity="error")
                return

        # Orchestrator CM → Agent CM 동기화
        self._sync_connection(conn_id)

        # 인라인 사이드바 표시
        sidebar = self.query_one("#schema-sidebar", SchemaExplorerSidebar)
        sidebar.show_for_connection(conn_id)
        self._active_conn_id = conn_id
        context_manager.active_conn_id = conn_id

    def action_switch_project(self):
        self.push_screen(ProjectScreen())

def run_app():
    """BI-Agent Console을 실행하는 엔트리 포인트."""
    app = BI_AgentConsole()
    app.run()

if __name__ == "__main__":
    run_app()
