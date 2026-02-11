import asyncio
import logging
from typing import List, Dict, Any, Optional

from textual.app import App
from textual.containers import VerticalScroll
from textual.widgets import Label

from backend.orchestrator.handlers.protocols import HandlerContext, CommandHandlerProtocol
from backend.orchestrator import MessageBubble
from backend.orchestrator.screens import DatabaseExplorerScreen

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
            # Handle subcommands: /connect, /connect load <file>, /connect list
            if len(parts) == 1:
                # Open connection flow (inline question flow)
                from backend.orchestrator.services.flows import build_connection_flow

                conn_flow = build_connection_flow(self.app.conn_mgr, self.app)
                self.app.flow_engine.start_flow(conn_flow)
            elif parts[1] == "load" and len(parts) >= 3:
                # Load connections from file
                filepath = " ".join(parts[2:])
                await self._load_connections_from_file(filepath, chat_log)
            elif parts[1] == "list":
                # List registered connections
                await self._list_connections(chat_log)
            
        elif cmd == "/project":
            if hasattr(self.app, "action_switch_project"):
                self.app.action_switch_project()
                
        elif cmd == "/login":
            from backend.orchestrator.services.flows import build_auth_flow
            from backend.orchestrator import auth_manager, context_manager

            auth_flow = build_auth_flow(auth_manager, context_manager)
            self.app.flow_engine.start_flow(auth_flow)
            
        elif cmd.startswith("/explore"):
            # Parse /explore[:mode[:provider]]
            # Examples:
            #   /explore              -> default mode from config
            #   /explore:local        -> force local mode
            #   /explore:api          -> force API mode with default provider
            #   /explore:api:gemini   -> force API mode with Gemini
            #   /explore:api:claude   -> force API mode with Claude
            #   /explore:api:openai   -> force API mode with OpenAI

            mode = None
            provider = None
            query = None

            # Split command and parse mode/provider
            cmd_parts = cmd.split(":")
            if len(cmd_parts) == 1:
                # /explore -> use defaults
                mode = None
                provider = None
            elif len(cmd_parts) == 2:
                # /explore:local or /explore:api
                mode = cmd_parts[1]
            elif len(cmd_parts) == 3:
                # /explore:api:gemini
                mode = cmd_parts[1]
                provider = cmd_parts[2]

            # Extract query from remaining parts (after command)
            args = parts[1:]
            query = " ".join(args) if args else None

            msg = MessageBubble(role="system", content="[dim]데이터 구조를 탐색 중입니다...[/dim]")
            chat_log.mount(msg)
            chat_log.scroll_end(animate=False)
            if hasattr(self.app, "_run_explore"):
                self.app.run_worker(self.app._run_explore(query, mode=mode, provider=provider))
                
        elif cmd == "/errors":
            if hasattr(self.app, "show_error_viewer"):
                self.app.show_error_viewer()
                
        elif cmd == "/help":
            help_content = (
                "[bold cyan]◈ BI-Agent 사용 가이드 ◈[/bold cyan]\n\n"
                "[bold #38bdf8]명령어 일람:[/bold #38bdf8]\n"
                "• [b]/login[/b]   - LLM API 키 설정 (AI 활성화 핵심)\n"
                "• [b]/connect[/b] - DB/File 연결 UI 열기\n"
                "• [b]/connect load <file>[/b] - YAML/JSON 파일에서 연결 로드\n"
                "• [b]/connect list[/b] - 등록된 연결 목록 보기\n"
                "• [b]/explore[/b] - 테이블 목록 및 상세 스키마 탐색\n"
                "  • [b]/explore:local[/b] - 로컬 AI 모드 (빠름, 무료)\n"
                "  • [b]/explore:api[/b] - Cloud API 모드 (정확, 유료)\n"
                "  • [b]/explore:api:gemini[/b] - Gemini 사용\n"
                "  • [b]/explore:api:claude[/b] - Claude 사용\n"
                "  • [b]/explore:api:openai[/b] - OpenAI 사용\n"
                "• [b]/analyze[/b] - 자연어 질문 기반 데이터 분석 및 시각화\n"
                "• [b]/errors[/b]  - 시스템 장애 및 로직 에러 로그 확인\n"
                "• [b]/quit[/b] 또는 [b]/exit[/b] - 앱 종료\n\n"
                "[bold #38bdf8]단축키 가이드:[/bold #38bdf8]\n"
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

    async def _load_connections_from_file(self, filepath: str, chat_log: VerticalScroll) -> None:
        """Load connections from YAML/JSON file."""
        try:
            from backend.agents.data_source.connection_file_loader import ConnectionFileLoader

            msg = MessageBubble(role="system", content=f"[dim]Loading connections from {filepath}...[/dim]")
            chat_log.mount(msg)
            chat_log.scroll_end(animate=False)

            # Load and normalize connections
            loader = ConnectionFileLoader()
            connections = loader.load_from_file(filepath)

            # Register each connection using orchestrator's ConnectionManager
            success_count = 0
            failed = []

            for conn_id, conn_data in connections.items():
                try:
                    conn_type = conn_data.pop("type")
                    # conn_data now contains: {host, port, database, dbname, user, password} or {path}
                    self.app.conn_mgr.register_connection(conn_id, conn_type, conn_data)
                    success_count += 1
                except Exception as e:
                    failed.append(f"{conn_id}: {str(e)}")
                    logger.error(f"Failed to register {conn_id}: {e}")

            # Report results
            if success_count > 0:
                success_msg = MessageBubble(
                    role="system",
                    content=f"[green]✓ Successfully loaded {success_count} connection(s)[/green]"
                )
                chat_log.mount(success_msg)

            if failed:
                error_msg = MessageBubble(
                    role="system",
                    content=f"[red]✗ Failed to load {len(failed)} connection(s):\n{chr(10).join(failed)}[/red]"
                )
                chat_log.mount(error_msg)

        except FileNotFoundError as e:
            msg = MessageBubble(role="system", content=f"[red]File not found: {filepath}[/red]")
            chat_log.mount(msg)
        except ImportError as e:
            msg = MessageBubble(role="system", content=f"[red]{str(e)}[/red]")
            chat_log.mount(msg)
        except Exception as e:
            logger.error(f"Failed to load connections: {e}")
            msg = MessageBubble(role="system", content=f"[red]Error loading connections: {e}[/red]")
            chat_log.mount(msg)

        chat_log.scroll_end(animate=False)

    async def _list_connections(self, chat_log: VerticalScroll) -> None:
        """List all registered connections."""
        try:
            import json
            storage_path = getattr(self.app.conn_mgr, 'storage_path', None) or getattr(self.app.conn_mgr, 'registry_path', None)

            if not storage_path:
                msg = MessageBubble(role="system", content="[red]Could not find connection storage[/red]")
                chat_log.mount(msg)
                return

            with open(storage_path, 'r', encoding='utf-8') as f:
                registry = json.load(f)

            if not registry:
                msg = MessageBubble(role="system", content="[yellow]No connections registered yet[/yellow]")
                chat_log.mount(msg)
                return

            content = "[bold cyan]Registered Connections:[/bold cyan]\n\n"
            for conn_id, info in registry.items():
                conn_type = info.get('type', 'unknown').upper()
                config = info.get('config', {})
                host = config.get('host', config.get('path', 'N/A'))
                content += f"• [bold]{conn_type}[/bold]: {conn_id} ({host})\n"

            msg = MessageBubble(role="system", content=content)
            chat_log.mount(msg)

        except Exception as e:
            logger.error(f"Failed to list connections: {e}")
            msg = MessageBubble(role="system", content=f"[red]Error: {e}[/red]")
            chat_log.mount(msg)

        chat_log.scroll_end(animate=False)
