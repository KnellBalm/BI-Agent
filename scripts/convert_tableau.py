#!/usr/bin/env python3
"""
Interactive Tableau to Meta JSON Converter
사용자와 대화하며 Tableau 파일을 Meta JSON으로 변환합니다
"""
import sys
import os
from pathlib import Path

# PYTHONPATH 설정
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.syntax import Syntax
    from rich.table import Table
    from rich import print as rprint
except ImportError:
    print("❌ 'rich' 라이브러리가 필요합니다.")
    print("다음 명령어로 설치해주세요:")
    print("  python3 -m pip install rich")
    sys.exit(1)

import json
from backend.agents.bi_tool.tableau_meta_schema import TableauMetaSchemaEngine
from backend.orchestrator.tui_meta_preview import TUI_MetaPreview

console = Console()

def show_welcome():
    """환영 메시지"""
    console.print(Panel.fit(
        "[bold cyan]🎨 Tableau → Meta JSON 변환기[/bold cyan]\n\n"
        "[yellow]실제 Tableau 파일을 분석하고 Meta JSON으로 변환합니다[/yellow]\n"
        "[dim]Claude & Antigravity가 만든 MVP 시스템[/dim]",
        border_style="cyan"
    ))
    console.print()

def find_tableau_files():
    """사용 가능한 Tableau 파일 찾기"""
    search_paths = ["tmp", "/tmp", "."]
    found_files = []
    
    for path in search_paths:
        if not os.path.exists(path):
            continue
        for file in Path(path).glob("*.twb*"):
            found_files.append(str(file))
    
    return found_files

def select_file():
    """파일 선택"""
    console.print("[bold yellow]📁 Tableau 파일 검색 중...[/bold yellow]")
    files = find_tableau_files()
    
    if not files:
        console.print("[red]❌ Tableau 파일을 찾을 수 없습니다.[/red]")
        console.print("\n다음 위치에 .twb 또는 .twbx 파일을 배치해주세요:")
        console.print("  • tmp/your_file.twb")
        console.print("  • /tmp/your_file.twbx")
        return None
    
    console.print(f"\n[green]✓[/green] {len(files)}개의 파일을 발견했습니다:\n")
    
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("#", style="cyan", width=4)
    table.add_column("파일명", style="white")
    table.add_column("크기", style="dim", justify="right")
    
    for i, file in enumerate(files, 1):
        size = os.path.getsize(file)
        size_str = f"{size:,} bytes" if size < 1024*1024 else f"{size/(1024*1024):.2f} MB"
        table.add_row(str(i), file, size_str)
    
    console.print(table)
    
    choice = Prompt.ask(
        "\n변환할 파일 번호를 선택하세요",
        choices=[str(i) for i in range(1, len(files)+1)],
        default="1"
    )
    
    return files[int(choice)-1]

def extract_twb_from_twbx(twbx_path):
    """TWBX에서 TWB 추출"""
    import zipfile
    import tempfile
    
    with console.status("[yellow]TWBX 파일 압축 해제 중...[/yellow]"):
        with zipfile.ZipFile(twbx_path, 'r') as zip_ref:
            twb_files = [f for f in zip_ref.namelist() if f.endswith('.twb')]
            if not twb_files:
                raise ValueError("TWBX 안에 .twb 파일이 없습니다")
            
            temp_dir = tempfile.mkdtemp()
            zip_ref.extract(twb_files[0], temp_dir)
            return os.path.join(temp_dir, twb_files[0])

def parse_tableau_file(file_path):
    """Tableau 파일 파싱"""
    console.print(f"\n[bold yellow]🔍 파일 분석 중...[/bold yellow]")
    console.print(f"[dim]파일: {file_path}[/dim]\n")
    
    actual_twb = file_path
    if file_path.endswith('.twbx'):
        actual_twb = extract_twb_from_twbx(file_path)
        console.print("[green]✓[/green] TWB 추출 완료\n")
    
    with console.status("[yellow]Tableau 메타데이터 파싱 중...[/yellow]"):
        engine = TableauMetaSchemaEngine(actual_twb)
        meta = engine.to_meta_json()
    
    console.print("[green]✓[/green] 파싱 완료!\n")
    return meta

