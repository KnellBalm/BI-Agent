"""
BI-Agent CLI — Claude CLI 스타일 하이브리드 REPL
터미널 자연 스크롤 방식 + 번호 블록 시스템 + 하단 상태바
"""
import asyncio
import os
import warnings
import logging
from dotenv import load_dotenv

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.CRITICAL)

load_dotenv()

from rich.console import Console
from rich.text import Text
from rich.spinner import Spinner
from rich.live import Live
from rich import box

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.styles import Style as PTStyle
from prompt_toolkit.completion import WordCompleter

from backend.orchestrator.ui.block_renderer import BlockStore, BlockRenderer
from backend.orchestrator.cli.command_router import COMMAND_NAMES, HELP_TEXT, is_block_ref

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


def print_banner(conn_info: str = "연결 없음"):
    console.clear()
    console.print(BANNER)
    console.print(
        f"  [dim]v0.1.0[/dim]  [dim]·[/dim]  "
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


def make_toolbar(store: BlockStore, conn_display: str):
    """prompt_toolkit bottom_toolbar 콜백."""
    count = store.count()
    count_str = f"{count}개 대화" if count else "대화 없음"
    return f" ● {conn_display}  │  {count_str}  │  /help"


async def run_query(orchestrator, user_input: str) -> str:
    """AgenticOrchestrator로 쿼리 실행."""
    result = await orchestrator.run(user_input)
    if isinstance(result, dict):
        return result.get("final_response") or result.get("final_answer") or result.get("output") or str(result)
    return str(result)


async def repl():
    # 히스토리 디렉토리 생성
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)

    # BlockStore + BlockRenderer 초기화
    store = BlockStore()
    renderer = BlockRenderer(console)

    # Orchestrator 및 세션 상태 초기화
    orchestrator = None
    try:
        from backend.orchestrator.orchestrators.agentic_orchestrator import AgenticOrchestrator
        orchestrator = AgenticOrchestrator(use_checkpointer=False)
    except Exception as e:
        console.print(f"[yellow]⚠ Orchestrator 초기화 실패: {e}[/yellow]")

    # AaC 파이프라인 상태 보관용
    last_pipeline_results = None
    last_intent = None

    conn_id, conn_display = get_conn_info()
    print_banner(conn_display)

    # 슬래시 명령어 자동완성
    completer = WordCompleter(COMMAND_NAMES, sentence=True)

    session: PromptSession = PromptSession(
        history=FileHistory(HISTORY_FILE),
        auto_suggest=AutoSuggestFromHistory(),
        completer=completer,
        style=PROMPT_STYLE,
        bottom_toolbar=lambda: make_toolbar(store, conn_display),
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

        # @N 블록 참조
        block_ref = is_block_ref(user_input)
        if block_ref:
            block = store.get(block_ref)
            if block:
                renderer.render_block_ref(block)
            else:
                console.print(f"[dim]블록 #{block_ref}이 없습니다. (현재 {store.count()}개)[/dim]")
            continue

        # 슬래시 명령어
        cmd = user_input.lower().split()[0] if user_input.startswith("/") else None

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

        elif cmd == "/history":
            renderer.render_history_list(store.all())
            continue

        elif cmd == "/list":
            try:
                from backend.utils.path_config import path_manager
                import json
                from rich.table import Table
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

        elif cmd == "/init":
            from backend.aac.plan_parser import PlanParser
            template = PlanParser().generate_template()
            plan_path = "plan.md"
            if os.path.exists(plan_path):
                console.print("[yellow]⚠ plan.md가 이미 존재합니다. 덮어쓰려면 /init --force를 사용하세요.[/yellow]")
            else:
                with open(plan_path, "w", encoding="utf-8") as f:
                    f.write(template)
                console.print(f"[green]✓ plan.md 템플릿이 생성되었습니다.[/green] [dim](현재 디렉토리: {os.getcwd()})[/dim]")
                console.print("[dim]/edit 로 편집하거나, 직접 수정 후 /build 로 분석을 시작하세요.[/dim]")
            continue

        elif cmd == "/build":
            plan_path = "plan.md"
            if not os.path.exists(plan_path):
                console.print("[red]✗ plan.md 파일이 없습니다. /init 으로 먼저 템플릿을 생성하세요.[/red]")
                continue
            try:
                from backend.aac.plan_parser import PlanParser
                from backend.aac.aac_orchestrator import AaCOrchestrator, PipelineStep
                import asyncio as _asyncio

                parser = PlanParser()
                intent = parser.parse_file(plan_path)
                console.print(f"[cyan]▶ 분석 시작[/cyan]  목표: [bold]{intent.goal or '(목표 미지정)'}[/bold]")
                console.print(f"  데이터소스: {intent.data_sources or ['(미지정)']}")
                console.print(f"  지표: {intent.metrics or ['(미지정)']}")
                console.print()

                orchestrator_aac = AaCOrchestrator(intent=intent)

                step_labels = {"profile": "데이터 프로파일링", "query": "데이터 조회",
                               "transform": "데이터 가공", "visualize": "시각화", "insight": "인사이트 도출"}

                with Live(Spinner("dots", text=Text(" 파이프라인 실행 중...", style="dim")),
                          console=console, refresh_per_second=12, transient=True):
                    results = await orchestrator_aac.run()
                    last_pipeline_results = results
                    last_intent = intent

                for r in results:
                    label = step_labels.get(r.step.value, r.step.value)
                    if r.success:
                        console.print(f"[green]✓[/green] {label}")
                        if r.output:
                            console.print(f"  [dim]{r.output[:200]}...[/dim]" if len(r.output) > 200 else f"  [dim]{r.output}[/dim]")
                    else:
                        console.print(f"[red]✗[/red] {label}: {r.error}")

                console.print("\n[green]✓ 파이프라인 완료[/green]  [dim]/export html 로 결과물을 내보내세요.[/dim]")
            except Exception as e:
                console.print(f"[red]✗ 빌드 오류: {e}[/red]")
            continue

        elif cmd == "/edit":
            parts = user_input.split()
            target = parts[1] if len(parts) > 1 else "plan"
            
            if target == "plan":
                plan_path = "plan.md"
                if not os.path.exists(plan_path):
                    console.print("[red]✗ plan.md 파일이 없습니다. /init 으로 먼저 템플릿을 생성하세요.[/red]")
                    continue
                
                try:
                    from backend.aac.interactive_editor import MarkdownEditorApp
                    app = MarkdownEditorApp(plan_path)
                    # 프롬프트 툴킷의 루프 내에서 Textual 앱을 직접 실행합니다.
                    # Textual이 종료되면 다시 이 루프로 안전하게 돌아옵니다.
                    saved = await app.run_async()
                    
                    if saved:
                        console.print(f"[green]✓ {plan_path} 덮어쓰기 완료[/green]")
                    else:
                        console.print(f"[dim]✓ {plan_path} 수정 취소됨[/dim]")
                except Exception as e:
                    console.print(f"[red]✗ 에디터 실행 오류: {e}[/red]")
            else:
                console.print(f"[dim]지원하지 않는 대상입니다: {target}[/dim]")
            continue

        elif cmd == "/export":
            parts = user_input.split()
            fmt = parts[1] if len(parts) > 1 else "html"
            
            if not last_pipeline_results or not last_intent:
                console.print("[red]✗ 내보낼 분석 결과가 없습니다. 먼저 /build 를 실행하세요.[/red]")
                continue
                
            try:
                from backend.utils.output_packager import OutputPackager
                result_name = last_intent.goal if last_intent.goal else "aac_analysis_result"
                
                # 결과 취합
                analysis_data = {
                    "goal": last_intent.goal,
                    "metrics": last_intent.metrics,
                    "summary": {}
                }
                
                for r in last_pipeline_results:
                    if r.success and r.step.value in ["insight", "visualize"]:
                        analysis_data["summary"][r.step.value] = r.output

                packager = OutputPackager("default")
                exported = packager.create_full_package(
                    result_name=result_name,
                    analysis_result=analysis_data,
                    export_formats=[fmt]
                )
                
                console.print(f"[green]✓ 성공적으로 패키징 되었습니다:[/green]")
                for format_type, path in exported.items():
                    console.print(f"  - [cyan]{format_type}[/cyan]: {path}")
                    
            except Exception as e:
                console.print(f"[red]✗ 내보내기 오류: {e}[/red]")
            continue

        elif cmd == "/connect":
            console.print("[dim]TUI 모드에서 연결을 설정하세요: [cyan]bi-agent[/cyan][/dim]")
            continue

        elif cmd == "/explore":
            console.print("[dim]TUI 모드에서 DB를 탐색하세요: [cyan]bi-agent[/cyan][/dim]")
            continue

        elif cmd and cmd.startswith("/"):
            console.print(f"[dim]알 수 없는 명령어: {cmd}  (/help 참고)[/dim]")
            continue

        # 일반 질문 — Orchestrator 실행
        if orchestrator is None:
            console.print("[red]Orchestrator가 초기화되지 않았습니다.[/red]")
            continue

        with Live(
            Spinner("dots", text=Text(" 분석 중...", style="dim")),
            console=console,
            refresh_per_second=12,
            transient=True,
        ):
            try:
                answer = await run_query(orchestrator, user_input)
            except Exception as e:
                answer = f"오류가 발생했습니다: {e}"

        block = store.add(user_input, answer)
        renderer.render(block)


def main():
    try:
        asyncio.run(repl())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
