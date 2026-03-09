"""
BI-Agent CLI v3 — prompt_toolkit full-screen TUI Application.

고정 헤더 + 스크롤 출력 + 고정 입력창을 가진 3-panel 대시보드 레이아웃.
"""
import asyncio
import os
import sys
import shutil
import warnings
import logging
from io import StringIO

from dotenv import load_dotenv

warnings.filterwarnings("ignore")

_root = logging.getLogger()
_root.setLevel(logging.CRITICAL)
for _h in _root.handlers[:]:
    _root.removeHandler(_h)
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

from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.layout import Layout, HSplit, Window, FormattedTextControl, BufferControl, FloatContainer, Float
from prompt_toolkit.layout.dimension import Dimension as D
from prompt_toolkit.layout.processors import BeforeInput
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.history import FileHistory
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.styles import Style as PTStyle

from backend.cli.layout import build_header_text
from backend.cli.commands import SlashCompleter

HISTORY_FILE = os.path.expanduser("~/.bi-agent/repl_history")
os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)

HELP_TEXT = """\
── 기본 명령어 (System) ──
 /help             도움말 표시
 /status           현재 에이전트 상태 상세 확인
 /quit  /exit      종료
 /clear            출력 영역 정리

── 데이터 연결 (Data) ──
 /connect <type> <path>    데이터 소스 연결 (sqlite, excel, pg)
 /list                     연결된 데이터 소스 목록

── 데이터 탐색 (Explore) ──
 /explore schema [table]   테이블 목록 또는 상세 구조
 /explore query <SQL>      SQL 쿼리 실행
 /explore preview <table>  상위 10행 미리보기

── 프로젝트 관리 (Project) ──
 /project new <이름>       새 프로젝트 생성
 /project list             프로젝트 파일 구조 표시
 /project status           현재 프로젝트 상태

── 리포트 관리 (Report) ──
 /report new <제목>        새 마크다운 리포트 생성
 /report list              리포트 목록
 /report show <이름>       리포트 내용 표시
 /report edit <이름>       $EDITOR로 열기
 /report append <이름> <내용>  리포트에 섹션 추가

── 설정 관리 (Setting) ──
 /setting                  현재 설정 표시
 /setting set <키> <값>    설정값 변경
 /setting login <provider> OAuth 로그인

── AI 분석 ──
 /thinking <아이디어>      마크다운 분석 계획 자동 생성
 /run <plan.md 경로>       마크다운 계획 실행
 /expert <질문>            LangChain Expert 딥 분석

── ALIVE 분석 플로우 ──
 /analysis new <제목>      새 분석 세션 생성
 /analysis run             BI-EXEC 블록 실행
 /analysis next            다음 스테이지로 이동
 /analysis status          분석 상태 확인
 /analysis list            분석 세션 목록

── 자연어 질문 ──
 / 없이 평문으로 질문하면 AI가 자동 응답합니다.
"""


# ──────────────────────────────────────────────
# 상태 수집 유틸
# ──────────────────────────────────────────────

def _get_status_info() -> dict:
    """CLI 상태 정보 수집."""
    status = {"model": "?", "auth": "미설정", "db": "연결 없음", "cwd": os.getcwd()}
    try:
        from backend.utils.setting_manager import setting_manager
        model = setting_manager.get("model")
        if model and model != "(미설정)":
            status["model"] = model
    except Exception:
        pass
    try:
        from backend.orchestrator.managers.auth_manager import auth_manager
        st = auth_manager.get_status()
        if st.get("oauth_valid"):
            status["auth"] = "OAuth"
        elif st.get("api_key_set"):
            status["auth"] = "API Key"
    except Exception:
        pass
    try:
        from backend.orchestrator.managers.connection_manager import ConnectionManager
        cm = ConnectionManager()
        conns = cm.list_connections()
        if conns:
            last = conns[-1]
            name = last.get("name", last.get("id", "?"))
            ctype = last.get("type", "?")
            status["db"] = f"{name} ({ctype})"
    except Exception:
        pass
    return status


