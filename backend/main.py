"""
BI-Agent CLI — Markdown-Driven 미니멀 REPL

Claude CLI / Gemini CLI 스타일의 극단적으로 심플한 텍스트 REPL.
TUI 없음. 실행과 로그 확인만 CLI에서, 결과물은 마크다운 파일로 IDE에서 확인.
"""
import asyncio
import os
import warnings
import logging
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.CRITICAL)

load_dotenv()

from rich.console import Console
from rich.spinner import Spinner
from rich.text import Text
from rich.live import Live
from rich import box
from rich.table import Table

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.styles import Style as PTStyle
from prompt_toolkit.completion import WordCompleter

console = Console()

PROMPT_STYLE = PTStyle.from_dict({
    "prompt": "bold ansicyan",
    "bottom-toolbar": "bg:#1a1a2e #8888aa",
})

HISTORY_FILE = os.path.expanduser("~/.bi-agent/repl_history")

BANNER = """
[bold cyan]    ____  ____     ___                    __ [/bold cyan]
[bold cyan]   / __ )/  _/    /   | ____ ____  ____  / /_[/bold cyan]
[bold cyan]  / __  |/ /_____/ /| |/ __ `/ _ \\/ __ \\/ __/[/bold cyan]
[bold cyan] / /_/ // /_____/ ___ / /_/ /  __/ / / / /_  [/bold cyan]
[bold cyan]/_____/___/    /_/  |_\\__, /\\___/_/ /_/\\__/  [/bold cyan]
[bold cyan]                     /____/                  [/bold cyan]
"""

COMMAND_NAMES = [
    "/help", "/quit", "/exit", "/clear",
    "/list", "/connect",
    "/thinking", "/run", "/expert",
    "/init", "/build",
    "/analysis-new", "/analysis-quick", "/analysis-status",
    "/analysis-list", "/analysis-run", "/analysis-next", "/analysis-archive",
]

HELP_TEXT = """
[bold]── 기본 명령어 ──[/bold]
  [cyan]/help[/cyan]              이 도움말 표시
  [cyan]/clear[/cyan]             화면 초기화
  [cyan]/quit[/cyan], [cyan]/exit[/cyan]      종료
  [cyan]/list[/cyan]              연결된 데이터 소스 목록

[bold]── 마크다운 중심 분석 ──[/bold]
  [cyan]/thinking[/cyan] [idea]   분석 아이디어를 마크다운 계획서 초안으로 확장
  [cyan]/run[/cyan] [file.md]     마크다운 문서 기반 분석 실행
  [cyan]/expert[/cyan] [질문]     LangChain 기반 Expert 모드 심층 분석

[bold]── AaC (Analysis as Code) ──[/bold]
  [cyan]/init[/cyan]              현재 디렉토리에 plan.md 템플릿 생성
  [cyan]/build[/cyan]             plan.md 분석 파이프라인 실행

[bold]── ALIVE 분석 ──[/bold]
  [cyan]/analysis-new[/cyan] [제목]      새 ALIVE 분석 생성
  [cyan]/analysis-quick[/cyan] [질문]    퀵 단일파일 분석 생성
  [cyan]/analysis-status[/cyan]          현재 분석 상태 확인
  [cyan]/analysis-list[/cyan]            모든 분석 목록
  [cyan]/analysis-run[/cyan]             현재 스테이지 BI-EXEC 블록 실행
  [cyan]/analysis-next[/cyan]            다음 스테이지로 전환
  [cyan]/analysis-archive[/cyan]         현재 분석 아카이브

[bold]── 자연어 질문 ──[/bold]
  그냥 질문하세요. AI가 자율적으로 DB를 조회하고 답변합니다.

  > 월별 매출 트렌드를 분석해줘
  > 이번 분기 가장 많이 팔린 상품 TOP 10은?
"""


def print_banner(conn_info: str = "연결 없음"):
    console.clear()
    console.print(BANNER)
    console.print(
        f"  [dim]v2.0.0 (Naked)[/dim]  [dim]·[/dim]  "
        f"[green]●[/green] [dim]{conn_info}[/dim]  [dim]·[/dim]  "
        f"[dim]/help 로 도움말[/dim]"
    )
    console.print()


def get_conn_info() -> tuple:
    """현재 연결 정보를 반환. (conn_id, display_str)"""
    try:
        from backend.utils.path_config import path_manager
        import json
        registry_path = path_manager.get_project_path("default") / "connections.json"
        if registry_path.exists():
            with open(registry_path) as f:
                reg = json.load(f)
            if reg:
                first = next(iter(reg))
                info = reg[first]
                return first, f"{info.get('name', first)} ({info.get('type', '?')})"
    except Exception:
        pass
    return None, "연결 없음"


