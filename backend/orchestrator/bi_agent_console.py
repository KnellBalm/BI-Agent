import sys
import traceback

def show_cli_help():
    print("◈ BI-Agent CLI Help ◈")
    print("Usage: bi-agent [options]")
    print("\nCommands (within TUI):")
    print("  /login    - Setup LLM API Keys")
    print("  /connect  - Connect to Data Source")
    print("  /explore  - Explore Data Schema")
    print("  /analyze  - Natural Language Analysis")
    print("  /quit     - Exit Application")

if "--help" in sys.argv or "-h" in sys.argv:
    show_cli_help()
    sys.exit(0)

# 전역 예외 처리기 설정 (bi-agent-debug.log 기록용)
def global_exception_handler(exctype, value, tb):
    """모든 미처리 예외를 통합 디버그 로그에 기록합니다."""
    import logging
    logger = logging.getLogger("bi_agent")
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    logger.critical(f"Unhandled Exception:\n{error_msg}")
    sys.__excepthook__(exctype, value, tb)

sys.excepthook = global_exception_handler

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

from backend.orchestrator.managers.auth_manager import auth_manager
from backend.orchestrator.managers.quota_manager import quota_manager
from backend.orchestrator.managers.context_manager import context_manager
from backend.orchestrator.managers.command_history import CommandHistory
from backend.orchestrator.ui.components.hud_statusline import HUDStatusLine
from backend.orchestrator.ui.components.error_viewer_screen import ErrorViewerScreen
from backend.orchestrator.ui.components.message_components import (
    MessageBubble,
    ThinkingPanel,
    StreamingMessageView,
    ToolActivityTracker
)
from backend.utils.logger_setup import setup_logger
from backend.utils.path_config import path_manager

