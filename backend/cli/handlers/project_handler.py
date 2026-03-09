"""
/project 핸들러 — 프로젝트(워크스페이스) 관리.

프로젝트 = CWD 아래의 .bi-project/ 디렉터리.
하위에 plan.md, explore/, reports/, data/ 구조를 갖는다.
"""
import os
import json
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich import box


console = Console()

PROJECT_ROOT_NAME = ".bi-project"
PROJECT_META_FILE = "project.json"

# ──────────────────────────────────────────────
# 기본 프로젝트 디렉터리 구조
# ──────────────────────────────────────────────

TEMPLATE_DIRS = ["explore", "reports", "data"]

PLAN_TEMPLATE = """# {title}

> 생성일: {date}

## 1. 분석 목적


## 2. 데이터 소스


## 3. 분석 방법


## 4. 기대 결과

"""


def _project_dir() -> Path:
    """현재 작업 디렉터리의 .bi-project/ 경로."""
    return Path.cwd() / PROJECT_ROOT_NAME


def _meta_path() -> Path:
    return _project_dir() / PROJECT_META_FILE


def _load_meta() -> dict | None:
    mp = _meta_path()
    if mp.exists():
        with open(mp, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _save_meta(meta: dict):
    mp = _meta_path()
    with open(mp, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)


async def handle_project(user_input: str):
    """
    /project new <이름>   — 프로젝트 생성
    /project list         — 프로젝트 파일 목록
    /project status       — 현재 프로젝트 상태
    """
    parts = user_input.split(maxsplit=2)
    sub = parts[1] if len(parts) > 1 else "status"
    arg = parts[2] if len(parts) > 2 else ""

    if sub == "new":
        _project_new(arg)
    elif sub == "list":
        _project_list()
    elif sub == "status":
        _project_status()
    else:
        console.print(f"[dim]알 수 없는 서브커맨드: {sub}  /project (new|list|status)[/dim]")


def _project_new(name: str):
    if not name:
        console.print("[yellow]사용법: /project new <프로젝트 이름>[/yellow]")
        return

    proj_dir = _project_dir()
    if proj_dir.exists():
        console.print(f"[yellow]이미 프로젝트가 존재합니다: {proj_dir}[/yellow]")
        return

    # 디렉터리 생성
    proj_dir.mkdir(parents=True)
    for d in TEMPLATE_DIRS:
        (proj_dir / d).mkdir()

    # plan.md 생성
    plan_content = PLAN_TEMPLATE.format(
        title=name,
        date=datetime.now().strftime("%Y-%m-%d"),
    )
    (proj_dir / "plan.md").write_text(plan_content, encoding="utf-8")

    # 메타 정보
    meta = {
        "name": name,
        "created": datetime.now().isoformat(),
        "cwd": str(Path.cwd()),
    }
    _save_meta(meta)

    console.print(f"[green]✓ 프로젝트 생성됨:[/green] [bold]{name}[/bold]")
    console.print(f"  경로: [dim]{proj_dir}[/dim]")
    console.print(f"  [dim]plan.md 가 생성되었습니다. 편집 후 분석을 시작하세요.[/dim]")


def _project_list():
    proj_dir = _project_dir()
    if not proj_dir.exists():
        console.print("[yellow]프로젝트가 없습니다. /project new <이름> 으로 생성하세요.[/yellow]")
        return

    console.print(f"[bold cyan]◈ 프로젝트 구조[/bold cyan]  [dim]{proj_dir}[/dim]\n")
    for child in sorted(proj_dir.iterdir()):
        if child.name.startswith("."):
            continue
        if child.is_dir():
            files = list(child.iterdir())
            console.print(f"  📁 {child.name}/  [dim]({len(files)} files)[/dim]")
            for f in sorted(files)[:5]:
                console.print(f"      [dim]{f.name}[/dim]")
        else:
            size = child.stat().st_size
            console.print(f"  📄 {child.name}  [dim]({size:,} bytes)[/dim]")


def _project_status():
    meta = _load_meta()
    if not meta:
        console.print("[yellow]프로젝트가 없습니다. /project new <이름> 으로 생성하세요.[/yellow]")
        return

    proj_dir = _project_dir()
    reports = list((proj_dir / "reports").glob("*.md")) if (proj_dir / "reports").exists() else []
    explores = list((proj_dir / "explore").glob("*")) if (proj_dir / "explore").exists() else []

    console.print(f"[bold cyan]◈ 프로젝트 상태[/bold cyan]")
    console.print(f"  이름: [bold]{meta['name']}[/bold]")
    console.print(f"  생성: [dim]{meta.get('created', '?')[:10]}[/dim]")
    console.print(f"  리포트: [cyan]{len(reports)}[/cyan] 개")
    console.print(f"  탐색 기록: [cyan]{len(explores)}[/cyan] 개")
    console.print(f"  경로: [dim]{proj_dir}[/dim]")
