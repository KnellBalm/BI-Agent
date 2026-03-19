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

# 루트 로거 콘솔 출력 차단 (외부 라이브러리 로그 억제)
_root = logging.getLogger()
_root.setLevel(logging.CRITICAL)
for _h in _root.handlers[:]:
    _root.removeHandler(_h)

# 주요 시끄러운 로거들 개별 침묵
for noisy in ("httpcore", "httpx", "google_genai", "urllib3", "google.auth", "google_genai.models"):
    logging.getLogger(noisy).setLevel(logging.CRITICAL)
    logging.getLogger(noisy).propagate = False

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
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.key_binding import KeyBindings

console = Console()

PROMPT_STYLE = PTStyle.from_dict({
    "prompt": "bold ansicyan",
    "status": "#666666",
    "bottom-toolbar": "bg:#1a1a2e #8888aa",
    # completion menu — 배경에 녹아드는 미니멀 테마
    "completion-menu": "bg:default #888888",
    "completion-menu.completion": "bg:default #aaaaaa",
    "completion-menu.completion.current": "bg:#333333 #ffffff bold",
    "completion-menu.meta.completion": "bg:default #666666 italic",
    "completion-menu.meta.completion.current": "bg:#333333 #aaaaaa italic",
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

# ──────────────────────────────────────────────
# 계층형 명령어 트리 (Nested Command Tree)
# ──────────────────────────────────────────────
# children 이 있는 명령어는 서브커맨드를 지원한다.
COMMAND_TREE: dict = {
    "/help":    {"meta": "Show this help message"},
    "/quit":    {"meta": "Exit the application"},
    "/exit":    {"meta": "Exit the application"},
    "/clear":   {"meta": "Clear the screen"},
    "/list":    {"meta": "Show connected data sources"},
    "/connect": {
        "meta": "Connect to a new data source",
        "children": {
            "sqlite": {"meta": "Connect to a SQLite database file"},
            "excel":  {"meta": "Connect to an Excel file"},
            "pg":     {"meta": "Connect to PostgreSQL database"},
        },
    },
    "/setting": {
        "meta": "Manage settings, API keys, OAuth login",
        "children": {
            "list":  {"meta": "Show current settings"},
            "set":   {
                "meta": "Update a setting value",
                "children": {
                    "gemini_key": {"meta": "Gemini API key"},
                    "claude_key": {"meta": "Claude API key"},
                    "openai_key": {"meta": "OpenAI API key"},
                    "model":      {"meta": "Default LLM model (e.g. gemini-2.5-flash)"},
                    "language":   {"meta": "Response language (ko, en, ja)"},
                },
            },
            "login": {
                "meta": "OAuth login to a provider",
                "children": {
                    "gemini": {"meta": "Google OAuth"},
                    "claude": {"meta": "Claude API key entry"},
                    "openai": {"meta": "OpenAI API key entry"},
                },
            },
            "help":  {"meta": "Show setting help details"},
        },
    },
    "/thinking":         {"meta": "Expand an idea into a markdown analysis plan"},
    "/run":              {"meta": "Execute an analysis from a markdown plan"},
    "/expert":           {"meta": "LangChain Expert mode deep-dive analysis"},
    "/init":             {"meta": "Generate plan.md template in current dir"},
    "/build":            {"meta": "Run the analysis pipeline from plan.md"},
    "/analysis": {
        "meta": "ALIVE analysis workflow",
        "children": {
            "new":     {"meta": "Create a new ALIVE analysis session"},
            "quick":   {"meta": "Run a quick single-file analysis"},
            "status":  {"meta": "Check current analysis status"},
            "list":    {"meta": "Show all analysis sessions"},
            "run":     {"meta": "Execute BI-EXEC block of current stage"},
            "next":    {"meta": "Transition to the next stage"},
            "archive": {"meta": "Archive the current analysis session"},
        },
    },
}

COMMAND_NAMES = list(COMMAND_TREE.keys())


class SlashCompleter(Completer):
    """/로 시작하는 계층형 명령어 자동완성 엔진.

    입력 토큰 수에 따라 올바른 depth의 후보를 제안한다.
    예) "/"        → 1-depth 전체
        "/setting " → 2-depth (login, set, list, help)
        "/setting login " → 3-depth (gemini, claude, openai)
    """

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if not text.startswith("/"):
            return

        parts = text.split()
        # 커서 바로 앞이 공백이면 다음 depth 진입
        trailing_space = text.endswith(" ")

        if not trailing_space and len(parts) <= 1:
            # 1-depth: 메인 명령어 매칭
            word = parts[0] if parts else "/"
            for cmd, node in COMMAND_TREE.items():
                if cmd.startswith(word):
                    yield Completion(
                        cmd,
                        start_position=-len(word),
                        display=cmd,
                        display_meta=node.get("meta", ""),
                    )
        else:
            # 2-depth 이상: 부모 노드를 찾아서 children 제안
            main_cmd = parts[0]  # e.g. "/setting"
            node = COMMAND_TREE.get(main_cmd)
            if not node or "children" not in node:
                return

            # depth 를 따라 내려가기
            children = node["children"]
            depth_parts = parts[1:]  # e.g. ["login", "gem"]

            # 이미 완성된 중간 토큰을 따라 내려감
            while len(depth_parts) > 1 or (len(depth_parts) == 1 and trailing_space):
                if not depth_parts:
                    break
                token = depth_parts[0]
                child_node = children.get(token)
                if child_node and "children" in child_node:
                    children = child_node["children"]
                    depth_parts = depth_parts[1:]
                else:
                    if trailing_space and len(depth_parts) == 1:
                        child_node = children.get(depth_parts[0])
                        if child_node and "children" in child_node:
                            children = child_node["children"]
                            depth_parts = []
                        else:
                            return
                    else:
                        break

            # 현재 depth 에서 매칭
            word = depth_parts[0] if depth_parts else ""
            for sub, sub_node in children.items():
                if sub.startswith(word):
                    yield Completion(
                        sub,
                        start_position=-len(word),
                        display=sub,
                        display_meta=sub_node.get("meta", ""),
                    )

HELP_TEXT = """
[bold]── 기본 명령어 (System) ──[/bold]
  [cyan]/help[/cyan]              명령어 상세 도움말 표시 (Show detailed help)
  [cyan]/clear[/cyan]             화면 초기화 (Clear screen)
  [cyan]/quit[/cyan], [cyan]/exit[/cyan]      프로그램 종료 (Exit application)

[bold]── 연결 및 설정 (Connection & Config) ──[/bold]
  [cyan]/list[/cyan]              현재 연동된 데이터 소스(DB) 목록 확인
  [cyan]/connect[/cyan]           새로운 데이터 소스 연동
  [cyan]/setting[/cyan]           [LLM API Key / 언어 / 모델] 설정 관리

[bold]── 마크다운 & 대화형 분석 (Markdown & Chat) ──[/bold]
  [cyan]/thinking[/cyan] [idea]   간단한 아이디어를 구체적인 마크다운 계획서 초안으로 확장
  [cyan]/run[/cyan] [file.md]     마크다운 문서의 절차에 따라 분석 자동 실행
  [cyan]/expert[/cyan] [질문]     LangChain 기반 Expert 모드로 복잡한 질문 심층 분석

[bold]── AaC (Analysis as Code) 파이프라인 ──[/bold]
  [cyan]/init[/cyan]              현재 디렉토리에 실행 가능한 plan.md 템플릿 생성
  [cyan]/build[/cyan]             plan.md에 정의된 분석 파이프라인 전체 실행

[bold]── ALIVE 분석 플로우 (ALIVE Session) ──[/bold]
  [cyan]/analysis new[/cyan] [제목]       새로운 ALIVE 분석 세션 생성
  [cyan]/analysis quick[/cyan] [질문]    단일 파일을 대상으로 빠른 분석 생성
  [cyan]/analysis status[/cyan]          현재 활성화된 분석의 진행 상태 확인
  [cyan]/analysis list[/cyan]            전체 분석 세션 목록 표시
  [cyan]/analysis run[/cyan]             현재 스테이지의 BI-EXEC 블록(코드) 실행
  [cyan]/analysis next[/cyan]            분석을 다음 스테이지로 강제 전환
  [cyan]/analysis archive[/cyan]         현재 분석 화면 및 데이터를 아카이브 저장

[bold]── 자연어 질문 (Natural Language) ──[/bold]
  / 없이 평문으로 질문하시면 AI가 연결된 DB를 자동 조회하여 답변합니다.
  [dim]> 월별 매출 트렌드를 분석해줘[/dim]
  [dim]> 이번 분기 가장 많이 팔린 상품 TOP 10은?[/dim]
"""


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


def get_status_info() -> dict:
    """현재 CLI 상태를 한눈에 보여주기 위한 정보를 수집한다."""
    status = {"model": "?", "auth": "미설정", "db": "연결 없음"}

    # 모델
    try:
        from backend.utils.setting_manager import setting_manager
        model = setting_manager.get("model")
        if model and model != "(미설정)":
            status["model"] = model
    except Exception:
        pass

    # 인증 방식
    try:
        has_key = bool(os.getenv("GEMINI_API_KEY"))
        if has_key:
            status["auth"] = "API Key"
    except Exception:
        pass

    # DB 연결
    _, conn_display = get_conn_info()
    status["db"] = conn_display

    return status


def print_banner(conn_info: str = "연결 없음"):
    console.clear()
    console.print(BANNER)
    info = get_status_info()
    console.print(
        f"  [dim]v2.0.0 (Naked)[/dim]  [dim]·[/dim]  "
        f"[bold cyan]{info['model']}[/bold cyan]  [dim]·[/dim]  "
        f"[green]●[/green] [dim]{info['auth']}[/dim]  [dim]·[/dim]  "
        f"[dim]{info['db']}[/dim]  [dim]·[/dim]  "
        f"[dim]/help 로 도움말[/dim]"
    )
    console.print()


def make_toolbar(conn_display: str = ""):
    """하단 툴바에 모델, 인증 방식, DB 정보를 실시간 표시한다."""
    info = get_status_info()
    return (
        f" Model: {info['model']}  │  "
        f"Auth: {info['auth']}  │  "
        f"DB: {info['db']}  │  "
        f"/help"
    )


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

    completer = SlashCompleter()

    # Tab = 현재 선택 항목을 확정(입력창에 삽입) + 공백 추가
    kb = KeyBindings()
    @kb.add("tab")
    def _(event):
        b = event.app.current_buffer
        if b.text.startswith("/"):
            if b.complete_state:
                cc = b.complete_state.current_completion
                if cc is None:
                    # 메뉴는 떠있지만 선택이 안 된 상태 → 첫 항목 선택
                    b.complete_next()
                    cc = b.complete_state and b.complete_state.current_completion
                if cc:
                    b.apply_completion(cc)
                    b.insert_text(" ")
            else:
                b.start_completion(select_first=True)
        else:
            b.insert_text("    ")

    session: PromptSession = PromptSession(
        history=FileHistory(HISTORY_FILE),
        auto_suggest=AutoSuggestFromHistory(),
        completer=completer,
        complete_while_typing=True,
        reserve_space_for_menu=6,
        key_bindings=kb,
        style=PROMPT_STYLE,
        bottom_toolbar=lambda: make_toolbar(),
    )

    while True:
        try:
            user_input = await session.prompt_async(
                lambda: [
                    ("class:status", f" {get_status_info()['model']}"),
                    ("", " · "),
                    ("class:status", f"{get_status_info()['auth']}"),
                    ("", " · "),
                    ("class:status", f"{get_status_info()['db']}"),
                    ("", "\n"),
                    ("class:prompt", " > "),
                ],
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

        # ── /connect: 데이터 소스 연결 ──

        elif cmd == "/connect":
            parts = user_input.split(maxsplit=2)
            if len(parts) < 3:
                console.print("[bold]── 데이터 소스 연결 ──[/bold]")
                console.print()
                console.print("  [cyan]/connect sqlite[/cyan]  <파일 경로>     SQLite DB 연결")
                console.print("  [cyan]/connect excel[/cyan]   <파일 경로>     Excel 파일 연결")
                console.print("  [cyan]/connect pg[/cyan]      <연결 문자열>   PostgreSQL 연결")
                console.print()
                console.print("  [dim]예시: /connect sqlite ./data/sales.db[/dim]")
                console.print("  [dim]      /connect excel  ./data/report.xlsx[/dim]")
                console.print("  [dim]      /connect pg     postgresql://user:pw@host:5432/db[/dim]")
            else:
                conn_type = parts[1].lower()
                conn_path = parts[2]
                try:
                    from backend.utils.path_config import path_manager
                    import json as _json
                    type_map = {"sqlite": "sqlite", "excel": "excel", "pg": "postgresql", "postgresql": "postgresql"}
                    resolved_type = type_map.get(conn_type)
                    if not resolved_type:
                        console.print(f"[yellow]지원 타입: sqlite, excel, pg[/yellow]")
                    else:
                        conn_id = os.path.splitext(os.path.basename(conn_path))[0]
                        registry_path = path_manager.get_project_path("default") / "connections.json"
                        registry_path.parent.mkdir(parents=True, exist_ok=True)
                        reg = {}
                        if registry_path.exists():
                            with open(registry_path) as f:
                                reg = _json.load(f)
                        reg[conn_id] = {"name": conn_id, "type": resolved_type, "config": {"path": os.path.abspath(conn_path)}}
                        with open(registry_path, "w") as f:
                            _json.dump(reg, f, indent=2)
                        console.print(f"[green]✓ '{conn_id}' ({resolved_type}) 연결 등록 완료[/green]")
                except Exception as e:
                    console.print(f"[red]연결 오류: {e}[/red]")
            continue

        # ── /setting: 설정 관리 ──

        elif cmd == "/setting":
            parts = user_input.split(maxsplit=3)
            sub = parts[1] if len(parts) > 1 else "list"

            try:
                from backend.utils.setting_manager import setting_manager, SETTING_KEYS

                if sub == "list" or sub == "/setting":
                    settings = setting_manager.get_all()
                    t = Table(title="⚙ 현재 설정", box=box.SIMPLE, show_header=True, header_style="bold")
                    t.add_column("키", style="cyan")
                    t.add_column("값")
                    t.add_column("설명", style="dim")
                    for k, v in settings.items():
                        desc = SETTING_KEYS.get(k, "")
                        t.add_row(k, str(v), desc)
                    console.print(t)
                    console.print("[dim]  /setting set <키> <값> 으로 변경[/dim]")

                elif sub == "login":
                    provider = parts[2] if len(parts) > 2 else "gemini"
                    valid_providers = ["gemini", "claude", "openai"]
                    if provider not in valid_providers:
                        console.print(f"[yellow]지원 프로바이더: {', '.join(valid_providers)}[/yellow]")
                    else:
                        console.print(f"[yellow]OAuth 로그인은 현재 지원되지 않습니다. /setting set gemini_key <키> 로 API 키를 설정하세요.[/yellow]")

                elif sub == "set":
                    if len(parts) < 4:
                        console.print("[yellow]사용법: /setting set <키> <값>[/yellow]")
                        console.print(f"[dim]  지원 키: {', '.join(SETTING_KEYS.keys())}[/dim]")
                    else:
                        key, value = parts[2], parts[3]
                        result = setting_manager.set(key, value)
                        console.print(f"[green]{result}[/green]")

                elif sub == "help":
                    console.print("[bold]── 설정 도움말 ──[/bold]")
                    console.print()
                    for k, desc in SETTING_KEYS.items():
                        console.print(f"  [cyan]{k:<15}[/cyan] {desc}")
                    console.print()
                    console.print("[bold]사용법:[/bold]")
                    console.print("  [cyan]/setting[/cyan]                  현재 설정 표시")
                    console.print("  [cyan]/setting set[/cyan] <키> <값>      설정 변경")
                    console.print("  [cyan]/setting login[/cyan] [provider]  OAuth 로그인 (gemini)")
                    console.print("  [cyan]/setting help[/cyan]             이 도움말")
                    console.print()
                    console.print("[dim]예시: /setting set gemini_key AIza...[/dim]")
                    console.print("[dim]예시: /setting login gemini[/dim]")

                else:
                    console.print(f"[dim]알 수 없는 서브 명령어: {sub}  (/setting help 참고)[/dim]")

            except Exception as e:
                console.print(f"[red]설정 오류: {e}[/red]")
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
                draft = await agent.thinking(idea)

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
                answer = await agent.run(prompt)

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

            if agent is None:
                console.print("[red]Agent가 초기화되지 않았습니다.[/red]")
                continue

            with Live(Spinner("dots", text=Text(" Expert 모드 분석 중...", style="dim")),
                       console=console, refresh_per_second=12, transient=True):
                answer = await agent.run(question)
            console.print(answer)
            continue

        # ── /init: plan.md 템플릿 생성 ──

        elif cmd == "/init":
            console.print("[yellow]/init 명령어는 더 이상 지원되지 않습니다.[/yellow]")
            continue

        # ── /build: plan.md 파이프라인 실행 ──

        elif cmd == "/build":
            console.print("[yellow]/build 명령어는 더 이상 지원되지 않습니다.[/yellow]")
            continue

        # ── /analysis: ALIVE 분석 워크플로우 ──

        elif cmd == "/analysis":
            console.print("[yellow]/analysis 명령어는 더 이상 지원되지 않습니다.[/yellow]")
            continue

        elif cmd and cmd.startswith("/"):
            console.print(f"[dim]알 수 없는 명령어: {cmd}  (/help 참고)[/dim]")
            continue

        # ── 일반 자연어 질문 → Core Agent ──

        if agent is None:
            console.print("[red]Agent가 초기화되지 않았습니다.[/red]")
            continue

        # SQL 실행 전 사용자 확인 콜백
        async def _confirm_sql(sql: str) -> bool:
            console.print()
            console.print("[bold yellow]⚡ SQL 실행 확인[/bold yellow]")
            console.print(f"[dim]```sql\n{sql}\n```[/dim]")
            try:
                ans = await session.prompt_async("  실행하시겠습니까? (엔터/y=실행, n=취소): ")
                return ans.strip().lower() not in ("n", "no", "아니", "취소")
            except (KeyboardInterrupt, EOFError):
                return False

        agent.confirm_callback = _confirm_sql
        console.print("[dim]  분석 중...[/dim]")
        try:
            answer = await agent.run(user_input)
        except Exception as e:
            answer = f"오류가 발생했습니다: {e}"
        finally:
            agent.confirm_callback = None

        console.print()
        console.print(answer)


def main():
    try:
        asyncio.run(repl())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