def _get_conn_context() -> dict | None:
    """현재 연결 정보를 context dict로 반환."""
    try:
        from backend.orchestrator.managers.connection_manager import ConnectionManager
        cm = ConnectionManager()
        conns = cm.list_connections()
        if conns:
            return {"connection_id": conns[-1].get("id")}
    except Exception:
        pass
    return None


def _render_rich(*args, **kwargs) -> str:
    """rich Console 출력을 plain text 문자열로 캡처한다."""
    buf = StringIO()
    cols = shutil.get_terminal_size().columns
    temp = Console(file=buf, highlight=False, width=cols, no_color=True)
    temp.print(*args, **kwargs)
    return buf.getvalue()


# ──────────────────────────────────────────────
# 메인 TUI 클래스
# ──────────────────────────────────────────────

class BIAgentTUI:
    """prompt_toolkit full-screen 3-panel TUI."""

    def __init__(self):
        self.agent = None
        self._init_agent()

        # ── Buffers ──
        self.output_buffer = Buffer(name="output", read_only=True)
        self.input_buffer = Buffer(
            name="input",
            completer=SlashCompleter(),
            history=FileHistory(HISTORY_FILE),
            multiline=False,
            complete_while_typing=True,
        )

        # ── Header ──
        info = _get_status_info()
        self._header_text = build_header_text(
            model=info["model"], auth=info["auth"],
            db=info["db"], cwd=info.get("cwd", ""),
        )

        self.header_control = FormattedTextControl(
            lambda: ANSI(self._header_text)
        )

        # ── Key Bindings ──
        kb = KeyBindings()

        @kb.add("enter")
        def handle_enter(event):
            text = self.input_buffer.text.strip()
            if not text:
                return
            self.input_buffer.reset()
            self._append(f"❯ {text}\n")
            asyncio.ensure_future(self._process(text))

        @kb.add("c-c")
        def handle_ctrl_c(event):
            self._append("\n(Ctrl+C — /quit 으로 종료)\n")

        @kb.add("c-d")
        def handle_ctrl_d(event):
            event.app.exit()

        @kb.add("tab")
        def handle_tab(event):
            b = event.app.current_buffer
            if b.name != "input":
                return
            if b.text.startswith("/"):
                if b.complete_state:
                    cc = b.complete_state.current_completion
                    if cc is None:
                        b.complete_next()
                        cc = b.complete_state and b.complete_state.current_completion
                    if cc:
                        b.apply_completion(cc)
                        b.insert_text(" ")
                else:
                    b.start_completion(select_first=True)
            else:
                b.insert_text("    ")

        # ── Layout ──
        body = HSplit([
            # 고정 헤더 (4줄)
            Window(
                self.header_control,
                height=D.exact(4),
                style="",
            ),
            # 구분선
            Window(height=1, char="─", style="class:separator"),
            # 스크롤 출력 영역 (나머지 공간 전부 차지)
            Window(
                BufferControl(buffer=self.output_buffer),
                wrap_lines=True,
            ),
            # 구분선
            Window(height=1, char="─", style="class:separator"),
            # 고정 입력창 (1줄)
            Window(
                BufferControl(
                    buffer=self.input_buffer,
                    input_processors=[BeforeInput("❯ ")],
                ),
                height=D.exact(1),
            ),
        ])

        # FloatContainer로 감싸서 자동완성 팝업 메뉴가 오버레이로 표시되도록 함
        self.layout = Layout(
            FloatContainer(
                content=body,
                floats=[
                    Float(
                        xcursor=True,
                        ycursor=True,
                        content=CompletionsMenu(max_height=12, scroll_offset=1),
                    ),
                ],
            ),
            focused_element=self.input_buffer,
        )

        self.style = PTStyle.from_dict({
            "separator": "#555555",
        })

        self.app = Application(
            layout=self.layout,
            key_bindings=kb,
            style=self.style,
            full_screen=True,
            mouse_support=False,
        )

    def _init_agent(self):
        try:
            from backend.core.core_agent import CoreAgent
            self.agent = CoreAgent()
        except Exception:
            pass

    # ── 출력 헬퍼 ──

    def _append(self, text: str):
        """출력 영역에 텍스트를 추가하고 스크롤을 맨 아래로 이동한다."""
        old = self.output_buffer.text
        new_text = old + text if old else text
        self.output_buffer.set_document(
            Document(new_text, len(new_text)),
            bypass_readonly=True,
        )
        if hasattr(self, "app"):
            self.app.invalidate()

    def _refresh_header(self):
        """헤더 상태 정보를 갱신한다."""
        info = _get_status_info()
        self._header_text = build_header_text(
            model=info["model"], auth=info["auth"],
            db=info["db"], cwd=info.get("cwd", ""),
        )
        if hasattr(self, "app"):
            self.app.invalidate()

    # ── 명령어 처리 ──

    async def _process(self, text: str):
        """사용자 입력을 비동기적으로 처리한다."""
        cmd = text.lower().split()[0] if text.startswith("/") else None
        ctx = _get_conn_context()

        try:
            if cmd in ("/quit", "/exit"):
                self._append("  ⎿  Bye!\n")
                await asyncio.sleep(0.2)
                self.app.exit()
                return

            elif cmd == "/clear":
                self.output_buffer.set_document(
                    Document("", 0), bypass_readonly=True,
                )
                self._refresh_header()
                return

            elif cmd == "/help":
                self._append(HELP_TEXT + "\n")
                return

            elif cmd == "/status":
                info = _get_status_info()
                lines = [
                    "\n◈ BI-Agent 현재 상태",
                    f"  모델: {info['model']} (인증: {info['auth']})",
                    f"  데이터: {info['db']}",
                    f"  경로: {info.get('cwd', '')}",
                ]
                try:
                    from backend.cli.handlers.project_handler import _load_meta, _project_dir
                    p_meta = _load_meta()
                    if p_meta:
                        lines.append(f"  프로젝트: {p_meta['name']} ({_project_dir()})")
                    else:
                        lines.append("  프로젝트: 활성 프로젝트 없음")
                except Exception:
                    pass
                try:
                    from backend.aac.analysis_manager import AnalysisManager
                    am = AnalysisManager()
                    active = am.get_active()
                    if active:
                        lines.append(f"  진행중인 분석: {active.title} (Stage: {active.status.value})")
                    else:
                        lines.append("  진행중인 분석: 없음")
                except Exception:
                    pass
                self._append("\n".join(lines) + "\n\n")
                return

            elif cmd == "/explore":
                result = await self._run_handler("explore", text, context=ctx)
                self._append(result)
                return

            elif cmd == "/project":
                result = await self._run_handler("project", text)
                self._append(result)
                return

            elif cmd == "/report":
                result = await self._run_handler("report", text)
                self._append(result)
                return

            elif cmd == "/list":
                try:
                    from backend.utils.path_config import path_manager
                    import json
                    registry_path = path_manager.get_project_path("default") / "connections.json"
                    with open(registry_path) as f:
                        reg = json.load(f)
                    if reg:
                        lines = []
                        for cid, cinfo in reg.items():
                            lines.append(f"  {cid} | {cinfo.get('name', cid)} | {cinfo.get('type', '?')}")
                        self._append("\n".join(lines) + "\n")
                    else:
                        self._append("연결된 데이터 소스가 없습니다.\n")
                except Exception as e:
                    self._append(f"오류: {e}\n")
                return

            elif cmd == "/connect":
                parts = text.split(maxsplit=2)
                if len(parts) < 3:
                    self._append(
                        "── 데이터 소스 연결 ──\n"
                        "  /connect sqlite  <파일 경로>\n"
                        "  /connect excel   <파일 경로>\n"
                        "  /connect pg      <연결 문자열>\n"
                    )
                else:
                    conn_type = parts[1].lower()
                    conn_path = parts[2]
                    try:
                        from backend.orchestrator.managers.connection_manager import ConnectionManager
                        cm = ConnectionManager()
                        type_map = {"sqlite": "sqlite", "excel": "excel", "pg": "postgresql", "postgresql": "postgresql"}
                        resolved = type_map.get(conn_type)
                        if not resolved:
                            self._append("지원 타입: sqlite, excel, pg\n")
                        else:
                            conn_id = os.path.splitext(os.path.basename(conn_path))[0]
                            config = {"path": os.path.abspath(conn_path), "name": conn_id}
                            cm.register_connection(conn_id, resolved, config)
                            self._append(f"✓ '{conn_id}' ({resolved}) 연결 등록 완료\n")
                            self._refresh_header()
                    except Exception as e:
                        self._append(f"연결 오류: {e}\n")
                return

            elif cmd == "/setting":
                parts = text.split(maxsplit=3)
                sub = parts[1] if len(parts) > 1 else "list"
                try:
                    from backend.utils.setting_manager import setting_manager, SETTING_KEYS
                    if sub in ("list", "/setting"):
                        settings = setting_manager.get_all()
                        lines = ["⚙ 현재 설정"]
                        for k, v in settings.items():
                            desc = SETTING_KEYS.get(k, "")
                            lines.append(f"  {k:<15} {v:<20} {desc}")
                        self._append("\n".join(lines) + "\n")
                    elif sub == "login":
                        provider = parts[2] if len(parts) > 2 else "gemini"
                        valid = ["gemini", "claude", "openai"]
                        if provider not in valid:
                            self._append(f"지원 프로바이더: {', '.join(valid)}\n")
                        else:
                            from backend.orchestrator.managers.auth_manager import auth_manager
                            self._append(f"  {provider} 로그인을 시도합니다...\n")
                            self.app.invalidate()
                            success, msg = await auth_manager.login_provider(provider)
                            self._append(f"{'✓' if success else '✗'} {msg}\n")
                            self._refresh_header()
                    elif sub == "set":
                        if len(parts) < 4:
                            self._append(f"사용법: /setting set <키> <값>\n  지원 키: {', '.join(SETTING_KEYS.keys())}\n")
                        else:
                            key, value = parts[2], parts[3]
                            result = setting_manager.set(key, value)
                            self._append(f"✓ {result}\n")
                            self._refresh_header()
                    elif sub == "help":
                        lines = ["── 설정 도움말 ──"]
                        for k, desc in SETTING_KEYS.items():
                            lines.append(f"  {k:<15} {desc}")
                        self._append("\n".join(lines) + "\n")
                    else:
                        self._append(f"알 수 없는 서브커맨드: {sub}\n")
                except Exception as e:
                    self._append(f"✗ 오류: {e}\n")
                return

            elif cmd == "/thinking":
                idea = text[len("/thinking"):].strip()
                if not idea:
                    self._append("사용법: /thinking <분석 아이디어>\n")
                elif self.agent:
                    self._append("  생각 중...\n")
                    self.app.invalidate()
                    result = await self.agent.thinking(idea)
                    self._append(str(result) + "\n")
                return

            elif cmd == "/run":
                md_path = text[len("/run"):].strip()
                if not md_path:
                    self._append("사용법: /run <plan.md 경로>\n")
                else:
                    try:
                        from backend.aac.plan_parser import PlanParser
                        parser = PlanParser()
                        plan = parser.parse(md_path)
                        self._append(f"▶ PLAN 실행: {plan.get('title', md_path)}\n")
                        self.app.invalidate()
                        if self.agent:
                            result = await self.agent.run(
                                f"다음 분석 계획을 실행하세요:\n\n{open(md_path).read()}",
                                context=ctx,
                            )
                            self._append(str(result) + "\n")
                    except Exception as e:
                        self._append(f"✗ 오류: {e}\n")
                return

            elif cmd == "/expert":
                question = text[len("/expert"):].strip()
                if not question:
                    self._append("사용법: /expert <분석 질문>\n")
                elif self.agent:
                    self._append("  전문가 분석 중...\n")
                    self.app.invalidate()
                    result = await self.agent.run(question, context=ctx)
                    self._append(str(result) + "\n")
                return

            elif cmd == "/analysis":
                parts = text.split(maxsplit=2)
                sub = parts[1] if len(parts) > 1 else "status"
                arg = parts[2] if len(parts) > 2 else ""
                try:
                    from backend.aac.analysis_manager import AnalysisManager
                    mgr = AnalysisManager()
                    if sub == "new":
                        if not arg:
                            self._append("사용법: /analysis new <분석 제목>\n")
                        else:
                            project = mgr.create_analysis(title=arg, connection="")
                            self._append(f"✓ ALIVE 분석 생성됨: {project.title}\n  경로: {project.path}\n")
                    elif sub == "status":
                        project = mgr.get_active()
                        if project:
                            self._append(f"◈ 분석 상태  {project.title}\n  스테이지: {project.status.value.upper()}\n")
                        else:
                            self._append("활성 분석 없음. /analysis new <제목>\n")
                    elif sub == "list":
                        for p in mgr.list_analyses():
                            self._append(f"  {p.title} ({p.status.value})\n")
                    elif sub == "run":
                        from backend.aac.stage_executor import StageExecutor
                        project = mgr.get_active()
                        if project:
                            executor = StageExecutor()
                            stage_file = project.current_stage_file()
                            count = executor.count_bi_exec_blocks(stage_file)
                            self._append("  실행 중...\n")
                            self.app.invalidate()
                            executor.execute_stage(stage_file)
                            self._append(f"✓ 완료  블록 수: {count}\n")
                    elif sub == "next":
                        project = mgr.get_active()
                        if project:
                            mgr.advance_stage(project)
                            self._append("✓ 다음 스테이지로 이동\n")
                    elif sub == "archive":
                        project = mgr.get_active()
                        if project:
                            mgr.archive(project)
                            self._append("✓ 아카이브됨\n")
                    else:
                        self._append(f"알 수 없는 서브커맨드: {sub}\n")
                except Exception as e:
                    self._append(f"✗ 오류: {e}\n")
                return

            elif cmd and cmd.startswith("/"):
                self._append(f"알 수 없는 명령어: {cmd}  (/help 참고)\n")
                return

            # ── 자연어 질문 → Core Agent ──
            if self.agent is None:
                self._append("Agent가 초기화되지 않았습니다.\n")
                return

            self._append("  분석 중...\n")
            self.app.invalidate()
            answer = await self.agent.run(text, context=ctx)
            self._append(str(answer) + "\n")

        except Exception as e:
            self._append(f"✗ 오류: {e}\n")

    async def _run_handler(self, handler_name: str, text: str, **kwargs) -> str:
        """핸들러를 실행하고 출력을 캡처한다."""
        buf = StringIO()
        cols = shutil.get_terminal_size().columns
        temp_console = Console(file=buf, highlight=False, width=cols, no_color=True)

        # 핸들러 모듈의 console을 임시 교체
        if handler_name == "explore":
            import backend.cli.handlers.explore_handler as mod
            from backend.cli.handlers.explore_handler import handle_explore as handler
        elif handler_name == "project":
            import backend.cli.handlers.project_handler as mod
            from backend.cli.handlers.project_handler import handle_project as handler
        elif handler_name == "report":
            import backend.cli.handlers.report_handler as mod
            from backend.cli.handlers.report_handler import handle_report as handler
        else:
            return f"알 수 없는 핸들러: {handler_name}\n"

        old_console = getattr(mod, "console", None)
        mod.console = temp_console
        try:
            await handler(text, **kwargs) if "context" in kwargs else await handler(text)
        except Exception as e:
            buf.write(f"✗ 오류: {e}\n")
        finally:
            if old_console is not None:
                mod.console = old_console

        return buf.getvalue()

    async def run(self):
        """TUI 애플리케이션을 실행한다."""
        await self.app.run_async()


async def run():
    """진입점 (async)."""
    tui = BIAgentTUI()
    await tui.run()


def main():
    """동기 진입점."""
    asyncio.run(run())