# 리팩토링된 모듈들 임포트
# Screens will be lazy-loaded in methods
from backend.orchestrator.ui.components.error_viewer_screen import ErrorViewerScreen
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
    
    CSS_PATH = "bi_agent_console.tcss"
    
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
        
        # 컴포넌트 및 핸들러 초기화 (지연 초기화 권장)
        self._conn_mgr = None
        self._orchestrator = None
        
        self.sidebar_manager = SidebarManager(self)
        self.command_palette = CommandPalette(self)
        self.command_handler = CommandHandler(self)
        self.input_handler = InputHandler(self, self.command_palette, self.command_history)
        
        # 상태값
        self.palette_visible = False 
        self.current_project = "default"
        
        # Legacy 지원용 COMMAND_LIST (CommandPalette와 동기화 필요)
        self.COMMAND_LIST = self.command_palette.commands

    def compose(self) -> ComposeResult:
        """UI 레이아웃 구성 (고정형 프레임 구조)"""
        yield HUDStatusLine(id="hud-status")
        
        with Horizontal(id="main-layout"):
            # Main Chat Area
            with Vertical(id="chat-area"):
                # 입구 배너 (상단 고정)
                yield Static(
                    "   ⚡ [indigo][bold underline]BI-AGENT SYSTEM[/bold underline][/indigo] v2.3\n"
                    "   [dim]Intelligent Data Analysis Framework[/dim]\n"
                    "   [dim]-------------------------------------------[/dim]",
                    id="entry-banner"
                )
                
                # 대화 기록 영역 (독립 스크롤)
                yield VerticalScroll(id="chat-log")
                
                # Command Palette (Overlay)
                yield OptionList(id="command-menu")
                
                # 입력 영역 (하단 고정)
                with Horizontal(id="input-container"):
                    yield Input(placeholder="질문을 입력하거나 '/'로 명령어를 시작하세요...", id="user-input")
                    yield Button("RUN", id="send-btn", variant="primary")
            
            # 사이드바 영역
            with Vertical(id="sidebar"):
                yield from self.sidebar_manager.compose()

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
                # cmd_ 접두사 제거 및 실제 명령어 매핑
                cmd = "/" + option_id.replace("cmd_", "")
                
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
        """분석 에이전트를 통한 쿼리 처리 (Non-blocking Worker)"""
        chat_log = self.query_one("#chat-log", VerticalScroll)
        user_input = self.query_one("#user-input", Input)
        banner = self.query_one("#entry-banner", Static)
        
        # UI 초기 상태 설정
        user_input.disabled = True
        user_input.placeholder = "에이전트가 분석 중입니다..."
        banner.update("   ⚡ [indigo][bold underline]BI-AGENT SYSTEM[/bold underline][/indigo] [yellow]● ANALYZING...[/yellow]\n"
                      "   [dim]Intelligent Data Analysis Framework[/dim]")
        
        from backend.orchestrator.ui.components.message_components import ThinkingBubble
        thinking = ThinkingBubble()
        chat_log.mount(thinking)
        chat_log.scroll_end()
        
        async def run_analysis():
            try:
                # 워커 내에서 실제 처리 수행
                result = await self.orchestrator.run(query)
                
                # UI 업데이트 (Main thread)
                self.call_from_thread(self._handle_analysis_result, result, thinking)
            except Exception as e:
                logger.error(f"Analysis worker failed: {e}")
                self.call_from_thread(self._handle_analysis_error, e, thinking)
            finally:
                # 입력창 및 배너 복구
                self.call_from_thread(self._restore_ui_state)

        # Worker 실행
        self.run_worker(run_analysis(), thread=True)

    async def _simulate_typewriter(self, response: str):
        """AI 응답을 타자기처럼 한 글자씩 출력 (Premium UX)"""
        chat_log = self.query_one("#chat-log", VerticalScroll)
        from backend.orchestrator.ui.components.message_components import StreamingMessageView
        
        stream_view = StreamingMessageView()
        chat_log.mount(stream_view)
        chat_log.scroll_end()
        
        # 문장 단위 또는 단어 단위로 쪼개서 출력
        tokens = response.split(" ")
        temp_content = ""
        
        for i, token in enumerate(tokens):
            temp_content += (token + " ")
            stream_view.content = temp_content
            # 적절한 속도로 지연 (너무 빠르지도 느리지도 않게)
            await asyncio.sleep(0.04)
            chat_log.scroll_end()
            
        # 스트리밍 완료 후 영구적인 Markdown 버블로 교체
        stream_view.remove()
        chat_log.mount(MessageBubble(role="agent", content=response))
        chat_log.scroll_end()

    def _handle_analysis_result(self, result, thinking):
        """결과 처리 및 UI 메시지 추가"""
        chat_log = self.query_one("#chat-log", VerticalScroll)
        if thinking.is_mounted:
            thinking.remove()
            
        if result.get("status") == "error":
            chat_log.mount(MessageBubble(role="system", content=f"[red]Error: {result.get('message')}[/red]"))
        else:
            response = result.get("final_response", result.get("summary", {}).get("table", "분석 완료"))
            # 타자기 효과 시작
            asyncio.create_task(self._simulate_typewriter(response))
            
            if result.get("tui_data"):
                chat_log.mount(MessageBubble(role="system", content="[green]📊 분석 결과에 따른 시각화 리포트가 생성되었습니다. 'v' 키를 눌러 확인하세요.[/green]"))
        
        chat_log.scroll_end()

    def _handle_analysis_error(self, e, thinking):
        """에러 처리"""
        chat_log = self.query_one("#chat-log", VerticalScroll)
        if thinking.is_mounted:
            thinking.remove()
        chat_log.mount(MessageBubble(role="system", content=f"[red]분석 중 오류 발생: {str(e)}[/red]"))
        chat_log.scroll_end()

    def _restore_ui_state(self):
        """UI 상태 원복"""
        user_input = self.query_one("#user-input", Input)
        banner = self.query_one("#entry-banner", Static)
        
        user_input.disabled = False
        user_input.placeholder = "질문을 입력하거나 '/'로 명령어를 시작하세요..."
        user_input.focus()
        
        banner.update("   ⚡ [indigo][bold underline]BI-AGENT SYSTEM[/bold underline][/indigo] v2.3\n"
                      "   [dim]Intelligent Data Analysis Framework[/dim]\n"
                      "   [dim]-------------------------------------------[/dim]")

    # --- 액션 핸들러 (Bindings) ---

    async def action_quit(self) -> None:
        """애플리케이션 종료"""
        self.exit()

    def action_show_help(self) -> None:
        asyncio.create_task(self.handle_command("/help"))

    def action_show_errors(self) -> None:
        self.push_screen(ErrorViewerScreen())

    def show_error_viewer(self) -> None:
        """Alias for action_show_errors to satisfy handlers."""
        self.action_show_errors()

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

    async def _update_sidebar(self):
        """Manual sidebar update trigger."""
        await self.sidebar_manager.update()

    # --- 백그라운드 워커 메서드 (CommandHandler 등에서 대리 호출용) ---

    async def _run_scan(self, conn_id: str):
        """Perform scan after connection and update sidebar."""
        chat_log = self.query_one("#chat-log", VerticalScroll)
        try:
            self.notify(f"Scanning data source '{conn_id}'...")
            chat_log.mount(MessageBubble(role="system", content=f"[bold blue]Scanning data source '{conn_id}'...[/bold blue]"))
            chat_log.scroll_end()
            
            # Thinking Indicator 추가
            from backend.orchestrator.ui.components.message_components import ThinkingBubble
            thinking = ThinkingBubble()
            chat_log.mount(thinking)
            chat_log.scroll_end()
            
            from backend.agents.data_source.metadata_scanner import MetadataScanner
            scanner = MetadataScanner(self.conn_mgr)
            
            # Run scan in executor
            meta = await asyncio.get_event_loop().run_in_executor(None, scanner.scan_source, conn_id)
            
            thinking.remove()
            table_count = len(meta.get("tables", []))
            summary = f"[green]✅ '{conn_id}' 연결 및 스캔 완료![/green]\n📊 발견된 테이블 수: {table_count}\n[dim]Tip: '/explore {conn_id}' 을 입력하여 목록을 확인하세요.[/dim]"
            
            chat_log.mount(MessageBubble(role="system", content=summary))
            self.notify(f"Scan complete: {table_count} tables found")
            
            # Journey Progress: Update to Connect step
            context_manager.update_journey_step(2) # Connect
            await self.sidebar_manager.update()
            
        except Exception as e:
            logger.error(f"Scan failed for {conn_id}: {e}")
            error_msg = f"[bold red]Scan Error:[/bold red] {e}"
            chat_log.mount(MessageBubble(role="system", content=error_msg))
            self.notify(f"Scan failed: {str(e)}", severity="error")
        
        chat_log.scroll_end()

    async def _run_explore(self, query: Optional[str]):
        """Explore metadata via TableSelectionScreen."""
        from backend.orchestrator.screens.table_selection_screen import TableSelectionScreen
        
        def on_table_selected(table_name: str):
            if table_name:
                self.notify(f"Selected table: {table_name}")
                # Metadata 스캔하여 context에 상세 정보 저장 (Thinking indicator included)
                asyncio.create_task(self._pin_table_context(table_name))

        # 팝업 호출 전 Thinking 노출 (준비 중임을 알림)
        self.push_screen(TableSelectionScreen(initial_query=query, callback=on_table_selected))

    async def _pin_table_context(self, table_fqn: str):
        """테이블 선택 시 상세 기베 정보를 로드하여 컨텍스트에 고정"""
        chat_log = self.query_one("#chat-log", VerticalScroll)
        from backend.orchestrator.ui.components.message_components import ThinkingBubble
        thinking = ThinkingBubble()
        chat_log.mount(thinking)
        chat_log.scroll_end()
        
        try:
            conn_id = context_manager.active_conn_id
            table_name = table_fqn
            if "." in table_fqn:
                conn_id, table_name = table_fqn.split(".", 1)
            
            from backend.agents.data_source.metadata_scanner import MetadataScanner
            scanner = MetadataScanner(self.conn_mgr)
            meta = await asyncio.get_event_loop().run_in_executor(None, scanner.scan_table, conn_id, table_name)
            
            context_manager.set_active_table(conn_id, table_name, meta)
            chat_log.mount(MessageBubble(role="system", content=f"[green]✓ Table context pinned: {table_fqn}[/green]"))
        except Exception as e:
            logger.error(f"Pin table context failed: {e}")
            chat_log.mount(MessageBubble(role="system", content=f"[red]Failed to pin context: {str(e)}[/red]"))
        finally:
            thinking.remove()
            chat_log.scroll_end()
            await self.sidebar_manager.update()
            context_manager.update_journey_step(3) # Explore
            await self.sidebar_manager.update()
            
            chat_log = self.query_one("#chat-log", VerticalScroll)
            chat_log.mount(MessageBubble(role="system", content=f"[green]📌 Table '{table_name}' pinned for analysis.[/green]"))
            chat_log.scroll_end()

    def action_switch_project(self):
        from backend.orchestrator.screens.project_screen import ProjectScreen
        self.push_screen(ProjectScreen())

    @property
    def conn_mgr(self):
        """Lazy ConnectionManager initialization."""
        if self._conn_mgr is None:
            from backend.agents.data_source.connection_manager import ConnectionManager
            self._conn_mgr = ConnectionManager()
        return self._conn_mgr

    @property
    def orchestrator(self):
        """Lazy Orchestrator initialization."""
        if self._orchestrator is None:
            from backend.orchestrator.orchestrators.collaborative_orchestrator import CollaborativeOrchestrator
            self._orchestrator = CollaborativeOrchestrator()
        return self._orchestrator

    async def _handle_analyze_command(self, query: str):
        """/analyze 명령어 처리 (main 브랜치 로직 복구)"""
        from backend.orchestrator.screens.visual_analysis_screen import VisualAnalysisScreen
        chat_log = self.query_one("#chat-log", VerticalScroll)
        
        if not context_manager.active_table:
            chat_log.mount(MessageBubble(role="system", content="[yellow]⚠️ 먼저 분석할 테이블을 선택(/explore)해 주세요.[/yellow]"))
            return

        chat_log.mount(MessageBubble(role="system", content=f"🚀 '{context_manager.active_table}' 테이블 기반 분석을 시작합니다..."))
        chat_log.scroll_end()
        
        try:
            # 1. Intent Analysis & Plan
            plan_data = await self.orchestrator.handle_intent(query, context_manager.active_conn_id)
            
            if plan_data.get("status") == "error":
                chat_log.mount(MessageBubble(role="system", content=f"[red]분석 실패: {plan_data.get('message')}[/red]"))
                return
                
            # Plan 출력
            plan_msg = f"[bold cyan]Analysis Plan:[/bold cyan]\n"
            for i, step in enumerate(plan_data.get("steps", [])):
                plan_msg += f"{i+1}. {step}\n"
            plan_msg += f"\n[dim]Value: {plan_data.get('estimated_value', '')}[/dim]"
            chat_log.mount(MessageBubble(role="agent", content=plan_msg))
            chat_log.scroll_end()

            # 2. Complete Analysis
            result = await self.orchestrator.handle_complex_request(query, context_manager.active_conn_id)
            
            if result.get("status") == "error":
                chat_log.mount(MessageBubble(role="system", content=f"[red]분석 중 오류 발생: {result.get('message')}[/red]"))
                return

            chat_log.mount(MessageBubble(role="agent", content=f"✅ 분석 완료! 시각화 리포트를 생성했습니다.\n[dim]결과 파일: {result.get('output_file')}[/dim]"))
            
            # 3. Show Visuals
            tui_data = result.get("tui_data", {"metrics": [], "charts": []})
            self.push_screen(VisualAnalysisScreen(tui_data, title=f"Analysis: {context_manager.active_table}"))
            
            # 4. Success message in Chat
            chat_log.mount(MessageBubble(role="system", content="[green]💡 'v' 키를 누르면 언제든지 시각화 리포트를 다시 볼 수 있습니다.[/green]"))
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            chat_log.mount(MessageBubble(role="system", content=f"[red]분석 중 예외 발생: {str(e)}[/red]"))
        
        chat_log.scroll_end()

def run_app():
    """BI-Agent Console을 실행하는 엔트리 포인트."""
    try:
        app = BI_AgentConsole()
        app.run()
    except Exception:
        logger.exception("FATAL: BI-Agent TUI crashed or encountered an unhandled exception")
        raise

if __name__ == "__main__":
    run_app()