def make_toolbar(conn_display: str):
    return f" ● {conn_display}  │  /help"


async def repl():
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)

    # Core Agent 초기화
    agent = None
    try:
        from backend.core.core_agent import CoreAgent
        agent = CoreAgent()
    except Exception as e:
        console.print(f"[yellow]⚠ Core Agent 초기화 실패: {e}[/yellow]")

    conn_id, conn_display = get_conn_info()
    print_banner(conn_display)

    completer = WordCompleter(COMMAND_NAMES, sentence=True)

    session: PromptSession = PromptSession(
        history=FileHistory(HISTORY_FILE),
        auto_suggest=AutoSuggestFromHistory(),
        completer=completer,
        style=PROMPT_STYLE,
        bottom_toolbar=lambda: make_toolbar(conn_display),
    )

    while True:
        try:
            user_input = await session.prompt_async(
                [("class:prompt", " > ")],
            )
        except KeyboardInterrupt:
            console.print("\n[dim](Ctrl+C — /quit 으로 종료)[/dim]")
            continue
        except EOFError:
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        cmd = user_input.lower().split()[0] if user_input.startswith("/") else None

        # ── 시스템 명령어 ──

        if cmd in ("/quit", "/exit", "/종료"):
            console.print("\n[dim]Bye![/dim]\n")
            break

        elif cmd == "/clear":
            _, conn_display = get_conn_info()
            print_banner(conn_display)
            continue

        elif cmd == "/help":
            console.print(HELP_TEXT)
            continue

        elif cmd == "/list":
            try:
                from backend.utils.path_config import path_manager
                import json
                registry_path = path_manager.get_project_path("default") / "connections.json"
                with open(registry_path) as f:
                    reg = json.load(f)
                if reg:
                    t = Table(box=box.SIMPLE, show_header=True, header_style="bold")
                    t.add_column("ID", style="cyan")
                    t.add_column("이름")
                    t.add_column("타입", style="green")
                    for cid, cinfo in reg.items():
                        t.add_row(cid, cinfo.get("name", cid), cinfo.get("type", "?"))
                    console.print(t)
                else:
                    console.print("[dim]연결된 데이터 소스가 없습니다.[/dim]")
            except Exception as e:
                console.print(f"[red]오류: {e}[/red]")
            continue

        # ── /thinking: 마크다운 초안 생성 ──

        elif cmd == "/thinking":
            idea = user_input[len("/thinking"):].strip()
            if not idea:
                console.print("[dim]사용법: /thinking [분석 아이디어][/dim]")
                continue

            if agent is None:
                console.print("[red]Agent가 초기화되지 않았습니다.[/red]")
                continue

            with Live(Spinner("dots", text=Text(" 분석 계획서 초안 작성 중...", style="dim")),
                       console=console, refresh_per_second=12, transient=True):
                draft = agent.thinking(idea)

            # 파일 저장
            analyses_dir = Path("analyses")
            analyses_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            slug = idea[:30].replace(" ", "_").replace("/", "_")
            file_path = analyses_dir / f"{timestamp}_{slug}.md"
            file_path.write_text(draft, encoding="utf-8")

            console.print(f"[green]✓ 분석 계획서 초안 생성 완료[/green]")
            console.print(f"  [cyan]{file_path}[/cyan]")
            console.print(f"  [dim]IDE에서 열어 수정 후, /run {file_path} 으로 실행하세요.[/dim]")
            continue

        # ── /run: 마크다운 문서 기반 실행 ──

        elif cmd == "/run":
            file_path = user_input[len("/run"):].strip()
            if not file_path:
                console.print("[dim]사용법: /run [파일경로.md][/dim]")
                continue

            path = Path(file_path)
            if not path.exists():
                console.print(f"[red]✗ 파일을 찾을 수 없습니다: {file_path}[/red]")
                continue

            if agent is None:
                console.print("[red]Agent가 초기화되지 않았습니다.[/red]")
                continue

            md_content = path.read_text(encoding="utf-8")
            prompt = f"아래 마크다운 문서의 분석 계획에 따라 데이터 분석을 실행해주세요. 각 단계의 SQL을 실행하고, 결과를 요약해주세요.\n\n---\n\n{md_content}"

            with Live(Spinner("dots", text=Text(" 문서 기반 분석 실행 중...", style="dim")),
                       console=console, refresh_per_second=12, transient=True):
                answer = agent.run(prompt)

            console.print(answer)

            # 결과를 별도 파일로 저장
            result_path = path.with_name(path.stem + "_result.md")
            result_content = f"# 분석 결과\n\n> 원본: {path.name}\n> 실행: {datetime.now().isoformat()}\n\n{answer}"
            result_path.write_text(result_content, encoding="utf-8")
            console.print(f"\n[green]✓ 결과 저장: {result_path}[/green]")
            continue

        # ── /expert: LangChain Expert 모드 ──

        elif cmd == "/expert":
            question = user_input[len("/expert"):].strip()
            if not question:
                console.print("[dim]사용법: /expert [복잡한 분석 질문][/dim]")
                continue

            try:
                from backend.orchestrator.orchestrators.agentic_orchestrator import AgenticOrchestrator
                expert = AgenticOrchestrator(use_checkpointer=False)
                with Live(Spinner("dots", text=Text(" Expert 모드 분석 중...", style="dim")),
                           console=console, refresh_per_second=12, transient=True):
                    result = asyncio.get_event_loop().run_until_complete(
                        expert.run(question)
                    ) if not asyncio.get_event_loop().is_running() else await expert.run(question)

                if isinstance(result, dict):
                    answer = result.get("final_response") or result.get("final_answer") or str(result)
                else:
                    answer = str(result)
                console.print(answer)
            except Exception as e:
                console.print(f"[red]Expert 모드 오류: {e}[/red]")
            continue

        # ── /init: plan.md 템플릿 생성 ──

        elif cmd == "/init":
            try:
                import os
                from backend.aac.plan_parser import PlanParser
                plan_path = "plan.md"
                if os.path.exists(plan_path):
                    console.print(f"[yellow]⚠ {plan_path}가 이미 존재합니다.[/yellow]")
                else:
                    template = PlanParser().generate_template()
                    with open(plan_path, "w", encoding="utf-8") as f:
                        f.write(template)
                    console.print(f"[green]✓ {plan_path} 템플릿이 생성되었습니다.[/green] [dim](경로: {os.getcwd()})[/dim]")
                    console.print(f"[dim]IDE에서 편집 후 /build 로 분석을 시작하세요.[/dim]")
            except Exception as e:
                console.print(f"[red]✗ 오류: {e}[/red]")
            continue

        # ── /build: plan.md 파이프라인 실행 ──

        elif cmd == "/build":
            try:
                import os
                plan_path = "plan.md"
                if not os.path.exists(plan_path):
                    console.print("[red]✗ plan.md 파일이 없습니다. /init 으로 먼저 생성하세요.[/red]")
                else:
                    from backend.aac.plan_parser import PlanParser
                    from backend.aac.aac_orchestrator import AaCOrchestrator
                    parser = PlanParser()
                    intent = parser.parse_file(plan_path)
                    console.print(f"[cyan]▶ 분석 시작[/cyan]  목표: [bold]{intent.goal or '(목표 미지정)'}[/bold]")
                    console.print(f"  데이터소스: {intent.data_sources or ['(미지정)']}")
                    console.print(f"  지표: {intent.metrics or ['(미지정)']}")
                    orchestrator_aac = AaCOrchestrator(intent=intent)
                    with Live(Spinner("dots", text=Text(" 파이프라인 실행 중...", style="dim")),
                               console=console, refresh_per_second=12, transient=True):
                        results = await orchestrator_aac.run()
                    step_labels = {
                        "profile": "데이터 프로파일링",
                        "query": "데이터 조회",
                        "transform": "데이터 가공",
                        "visualize": "시각화",
                        "insight": "인사이트 도출",
                    }
                    console.print("[green]✓ 파이프라인 완료[/green]")
                    for r in results:
                        label = step_labels.get(r.step.value, r.step.value)
                        if r.success:
                            console.print(f"  [green]✓[/green] {label}")
                        else:
                            console.print(f"  [red]✗[/red] {label}: {r.error}")
                    console.print("[dim]/export html 로 결과물을 내보내세요.[/dim]")
            except Exception as e:
                console.print(f"[red]✗ 오류: {e}[/red]")
            continue

        # ── /analysis-new: 새 ALIVE 분석 생성 ──

        elif cmd == "/analysis-new":
            title = user_input[len("/analysis-new"):].strip()
            if not title:
                console.print("[yellow]사용법: /analysis-new <분석 제목>[/yellow]")
            else:
                try:
                    from backend.aac.analysis_manager import AnalysisManager
                    mgr = AnalysisManager()
                    project = mgr.create_analysis(title=title, connection="")
                    console.print(f"[green]✓ ALIVE 분석 생성됨:[/green] [bold]{project.title}[/bold]")
                    console.print(f"  ID: [cyan]{project.id}[/cyan]")
                    console.print(f"  스테이지: [yellow]{project.status.value.upper()}[/yellow]")
                    console.print(f"  경로: [dim]{project.path}[/dim]")
                    console.print(f"  [dim]/analysis-run 으로 BI-EXEC 블록을 실행하거나 파일을 편집하세요.[/dim]")
                except Exception as e:
                    console.print(f"[red]✗ 오류: {e}[/red]")
            continue

        # ── /analysis-quick: 퀵 단일파일 분석 생성 ──

        elif cmd == "/analysis-quick":
            question = user_input[len("/analysis-quick"):].strip()
            if not question:
                console.print("[yellow]사용법: /analysis-quick <분석 질문>[/yellow]")
            else:
                try:
                    from backend.aac.analysis_manager import AnalysisManager
                    mgr = AnalysisManager()
                    filepath = mgr.create_quick(question=question, connection="")
                    console.print(f"[green]✓ 퀵 분석 생성됨:[/green] [bold]{question}[/bold]")
                    console.print(f"  경로: [dim]{filepath}[/dim]")
                    console.print(f"  [dim]단일 파일로 ALIVE 전체 구조가 포함되어 있습니다.[/dim]")
                except Exception as e:
                    console.print(f"[red]✗ 오류: {e}[/red]")
            continue

        # ── /analysis-status: 현재 분석 상태 ──

        elif cmd == "/analysis-status":
            try:
                from backend.aac.analysis_manager import AnalysisManager
                mgr = AnalysisManager()
                project = mgr.get_active()
                if not project:
                    all_analyses = mgr.list_analyses()
                    if not all_analyses:
                        console.print("[yellow]분석 프로젝트가 없습니다. /analysis-new 로 생성하세요.[/yellow]")
                    else:
                        console.print("[yellow]활성 분석이 없습니다. /analysis-list 로 목록을 확인하세요.[/yellow]")
                else:
                    stage_emoji = {"ask": "❶", "look": "❷", "investigate": "❸", "voice": "❹", "evolve": "❺"}
                    emoji = stage_emoji.get(project.status.value, "●")
                    console.print(f"[bold cyan]◈ 현재 분석 상태 ◈[/bold cyan]")
                    console.print(f"  제목: [bold]{project.title}[/bold]")
                    console.print(f"  ID: [cyan]{project.id}[/cyan]")
                    console.print(f"  스테이지: {emoji} [yellow]{project.status.value.upper()}[/yellow]")
                    console.print(f"  연결: [dim]{project.connection or '(없음)'}[/dim]")
                    console.print(f"  생성: [dim]{project.created}[/dim]")
                    console.print(f"  경로: [dim]{project.path}[/dim]")
                    console.print(f"  [dim]/analysis-run 으로 현재 스테이지 실행 | /analysis-next 로 다음 스테이지 이동[/dim]")
            except Exception as e:
                console.print(f"[red]✗ 오류: {e}[/red]")
            continue

        # ── /analysis-list: 모든 분석 목록 ──

        elif cmd == "/analysis-list":
            try:
                from backend.aac.analysis_manager import AnalysisManager
                mgr = AnalysisManager()
                analyses = mgr.list_analyses()
                if not analyses:
                    console.print("[yellow]분석 프로젝트가 없습니다. /analysis-new 로 생성하세요.[/yellow]")
                else:
                    active = mgr.get_active()
                    active_id = active.id if active else None
                    console.print(f"[bold cyan]◈ ALIVE 분석 목록 ◈[/bold cyan]")
                    for p in analyses:
                        marker = "[green]▶[/green]" if p.id == active_id else " "
                        console.print(f"  {marker} [bold]{p.title}[/bold] [dim]({p.id})[/dim]")
                        console.print(f"      스테이지: [yellow]{p.status.value.upper()}[/yellow]  |  생성: [dim]{p.created[:10]}[/dim]")
                    console.print(f"\n[dim]{len(analyses)}개의 분석 프로젝트[/dim]")
            except Exception as e:
                console.print(f"[red]✗ 오류: {e}[/red]")
            continue

        # ── /analysis-run: 현재 스테이지 BI-EXEC 실행 ──

        elif cmd == "/analysis-run":
            try:
                from backend.aac.analysis_manager import AnalysisManager
                from backend.aac.stage_executor import StageExecutor, FileLockedError
                mgr = AnalysisManager()
                project = mgr.get_active()
                if not project:
                    console.print("[yellow]활성 분석이 없습니다. /analysis-new 로 먼저 생성하세요.[/yellow]")
                else:
                    stage_file = project.current_stage_file()
                    if not stage_file.exists():
                        console.print(f"[red]✗ 스테이지 파일 없음: {stage_file}[/red]")
                    else:
                        try:
                            from backend.orchestrator.orchestrators.agentic_orchestrator import AgenticOrchestrator
                            registry = AgenticOrchestrator(use_checkpointer=False)._registry
                        except Exception:
                            registry = None
                        executor = StageExecutor(registry=registry)
                        count = executor.count_bi_exec_blocks(stage_file)
                        if count == 0:
                            console.print(f"[yellow]실행할 BI-EXEC 블록이 없습니다.[/yellow]")
                            console.print(f"  [dim]스테이지: {project.status.value.upper()} | 파일: {stage_file.name}[/dim]")
                        else:
                            console.print(f"[cyan]▶ BI-EXEC 실행 시작[/cyan]")
                            console.print(f"  스테이지: [yellow]{project.status.value.upper()}[/yellow]  |  블록 수: [bold]{count}[/bold]")
                            prior_files = project.completed_stage_files()
                            with Live(Spinner("dots", text=Text(" 실행 중...", style="dim")),
                                       console=console, refresh_per_second=12, transient=True):
                                executor.execute_stage(stage_file, prior_stage_files=prior_files)
                            console.print(f"[green]✓ BI-EXEC 실행 완료[/green]  블록 수: [bold]{count}[/bold]")
                            console.print(f"  [dim]결과는 {stage_file.name} 파일에 기록되었습니다.[/dim]")
            except FileLockedError as e:
                console.print(f"[yellow]⚠ 파일 잠금: {e}[/yellow]")
            except Exception as e:
                console.print(f"[red]✗ 오류: {e}[/red]")
            continue

        # ── /analysis-next: 다음 스테이지로 전환 ──

        elif cmd == "/analysis-next":
            try:
                from backend.aac.analysis_manager import AnalysisManager
                mgr = AnalysisManager()
                project = mgr.get_active()
                if not project:
                    console.print("[yellow]활성 분석이 없습니다. /analysis-new 로 먼저 생성하세요.[/yellow]")
                else:
                    prev_stage = project.status.value.upper()
                    mgr.advance_stage(project)
                    project = mgr.get_active()
                    new_stage = project.status.value.upper() if project else "ARCHIVED"
                    console.print(f"[green]✓ 스테이지 전환 완료:[/green] [yellow]{prev_stage}[/yellow] → [cyan]{new_stage}[/cyan]")
                    console.print(f"  [dim]새 스테이지 파일이 생성되었습니다. /analysis-run 으로 실행하세요.[/dim]")
            except ValueError as e:
                console.print(f"[yellow]⚠ {e}[/yellow]")
            except Exception as e:
                console.print(f"[red]✗ 오류: {e}[/red]")
            continue

        # ── /analysis-archive: 현재 분석 아카이브 ──

        elif cmd == "/analysis-archive":
            try:
                from backend.aac.analysis_manager import AnalysisManager
                mgr = AnalysisManager()
                project = mgr.get_active()
                if not project:
                    console.print("[yellow]활성 분석이 없습니다.[/yellow]")
                else:
                    title = project.title
                    mgr.archive(project)
                    console.print(f"[green]✓ 분석 아카이브됨:[/green] [bold]{title}[/bold]")
            except Exception as e:
                console.print(f"[red]✗ 오류: {e}[/red]")
            continue

        elif cmd and cmd.startswith("/"):
            console.print(f"[dim]알 수 없는 명령어: {cmd}  (/help 참고)[/dim]")
            continue

        # ── 일반 자연어 질문 → Core Agent ──

        if agent is None:
            console.print("[red]Agent가 초기화되지 않았습니다.[/red]")
            continue

        with Live(
            Spinner("dots", text=Text(" 분석 중...", style="dim")),
            console=console,
            refresh_per_second=12,
            transient=True,
        ):
            try:
                answer = agent.run(user_input)
            except Exception as e:
                answer = f"오류가 발생했습니다: {e}"

        console.print(answer)


def main():
    try:
        asyncio.run(repl())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
