import asyncio
import logging
from typing import List, Dict, Any, Optional

from backend.orchestrator.handlers.protocols import HandlerContext, CommandHandlerProtocol

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
                    
        elif cmd == "/init":
            import os
            from backend.aac.plan_parser import PlanParser
            template = PlanParser().generate_template()
            plan_path = "plan.md"
            if os.path.exists(plan_path):
                msg = MessageBubble(role="system", content=f"[yellow]⚠ {plan_path}가 이미 존재합니다.[/yellow]")
            else:
                with open(plan_path, "w", encoding="utf-8") as f:
                    f.write(template)
                msg = MessageBubble(role="system", content=f"[green]✓ {plan_path} 템플릿이 생성되었습니다.[/green] [dim](경로: {os.getcwd()})[/dim]\n[dim]/edit 로 편집하거나 /build 로 분석을 시작하세요.[/dim]")
            chat_log.mount(msg)
            chat_log.scroll_end(animate=False)

        elif cmd == "/edit":
            target = parts[1] if len(parts) > 1 else "plan"
            if target == "plan":
                plan_path = "plan.md"
                import os
                if not os.path.exists(plan_path):
                    msg = MessageBubble(role="system", content="[red]✗ plan.md 파일이 없습니다. /init 으로 먼저 생성하세요.[/red]")
                    chat_log.mount(msg)
                else:
                    # Textual 모달 에디터 띄우기 (suspend 이용)
                    async def run_editor():
                        with self.app.suspend():
                            from backend.aac.interactive_editor import MarkdownEditorApp
                            editor = MarkdownEditorApp(plan_path)
                            saved = await editor.run_async()
                        
                        # 앱이 다시 재개된(Resume) 이후 화면 렌더링
                        if saved:
                            msg = MessageBubble(role="system", content=f"[green]✓ {plan_path} 덮어쓰기 완료[/green]")
                        else:
                            msg = MessageBubble(role="system", content=f"[dim]✓ {plan_path} 수정 취소됨[/dim]")
                        
                        chat_log.mount(msg)
                        chat_log.scroll_end(animate=False)
                        
                    asyncio.create_task(run_editor())
            else:
                msg = MessageBubble(role="system", content=f"[dim]지원하지 않는 대상입니다: {target}[/dim]")
                chat_log.mount(msg)
            chat_log.scroll_end(animate=False)

        elif cmd == "/build":
            plan_path = "plan.md"
            import os
            if not os.path.exists(plan_path):
                msg = MessageBubble(role="system", content="[red]✗ plan.md 파일이 없습니다. /init 으로 먼저 생성하세요.[/red]")
                chat_log.mount(msg)
                chat_log.scroll_end(animate=False)
            else:
                async def run_build():
                    try:
                        from backend.aac.plan_parser import PlanParser
                        from backend.aac.aac_orchestrator import AaCOrchestrator
                        
                        parser = PlanParser()
                        intent = parser.parse_file(plan_path)
                        start_msg = MessageBubble(role="system", content=f"[cyan]▶ 분석 시작[/cyan]  목표: [bold]{intent.goal or '(목표 미지정)'}[/bold]\n  데이터소스: {intent.data_sources or ['(미지정)']}\n  지표: {intent.metrics or ['(미지정)']}")
                        chat_log.mount(start_msg)
                        chat_log.scroll_end(animate=False)

                        orchestrator_aac = AaCOrchestrator(intent=intent)
                        # 여기서는 임시 저장 공간을 App.conn_mgr 이나 다른 어딘가에 둘 수 있습니다
                        self.app._last_pipeline_results = await orchestrator_aac.run()
                        self.app._last_intent = intent
                        
                        step_labels = {"profile": "데이터 프로파일링", "query": "데이터 조회", "transform": "데이터 가공", "visualize": "시각화", "insight": "인사이트 도출"}
                        
                        result_str = "[green]✓ 파이프라인 완료[/green]\n"
                        for r in self.app._last_pipeline_results:
                            label = step_labels.get(r.step.value, r.step.value)
                            if r.success:
                                result_str += f"[green]✓[/green] {label}\n"
                            else:
                                result_str += f"[red]✗[/red] {label}: {r.error}\n"
                        result_str += "\n[dim]/export html 로 결과물을 내보내세요.[/dim]"
                        
                        end_msg = MessageBubble(role="system", content=result_str)
                        chat_log.mount(end_msg)
                        chat_log.scroll_end(animate=False)
                    except Exception as e:
                        err_msg = MessageBubble(role="system", content=f"[red]✗ 빌드 오류: {e}[/red]")
                        chat_log.mount(err_msg)
                        chat_log.scroll_end(animate=False)
                
                asyncio.create_task(run_build())

        elif cmd == "/export":
            fmt = parts[1] if len(parts) > 1 else "html"
            results = getattr(self.app, "_last_pipeline_results", None)
            intent = getattr(self.app, "_last_intent", None)
            
            if not results or not intent:
                msg = MessageBubble(role="system", content="[red]✗ 내보낼 분석 결과가 없습니다. 먼저 /build 를 실행하세요.[/red]")
                chat_log.mount(msg)
            else:
                try:
                    from backend.utils.output_packager import OutputPackager
                    result_name = intent.goal if intent.goal else "aac_analysis_result"
                    
                    analysis_data = {
                        "goal": intent.goal,
                        "metrics": intent.metrics,
                        "summary": {}
                    }
                    for r in results:
                        if r.success and r.step.value in ["insight", "visualize"]:
                            analysis_data["summary"][r.step.value] = r.output

                    packager = OutputPackager("default")
                    exported = packager.create_full_package(
                        result_name=result_name,
                        analysis_result=analysis_data,
                        export_formats=[fmt]
                    )
                    
                    out_str = "[green]✓ 성공적으로 패키징 되었습니다:[/green]\n"
                    for format_type, path in exported.items():
                        out_str += f"  - [cyan]{format_type}[/cyan]: {path}\n"
                    msg = MessageBubble(role="system", content=out_str)
                    chat_log.mount(msg)
                except Exception as e:
                    msg = MessageBubble(role="system", content=f"[red]✗ 내보내기 오류: {e}[/red]")
                    chat_log.mount(msg)
            chat_log.scroll_end(animate=False)

        elif cmd == "/connect":
            # Handle subcommands: /connect, /connect load <file>, /connect list
            if len(parts) == 1:
                # Open interactive connection selector inline
                from backend.orchestrator.ui.components.interactive_connection_selector import InteractiveConnectionSelector
                
                async def _on_connection_selected(conn_id: str):
                    # 활성 연결 설정 및 인라인 사이드바 표시
                    from backend.orchestrator import context_manager
                    context_manager.active_conn_id = conn_id
                    self.app._active_conn_id = conn_id
                    self.app.notify(f"'{conn_id}' 에 연결되었습니다. 스키마를 로딩합니다...", severity="information")
                    # 인라인 사이드바 자동 표시
                    if hasattr(self.app, "_run_explore"):
                        self.app.run_worker(self.app._run_explore(query=None))

                selector = InteractiveConnectionSelector(
                    conn_mgr=self.app.conn_mgr, 
                    on_connect=_on_connection_selected
                )
                await chat_log.mount(selector)
                selector.scroll_visible()
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

            msg = MessageBubble(role="system", content="[dim]스키마 탐색기를 여는 중...[/dim]")
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
                "[bold #38bdf8]AaC (Analysis as Code) 기능:[/bold #38bdf8]\n"
                "• [b]/init[/b]   - 현재 디렉토리에 plan.md 템플릿 생성\n"
                "• [b]/edit[/b]   - plan.md 마크다운 에디터 열기 (TUI 모달)\n"
                "• [b]/build[/b]  - plan.md 분석 파이프라인 실행\n"
                "• [b]/export [fmt][/b] - 결과물 내보내기 (html/pdf)\n\n"
                "[bold #38bdf8]ALIVE 분석 (Analysis as Markdown):[/bold #38bdf8]\n"
                "• [b]/analysis-new <제목>[/b]   - 새 ALIVE 분석 프로젝트 생성\n"
                "• [b]/analysis-quick <제목>[/b] - 퀵 단일파일 분석 생성\n"
                "• [b]/analysis-status[/b]       - 현재 분석 상태 확인\n"
                "• [b]/analysis-list[/b]         - 모든 분석 목록 보기\n"
                "• [b]/analysis-run[/b]          - 현재 스테이지 BI-EXEC 블록 실행\n"
                "• [b]/analysis-next[/b]         - 다음 스테이지로 진행\n"
                "• [b]/analysis-archive[/b]      - 현재 분석 아카이브\n\n"
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

        elif cmd == "/analysis-new":
            title = " ".join(parts[1:]) if len(parts) > 1 else ""
            if not title:
                msg = MessageBubble(role="system", content="[yellow]사용법: /analysis-new <분석 제목>[/yellow]")
                chat_log.mount(msg)
                chat_log.scroll_end(animate=False)
            else:
                async def run_analysis_new(t=title):
                    try:
                        from backend.aac.analysis_manager import AnalysisManager
                        conn_id = getattr(self.app, "_active_conn_id", None)
                        mgr = AnalysisManager()
                        project = mgr.create_analysis(title=t, connection=conn_id or "")
                        msg = MessageBubble(role="system", content=(
                            f"[green]✓ ALIVE 분석 생성됨:[/green] [bold]{project.title}[/bold]\n"
                            f"  ID: [cyan]{project.id}[/cyan]\n"
                            f"  스테이지: [yellow]{project.status.value.upper()}[/yellow]\n"
                            f"  경로: [dim]{project.path}[/dim]\n"
                            f"  [dim]/analysis-run 으로 BI-EXEC 블록을 실행하거나 파일을 편집하세요.[/dim]"
                        ))
                        chat_log.mount(msg)
                        chat_log.scroll_end(animate=False)
                    except Exception as e:
                        msg = MessageBubble(role="system", content=f"[red]✗ 분석 생성 오류: {e}[/red]")
                        chat_log.mount(msg)
                        chat_log.scroll_end(animate=False)
                asyncio.create_task(run_analysis_new())

        elif cmd == "/analysis-quick":
            title = " ".join(parts[1:]) if len(parts) > 1 else ""
            if not title:
                msg = MessageBubble(role="system", content="[yellow]사용법: /analysis-quick <분석 제목>[/yellow]")
                chat_log.mount(msg)
                chat_log.scroll_end(animate=False)
            else:
                async def run_analysis_quick(t=title):
                    try:
                        from backend.aac.analysis_manager import AnalysisManager
                        conn_id = getattr(self.app, "_active_conn_id", None)
                        mgr = AnalysisManager()
                        filepath = mgr.create_quick(question=t, connection=conn_id or "")
                        msg = MessageBubble(role="system", content=(
                            f"[green]✓ 퀵 분석 생성됨:[/green] [bold]{t}[/bold]\n"
                            f"  경로: [dim]{filepath}[/dim]\n"
                            f"  [dim]단일 파일로 ALIVE 전체 구조가 포함되어 있습니다.[/dim]"
                        ))
                        chat_log.mount(msg)
                        chat_log.scroll_end(animate=False)
                    except Exception as e:
                        msg = MessageBubble(role="system", content=f"[red]✗ 퀵 분석 생성 오류: {e}[/red]")
                        chat_log.mount(msg)
                        chat_log.scroll_end(animate=False)
                asyncio.create_task(run_analysis_quick())

        elif cmd == "/analysis-next":
            async def run_analysis_next():
                try:
                    from backend.aac.analysis_manager import AnalysisManager
                    mgr = AnalysisManager()
                    project = mgr.get_active()
                    if not project:
                        msg = MessageBubble(role="system", content="[yellow]활성 분석이 없습니다. /analysis-new 로 먼저 생성하세요.[/yellow]")
                        chat_log.mount(msg)
                        chat_log.scroll_end(animate=False)
                        return
                    prev_stage = project.status.value.upper()
                    mgr.advance_stage(project)
                    project = mgr.get_active()
                    new_stage = project.status.value.upper() if project else "ARCHIVED"
                    msg = MessageBubble(role="system", content=(
                        f"[green]✓ 스테이지 전환 완료:[/green] "
                        f"[yellow]{prev_stage}[/yellow] → [cyan]{new_stage}[/cyan]\n"
                        f"  [dim]새 스테이지 파일이 생성되었습니다. /analysis-run 으로 실행하세요.[/dim]"
                    ))
                    chat_log.mount(msg)
                    chat_log.scroll_end(animate=False)
                except ValueError as e:
                    msg = MessageBubble(role="system", content=f"[yellow]⚠ {e}[/yellow]")
                    chat_log.mount(msg)
                    chat_log.scroll_end(animate=False)
                except Exception as e:
                    msg = MessageBubble(role="system", content=f"[red]✗ 스테이지 전환 오류: {e}[/red]")
                    chat_log.mount(msg)
                    chat_log.scroll_end(animate=False)
            asyncio.create_task(run_analysis_next())

        elif cmd == "/analysis-status":
            async def run_analysis_status():
                try:
                    from backend.aac.analysis_manager import AnalysisManager
                    mgr = AnalysisManager()
                    project = mgr.get_active()
                    if not project:
                        all_analyses = mgr.list_analyses()
                        if not all_analyses:
                            msg = MessageBubble(role="system", content="[yellow]분석 프로젝트가 없습니다. /analysis-new 로 생성하세요.[/yellow]")
                        else:
                            msg = MessageBubble(role="system", content="[yellow]활성 분석이 없습니다. /analysis-list 로 목록을 확인하세요.[/yellow]")
                        chat_log.mount(msg)
                        chat_log.scroll_end(animate=False)
                        return
                    stage_emoji = {"ask": "❶", "look": "❷", "investigate": "❸", "voice": "❹", "evolve": "❺"}
                    emoji = stage_emoji.get(project.status.value, "●")
                    msg = MessageBubble(role="system", content=(
                        f"[bold cyan]◈ 현재 분석 상태 ◈[/bold cyan]\n"
                        f"  제목: [bold]{project.title}[/bold]\n"
                        f"  ID: [cyan]{project.id}[/cyan]\n"
                        f"  스테이지: {emoji} [yellow]{project.status.value.upper()}[/yellow]\n"
                        f"  연결: [dim]{project.connection or '(없음)'}[/dim]\n"
                        f"  생성: [dim]{project.created}[/dim]\n"
                        f"  경로: [dim]{project.path}[/dim]\n\n"
                        f"  [dim]/analysis-run 으로 현재 스테이지 실행 | /analysis-next 로 다음 스테이지 이동[/dim]"
                    ))
                    chat_log.mount(msg)
                    chat_log.scroll_end(animate=False)
                except Exception as e:
                    msg = MessageBubble(role="system", content=f"[red]✗ 상태 조회 오류: {e}[/red]")
                    chat_log.mount(msg)
                    chat_log.scroll_end(animate=False)
            asyncio.create_task(run_analysis_status())

        elif cmd == "/analysis-list":
            async def run_analysis_list():
                try:
                    from backend.aac.analysis_manager import AnalysisManager
                    mgr = AnalysisManager()
                    analyses = mgr.list_analyses()
                    if not analyses:
                        msg = MessageBubble(role="system", content="[yellow]분석 프로젝트가 없습니다. /analysis-new 로 생성하세요.[/yellow]")
                        chat_log.mount(msg)
                        chat_log.scroll_end(animate=False)
                        return
                    active = mgr.get_active()
                    active_id = active.id if active else None
                    content = "[bold cyan]◈ ALIVE 분석 목록 ◈[/bold cyan]\n\n"
                    for p in analyses:
                        marker = "[green]▶[/green] " if p.id == active_id else "  "
                        content += f"{marker}[bold]{p.title}[/bold] [dim]({p.id})[/dim]\n"
                        content += f"     스테이지: [yellow]{p.status.value.upper()}[/yellow]  |  생성: [dim]{p.created[:10]}[/dim]\n"
                    content += f"\n[dim]{len(analyses)}개의 분석 프로젝트[/dim]"
                    msg = MessageBubble(role="system", content=content)
                    chat_log.mount(msg)
                    chat_log.scroll_end(animate=False)
                except Exception as e:
                    msg = MessageBubble(role="system", content=f"[red]✗ 목록 조회 오류: {e}[/red]")
                    chat_log.mount(msg)
                    chat_log.scroll_end(animate=False)
            asyncio.create_task(run_analysis_list())

        elif cmd == "/analysis-archive":
            async def run_analysis_archive():
                try:
                    from backend.aac.analysis_manager import AnalysisManager
                    mgr = AnalysisManager()
                    project = mgr.get_active()
                    if not project:
                        msg = MessageBubble(role="system", content="[yellow]활성 분석이 없습니다.[/yellow]")
                        chat_log.mount(msg)
                        chat_log.scroll_end(animate=False)
                        return
                    title = project.title
                    mgr.archive(project)
                    msg = MessageBubble(role="system", content=f"[green]✓ 분석 아카이브됨:[/green] [bold]{title}[/bold]")
                    chat_log.mount(msg)
                    chat_log.scroll_end(animate=False)
                except Exception as e:
                    msg = MessageBubble(role="system", content=f"[red]✗ 아카이브 오류: {e}[/red]")
                    chat_log.mount(msg)
                    chat_log.scroll_end(animate=False)
            asyncio.create_task(run_analysis_archive())

        elif cmd == "/analysis-run":
            async def run_analysis_run():
                try:
                    from backend.aac.analysis_manager import AnalysisManager
                    from backend.aac.stage_executor import StageExecutor, FileLockedError
                    mgr = AnalysisManager()
                    project = mgr.get_active()
                    if not project:
                        msg = MessageBubble(role="system", content="[yellow]활성 분석이 없습니다. /analysis-new 로 먼저 생성하세요.[/yellow]")
                        chat_log.mount(msg)
                        chat_log.scroll_end(animate=False)
                        return
                    stage_file = project.current_stage_file()
                    if not stage_file.exists():
                        msg = MessageBubble(role="system", content=f"[red]✗ 스테이지 파일 없음: {stage_file}[/red]")
                        chat_log.mount(msg)
                        chat_log.scroll_end(animate=False)
                        return
                    orchestrator = getattr(self.app, "_orchestrator", None)
                    registry = orchestrator.registry if orchestrator else None
                    executor = StageExecutor(registry=registry)
                    count = executor.count_bi_exec_blocks(stage_file)
                    if count == 0:
                        msg = MessageBubble(role="system", content=(
                            f"[yellow]실행할 BI-EXEC 블록이 없습니다.[/yellow]\n"
                            f"  [dim]스테이지: {project.status.value.upper()} | 파일: {stage_file.name}[/dim]"
                        ))
                        chat_log.mount(msg)
                        chat_log.scroll_end(animate=False)
                        return
                    start_msg = MessageBubble(role="system", content=(
                        f"[cyan]▶ BI-EXEC 실행 시작[/cyan]\n"
                        f"  스테이지: [yellow]{project.status.value.upper()}[/yellow]  |  블록 수: [bold]{count}[/bold]"
                    ))
                    chat_log.mount(start_msg)
                    chat_log.scroll_end(animate=False)
                    prior_files = project.completed_stage_files()
                    executor.execute_stage(stage_file, prior_stage_files=prior_files)
                    result_content = (
                        f"[green]✓ BI-EXEC 실행 완료[/green]  블록 수: [bold]{count}[/bold]\n"
                        f"  [dim]결과는 {stage_file.name} 파일에 기록되었습니다.[/dim]"
                    )
                    end_msg = MessageBubble(role="system", content=result_content)
                    chat_log.mount(end_msg)
                    chat_log.scroll_end(animate=False)
                except FileLockedError as e:
                    msg = MessageBubble(role="system", content=f"[yellow]⚠ 파일 잠금: {e}[/yellow]")
                    chat_log.mount(msg)
                    chat_log.scroll_end(animate=False)
                except Exception as e:
                    msg = MessageBubble(role="system", content=f"[red]✗ 실행 오류: {e}[/red]")
                    chat_log.mount(msg)
                    chat_log.scroll_end(animate=False)
            asyncio.create_task(run_analysis_run())

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
