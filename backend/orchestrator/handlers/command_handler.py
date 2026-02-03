import asyncio
import logging
from typing import List, Dict, Any, Optional

from textual.app import App
from textual.containers import VerticalScroll
from textual.widgets import Label

from backend.orchestrator.handlers.protocols import HandlerContext, CommandHandlerProtocol
from backend.orchestrator.ui.components.message_components import MessageBubble

logger = logging.getLogger("tui")

class CommandHandler(CommandHandlerProtocol):
    """
    슬래시 명령어 라우팅 및 처리를 담당하는 핸들러 (Mediator 패턴)
    """
    def __init__(self, context: HandlerContext):
        self.context = context
        self.app = context.app

    async def handle(self, cmd_text: str) -> None:
        """Routing for slash commands."""
        parts = cmd_text.split()
        if not parts:
            return
            
        cmd = parts[0]
        chat_log = self.context.query_one("#chat-log", VerticalScroll)
        
        if cmd == "/intent" or cmd == "/analyze":
            user_intent = " ".join(parts[1:]) if len(parts) > 1 else ""
            if not user_intent:
                msg = MessageBubble(role="system", content="[yellow]분석 의도를 입력해주세요. 예: /analyze 이번 달 매출 하락 원인 분석[/yellow]")
                chat_log.mount(msg)
            else:
                # App의 메서드를 비동기로 실행
                if hasattr(self.app, "_handle_analyze_command"):
                    asyncio.create_task(self.app._handle_analyze_command(user_intent))
                
        elif cmd == "/connect":
            def on_connected(conn_id: str):
                if conn_id and hasattr(self.app, "_run_scan"):
                    # 비동기 워커로 스캔 실행 (UI 프리징 방지)
                    self.app.run_worker(self.app._run_scan(conn_id))
            
            from backend.orchestrator.screens.connection_screen import ConnectionScreen
            self.context.push_screen(ConnectionScreen(callback=on_connected))
            
        elif cmd == "/project":
            if hasattr(self.app, "action_switch_project"):
                self.app.action_switch_project()
                
        elif cmd == "/login":
            from backend.orchestrator.screens.auth_screen import AuthScreen
            self.context.push_screen(AuthScreen())
            
        elif cmd == "/explore":
            args = parts[1:]
            query = args[0] if args else None
            msg = MessageBubble(role="system", content="[dim]데이터 구조를 탐색 중입니다...[/dim]")
            chat_log.mount(msg)
            chat_log.scroll_end(animate=False)
            if hasattr(self.app, "_run_explore"):
                self.app.run_worker(self.app._run_explore(query))
                
        elif cmd == "/errors":
            if hasattr(self.app, "show_error_viewer"):
                self.app.show_error_viewer()
                
        elif cmd == "/help":
            help_content = (
                "[bold indigo]◈ BI-Agent 사용 가이드 ◈[/bold indigo]\n\n"
                "[bold indigo]명령어 일람:[/bold indigo]\n"
                "• [b]/login[/b]   - LLM API 키 설정 (AI 활성화 핵심)\n"
                "• [b]/connect[/b] - DB/File 연결 (sqlite, postgres, excel)\n"
                "• [b]/explore[/b] - 테이블 목록 및 상세 스키마 탐색\n"
                "• [b]/analyze[/b] - 자연어 질문 기반 데이터 분석 및 시각화\n"
                "• [b]/errors[/b]  - 시스템 장애 및 로직 에러 로그 확인\n"
                "• [b]/quit[/b] 또는 [b]/exit[/b] - 앱 종료\n\n"
                "[bold indigo]단축키 가이드:[/bold indigo]\n"
                "• [b]/[/b] : 명령어 입력 시작 (입력창 포커스 + / 자동입력) ⭐\n"
                "• [b]q[/b] : 앱 종료\n"
                "• [b]v[/b] : 분석 시각화 리포트/차트 보기\n"
                "• [b]F1[/b] : 도움말 보기\n"
                "• [b]ctrl+l[/b] : 채팅 내용 삭제\n"
                "• [b]tab[/b] : 명령어 자동 완성 및 입력 보조\n"
                "• [b]ctrl+e[/b] : 에러 로그 창 열기\n\n"
                "[dim]Tip: 오른쪽 사이드바의 'ACTION RECOMMENDATION'에서 항상 다음 단계를 확인하세요![/dim]"
            )
            msg = MessageBubble(role="system", content=help_content)
            chat_log.mount(msg)
            
        elif cmd in ["/quit", "/exit"]:
            if hasattr(self.app, "action_quit"):
                await self.app.action_quit()
        else:
            msg = MessageBubble(role="system", content=f"[red]알 수 없는 명령어입니다: {cmd}[/red]")
            chat_log.mount(msg)
        
        chat_log.scroll_end(animate=False)

    def can_handle(self, cmd: str) -> bool:
        return cmd.startswith("/")
