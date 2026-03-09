"""
/explore 핸들러 — 데이터 탐색 (스키마, 쿼리, 프리뷰).

기존 core/tools.py의 analyze_schema, query_database를
CLI에서 직접 호출하는 래퍼.
"""
from rich.console import Console
from rich.table import Table
from rich import box


console = Console()


async def handle_explore(user_input: str, context: dict | None = None):
    """
    /explore schema [table]  — 테이블 목록 또는 특정 테이블 상세
    /explore query <SQL>     — SELECT 쿼리 실행
    /explore preview <table> — 상위 10행 미리보기
    """
    parts = user_input.split(maxsplit=2)
    sub = parts[1] if len(parts) > 1 else "schema"
    arg = parts[2] if len(parts) > 2 else ""

    if sub == "schema":
        _explore_schema(arg, context)

    elif sub == "query":
        if not arg:
            console.print("[yellow]사용법: /explore query <SQL SELECT 문>[/yellow]")
        else:
            _explore_query(arg, context)

    elif sub == "preview":
        if not arg:
            console.print("[yellow]사용법: /explore preview <테이블명>[/yellow]")
        else:
            _explore_query(f"SELECT * FROM {arg} LIMIT 10", context)

    else:
        console.print(f"[dim]알 수 없는 서브커맨드: {sub}  /explore (schema|query|preview)[/dim]")


def _explore_schema(table_name: str, context: dict | None):
    """analyze_schema 도구를 직접 호출하여 결과를 출력한다."""
    try:
        from backend.core.tools import analyze_schema
        result = analyze_schema(table_name=table_name, context=context)
        console.print(result)
    except Exception as e:
        console.print(f"[red]✗ 스키마 조회 오류: {e}[/red]")


def _explore_query(sql: str, context: dict | None):
    """query_database 도구를 직접 호출하여 결과를 출력한다."""
    try:
        from backend.core.tools import query_database
        result = query_database(sql_query=sql, context=context)
        console.print(result)
    except Exception as e:
        console.print(f"[red]✗ 쿼리 실행 오류: {e}[/red]")
