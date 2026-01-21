#!/usr/bin/env python3
"""
BI-Agent TUI (Terminal User Interface)
rich 라이브러리를 사용한 인터랙티브 터미널 인터페이스
"""

import asyncio
import os
import sys
from typing import Optional

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.live import Live
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn

# 환경 변수 로드
load_dotenv()

# 경로 설정
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from orchestrator.connection_manager import ConnectionManager

console = Console()

def show_welcome():
    """환영 메시지 표시"""
    welcome_text = """
# 🚀 BI-Agent TUI

자연어로 데이터베이스를 조회하고 BI 대시보드를 수정하세요.

## 명령어
- `query <질문>`: 데이터베이스 조회 (예: query 이번 달 매출 보여줘)
- `connections`: 등록된 연결 목록 보기
- `use <id>`: 연결 선택 (예: use test_pg)
- `help`: 도움말 표시
- `exit`: 종료
"""
    console.print(Panel(Markdown(welcome_text), title="[bold blue]Welcome[/bold blue]", border_style="blue"))

def show_connections(conn_manager: ConnectionManager):
    """등록된 연결 목록 표시"""
    connections = conn_manager.list_connections()
    
    if not connections:
        console.print("[yellow]등록된 연결이 없습니다.[/yellow]")
        return
    
    table = Table(title="📦 등록된 데이터 연결")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Type", style="magenta")
    table.add_column("Server Path", style="green")
    
    for conn in connections:
        server_path = conn.get("server_path", "N/A")
        if server_path and len(server_path) > 40:
            server_path = "..." + server_path[-37:]
        table.add_row(
            conn.get("id", "unknown"),
            conn.get("type", "unknown"),
            server_path
        )
    
    console.print(table)

async def run_query_with_progress(query: str, conn_id: Optional[str] = None):
    """쿼리 실행 (프로그레스 표시)"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("[cyan]쿼리 실행 중...", total=None)
        
        # 실제 쿼리 실행 로직 (LLM 필요 - 현재 스텁)
        await asyncio.sleep(1)  # 시뮬레이션
        
        progress.update(task, description="[green]완료!")
        
    # 결과 표시 (스텁)
    console.print(Panel(
        "[yellow]⚠️ LLM API 키가 필요합니다. GEMINI_API_KEY를 .env에 설정하세요.[/yellow]",
        title="Query Result",
        border_style="yellow"
    ))

async def main_loop():
    """메인 이벤트 루프"""
    conn_manager = ConnectionManager()
    current_conn: Optional[str] = None
    
    show_welcome()
    
    while True:
        try:
            # 프롬프트 표시
            prompt_text = f"[bold green]bi-agent[/bold green]"
            if current_conn:
                prompt_text += f" [dim]({current_conn})[/dim]"
            prompt_text += " > "
            
            user_input = Prompt.ask(prompt_text)
            
            if not user_input.strip():
                continue
            
            parts = user_input.strip().split(maxsplit=1)
            command = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            
            if command == "exit" or command == "quit":
                console.print("[dim]👋 안녕히 가세요![/dim]")
                break
            
            elif command == "help":
                show_welcome()
            
            elif command == "connections":
                show_connections(conn_manager)
            
            elif command == "use":
                if not args:
                    console.print("[red]사용법: use <connection_id>[/red]")
                else:
                    conn = conn_manager.get_connection(args)
                    if conn:
                        current_conn = args
                        console.print(f"[green]✓ '{args}' 연결 선택됨[/green]")
                    else:
                        console.print(f"[red]연결 '{args}'을(를) 찾을 수 없습니다.[/red]")
            
            elif command == "query":
                if not args:
                    console.print("[red]사용법: query <자연어 질문>[/red]")
                else:
                    await run_query_with_progress(args, current_conn)
            
            else:
                # 명령어가 아니면 쿼리로 처리
                await run_query_with_progress(user_input, current_conn)
                
        except KeyboardInterrupt:
            console.print("\n[dim]Ctrl+C 입력됨. 'exit'로 종료하세요.[/dim]")
        except Exception as e:
            console.print(f"[red]오류: {e}[/red]")

def main():
    """엔트리포인트"""
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        console.print("\n[dim]종료됨[/dim]")

if __name__ == "__main__":
    main()
