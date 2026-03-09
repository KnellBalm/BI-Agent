"""
/report 핸들러 — 마크다운 리포트 CRUD.

현재 프로젝트(.bi-project/reports/) 내의 마크다운 파일을 관리한다.
"""
import os
import subprocess
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown


console = Console()

PROJECT_ROOT = ".bi-project"

REPORT_TEMPLATE = """# {title}

> 생성일: {date}
> 프로젝트: {project}

---

## 요약


## 분석 결과


## 결론 및 액션

"""


def _reports_dir() -> Path:
    d = Path.cwd() / PROJECT_ROOT / "reports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _find_report(name: str) -> Path | None:
    """이름(확장자 포함/미포함)으로 리포트 파일을 찾는다."""
    d = _reports_dir()
    # 정확한 파일명 매칭
    exact = d / name
    if exact.exists():
        return exact
    # .md 확장자 자동 추가
    with_ext = d / f"{name}.md"
    if with_ext.exists():
        return with_ext
    # 부분 매칭
    for f in d.glob("*.md"):
        if name.lower() in f.stem.lower():
            return f
    return None


async def handle_report(user_input: str):
    """
    /report new <제목>       — 새 리포트 생성
    /report list             — 리포트 목록
    /report show <이름>      — 리포트 출력
    /report edit <이름>      — $EDITOR로 열기
    /report append <이름> <내용> — 리포트에 내용 추가
    """
    parts = user_input.split(maxsplit=2)
    sub = parts[1] if len(parts) > 1 else "list"
    arg = parts[2] if len(parts) > 2 else ""

    if sub == "new":
        _report_new(arg)
    elif sub == "list":
        _report_list()
    elif sub == "show":
        _report_show(arg)
    elif sub == "edit":
        _report_edit(arg)
    elif sub == "append":
        _report_append(arg)
    else:
        console.print(f"[dim]알 수 없는 서브커맨드: {sub}  /report (new|list|show|edit|append)[/dim]")


def _report_new(title: str):
    if not title:
        console.print("[yellow]사용법: /report new <리포트 제목>[/yellow]")
        return

    # 파일명 생성 (공백 → 하이픈)
    slug = title.replace(" ", "-").lower()
    filepath = _reports_dir() / f"{slug}.md"

    if filepath.exists():
        console.print(f"[yellow]이미 존재하는 리포트: {filepath.name}[/yellow]")
        return

    # 프로젝트명 가져오기
    import json
    meta_path = Path.cwd() / PROJECT_ROOT / "project.json"
    project_name = "?"
    if meta_path.exists():
        with open(meta_path, "r") as f:
            project_name = json.load(f).get("name", "?")

    content = REPORT_TEMPLATE.format(
        title=title,
        date=datetime.now().strftime("%Y-%m-%d"),
        project=project_name,
    )
    filepath.write_text(content, encoding="utf-8")
    console.print(f"[green]✓ 리포트 생성됨:[/green] [bold]{title}[/bold]")
    console.print(f"  경로: [dim]{filepath}[/dim]")
    console.print(f"  [dim]/report edit {slug} 또는 에디터에서 직접 편집하세요.[/dim]")


def _report_list():
    reports = sorted(_reports_dir().glob("*.md"))
    if not reports:
        console.print("[yellow]리포트가 없습니다. /report new <제목> 으로 생성하세요.[/yellow]")
        return

    console.print(f"[bold cyan]◈ 리포트 목록[/bold cyan]  [dim]({len(reports)}개)[/dim]\n")
    for r in reports:
        size = r.stat().st_size
        mtime = datetime.fromtimestamp(r.stat().st_mtime).strftime("%m-%d %H:%M")
        console.print(f"  📄 [bold]{r.stem}[/bold]  [dim]{size:,}B · {mtime}[/dim]")


def _report_show(name: str):
    if not name:
        console.print("[yellow]사용법: /report show <리포트 이름>[/yellow]")
        return

    path = _find_report(name)
    if not path:
        console.print(f"[yellow]리포트를 찾을 수 없습니다: {name}[/yellow]")
        return

    content = path.read_text(encoding="utf-8")
    console.print(Markdown(content))


def _report_edit(name: str):
    if not name:
        console.print("[yellow]사용법: /report edit <리포트 이름>[/yellow]")
        return

    path = _find_report(name)
    if not path:
        console.print(f"[yellow]리포트를 찾을 수 없습니다: {name}[/yellow]")
        return

    editor = os.environ.get("EDITOR", "vi")
    try:
        subprocess.run([editor, str(path)])
    except Exception as e:
        console.print(f"[red]에디터 실행 오류: {e}[/red]")
        console.print(f"  [dim]직접 열기: {path}[/dim]")


def _report_append(raw_arg: str):
    if not raw_arg:
        console.print("[yellow]사용법: /report append <리포트이름> <추가할 내용>[/yellow]")
        return

    # 첫 토큰 = 리포트 이름, 나머지 = 내용
    tokens = raw_arg.split(maxsplit=1)
    name = tokens[0]
    content = tokens[1] if len(tokens) > 1 else ""

    if not content:
        console.print("[yellow]추가할 내용을 입력하세요.[/yellow]")
        return

    path = _find_report(name)
    if not path:
        console.print(f"[yellow]리포트를 찾을 수 없습니다: {name}[/yellow]")
        return

    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n\n{content}\n")

    console.print(f"[green]✓ 리포트에 추가됨:[/green] [bold]{path.stem}[/bold]")
