"""
Command Router — Slash command definitions and autocomplete for the CLI REPL.
"""
from typing import Dict, Tuple

# Command registry: name -> (description, requires_tui)
COMMANDS: Dict[str, Tuple[str, bool]] = {
    "/help":    ("도움말 표시", False),
    "/list":    ("연결된 데이터 소스 목록", False),
    "/connect": ("데이터 소스 연결", False),
    "/explore": ("DB 스키마 탐색기", False),
    "/history": ("대화 히스토리 목록", False),
    "/clear":   ("화면 초기화", False),
    "/quit":    ("종료", False),
    "/init":    ("현재 디렉토리에 plan.md 템플릿 생성", False),
    "/build":   ("plan.md 분석 파이프라인 실행", False),
    "/edit":    ("plan.md 마크다운 에디터", False),
    "/export":  ("결과물 내보내기 [html/streamlit/pdf]", False),
    "/analysis-new":     ("새 ALIVE 분석 생성 <제목>", False),
    "/analysis-quick":   ("퀵 단일파일 분석 생성 <제목>", False),
    "/analysis-status":  ("현재 분석 상태 확인", False),
    "/analysis-list":    ("모든 분석 목록 보기", False),
    "/analysis-run":     ("현재 스테이지 BI-EXEC 실행", False),
    "/analysis-next":    ("다음 스테이지로 전환", False),
    "/analysis-archive": ("현재 분석 아카이브", False),
}

COMMAND_NAMES = list(COMMANDS.keys())

HELP_TEXT = """
[bold]사용 가능한 명령어[/bold]

  [cyan]/help[/cyan]           이 도움말 표시
  [cyan]/connect[/cyan]        데이터 소스 연결 (TUI 팝업)
  [cyan]/explore[/cyan]        DB 스키마 탐색기 (TUI 팝업)
  [cyan]/list[/cyan]           연결된 데이터 소스 목록
  [cyan]/history[/cyan]        대화 히스토리 목록
  [cyan]/clear[/cyan]          화면 초기화
  [cyan]/quit[/cyan], [cyan]/exit[/cyan]   종료

[bold]AaC (Analysis as Code)[/bold]

  [cyan]/init[/cyan]           현재 디렉토리에 plan.md 템플릿 생성
  [cyan]/edit[/cyan]           plan.md 마크다운 에디터 열기 (TUI)
  [cyan]/build[/cyan]          plan.md 분석 파이프라인 실행
  [cyan]/export [fmt][/cyan]   결과물 내보내기 (html/streamlit/pdf)

[bold]블록 참조[/bold]

  [cyan]@N[/cyan]              블록 N 재출력 (예: @1, @2)

[bold]자연어 질문 예시[/bold]

  > 월별 매출 트렌드를 분석해줘
  > 가장 많이 팔린 상품 TOP 10은?
  > 지역별 매출을 비교해줘
"""


def is_block_ref(text: str) -> int:
    """
    Returns block index if text is a @N reference, else 0.
    e.g. '@1' -> 1, '@2' -> 2, 'hello' -> 0
    """
    t = text.strip()
    if t.startswith("@") and t[1:].isdigit():
        return int(t[1:])
    return 0