def show_summary(meta):
    """요약 정보 표시"""
    console.print("[bold yellow]📊 워크북 요약[/bold yellow]\n")
    
    table = Table(show_header=False, box=None)
    table.add_column("항목", style="cyan", width=20)
    table.add_column("값", style="bold white")
    
    table.add_row("📌 버전", meta.version)
    table.add_row("🔧 도구", meta.tool.upper())
    table.add_row("💾 데이터소스", f"{len(meta.datasources)}개")
    table.add_row("📄 워크시트", f"{len(meta.worksheets)}개")
    table.add_row("🧮 계산 필드", f"{len(meta.calculated_fields)}개")
    
    if meta.datasources:
        ds = meta.datasources[0]
        table.add_row("", "")
        table.add_row("📂 첫 데이터소스", ds.name)
        table.add_row("  ↳ 필드 수", f"{len(ds.fields)}개")
        table.add_row("  ↳ 연결 타입", ds.connection.type)
    
    if meta.worksheets:
        ws = meta.worksheets[0]
        table.add_row("", "")
        table.add_row("📈 첫 워크시트", ws.name)
        table.add_row("  ↳ 차트 타입", ws.visual_type.upper())
        table.add_row("  ↳ 차원", f"{len(ws.dimensions)}개")
        table.add_row("  ↳ 측정값", f"{len(ws.measures)}개")
    
    console.print(table)
    console.print()

def preview_json(meta):
    """JSON 미리보기"""
    if not Confirm.ask("\n[cyan]Meta JSON을 미리보시겠습니까?[/cyan]", default=True):
        return
    
    console.print("\n[bold yellow]📝 Meta JSON 미리보기[/bold yellow]\n")
    
    json_str = meta.to_json()
    lines = json_str.split('\n')
    
    # 처음 40줄만 표시
    preview_lines = lines[:40]
    if len(lines) > 40:
        preview_lines.append("  ...")
        preview_lines.append(f"  (총 {len(lines)}줄 중 40줄 표시)")
    
    syntax = Syntax('\n'.join(preview_lines), "json", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, border_style="yellow"))
    console.print()

def save_json(meta):
    """JSON 파일 저장"""
    if not Confirm.ask("\n[cyan]Meta JSON을 파일로 저장하시겠습니까?[/cyan]", default=True):
        return None
    
    default_name = "tableau_converted.json"
    filename = Prompt.ask(
        "저장할 파일명을 입력하세요",
        default=default_name
    )
    
    output_path = f"backend/data/outputs/{filename}"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with console.status("[yellow]파일 저장 중...[/yellow]"):
        meta.save(output_path)
    
    console.print(f"\n[green]✓[/green] 저장 완료: [cyan]{output_path}[/cyan]")
    return output_path

def main():
    """메인 대화형 프로세스"""
    show_welcome()
    
    try:
        # 1. 파일 선택
        file_path = select_file()
        if not file_path:
            return
        
        if not Confirm.ask(f"\n[cyan]'{os.path.basename(file_path)}'를 변환하시겠습니까?[/cyan]", default=True):
            console.print("[yellow]취소되었습니다.[/yellow]")
            return
        
        # 2. 파싱
        meta = parse_tableau_file(file_path)
        
        # 3. 요약 표시
        show_summary(meta)
        
        # 4. JSON 미리보기
        preview_json(meta)
        
        # 5. 저장
        saved_path = save_json(meta)
        
        # 6. 완료
        console.print("\n" + "="*60)
        console.print(Panel.fit(
            "[bold green]✨ 변환 완료![/bold green]\n\n"
            f"[cyan]Tableau 파일:[/cyan] {os.path.basename(file_path)}\n"
            f"[cyan]Meta JSON:[/cyan] {saved_path if saved_path else '(저장 안 함)'}",
            border_style="green"
        ))
        
    except KeyboardInterrupt:
        console.print("\n\n[yellow]사용자가 중단했습니다.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ 오류 발생:[/red] {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")

if __name__ == "__main__":
    main()
