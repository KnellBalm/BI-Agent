"""
Real Tableau File to Meta JSON Converter Demo
실제 Tableau 파일(.twb/.twbx)을 Meta JSON으로 변환하는 실전 데모
"""
import sys
import os
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
import json

# PYTHONPATH 설정
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.agents.bi_tool.tableau_meta_schema import TableauMetaSchemaEngine, twb_to_meta_json
from backend.orchestrator.tui_meta_preview import TUI_MetaPreview

def find_tableau_file():
    """Tableau 파일 찾기"""
    possible_paths = [
        "/tmp/tableau_test.twbx",
        "tmp/tableau_test.twbx",
        "/tmp/test.twb",
        "tmp/test.twb"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None

def extract_twb_from_twbx(twbx_path):
    """TWBX 파일에서 TWB 추출 (TWBX는 압축 파일)"""
    import zipfile
    import tempfile
    
    with zipfile.ZipFile(twbx_path, 'r') as zip_ref:
        # TWBX 안의 .twb 파일 찾기
        twb_files = [f for f in zip_ref.namelist() if f.endswith('.twb')]
        if not twb_files:
            raise ValueError("TWBX 파일 안에 .twb 파일을 찾을 수 없습니다")
        
        # 임시 디렉토리에 추출
        temp_dir = tempfile.mkdtemp()
        zip_ref.extract(twb_files[0], temp_dir)
        return os.path.join(temp_dir, twb_files[0])

def main():
    console = Console()
    
    console.print(Panel.fit(
        "[bold cyan]Real Tableau File → Meta JSON Converter[/bold cyan]\n"
        "[yellow]실제 Tableau 파일을 우리의 Meta JSON 형식으로 변환합니다[/yellow]",
        border_style="cyan"
    ))
    
    # 1. Tableau 파일 찾기
    console.print("\n[yellow]Step 1:[/yellow] Tableau 파일 검색 중...")
    tableau_file = find_tableau_file()
    
    if not tableau_file:
        console.print("[red]Error:[/red] Tableau 파일을 찾을 수 없습니다.")
        console.print("다음 경로에 파일을 배치해주세요:")
        console.print("  - /tmp/tableau_test.twbx")
        console.print("  - tmp/test.twb")
        return
    
    console.print(f"[green]✓[/green] 파일 발견: [cyan]{tableau_file}[/cyan]")
    
    # 2. TWBX인 경우 TWB 추출
    actual_twb = tableau_file
    if tableau_file.endswith('.twbx'):
        console.print("\n[yellow]Step 2:[/yellow] TWBX 파일에서 TWB 추출 중...")
        try:
            actual_twb = extract_twb_from_twbx(tableau_file)
            console.print(f"[green]✓[/green] TWB 추출 완료: [dim]{actual_twb}[/dim]")
        except Exception as e:
            console.print(f"[red]Error:[/red] TWB 추출 실패: {e}")
            return
    
    # 3. Tableau Meta JSON으로 변환
    console.print(f"\n[yellow]Step 3:[/yellow] Tableau 파일 파싱 및 Meta JSON 변환 중...")
    try:
        engine = TableauMetaSchemaEngine(actual_twb)
        meta = engine.to_meta_json()
        console.print("[green]✓[/green] Meta JSON 변환 완료!")
        
        # 요약 정보 표시
        summary_table = Table(title="Tableau Workbook Summary", border_style="cyan")
        summary_table.add_column("항목", style="cyan")
        summary_table.add_column("내용", style="bold white")
        
        summary_table.add_row("버전", meta.version)
        summary_table.add_row("도구", meta.tool)
        summary_table.add_row("데이터소스 수", str(len(meta.datasources)))
        summary_table.add_row("워크시트 수", str(len(meta.worksheets)))
        summary_table.add_row("계산 필드 수", str(len(meta.calculated_fields)))
        
        if meta.datasources:
            summary_table.add_row("첫 번째 데이터소스", meta.datasources[0].name)
            summary_table.add_row("필드 수", str(len(meta.datasources[0].fields)))
        
        if meta.worksheets:
            summary_table.add_row("첫 번째 워크시트", meta.worksheets[0].name)
            summary_table.add_row("차트 유형", meta.worksheets[0].visual_type)
        
        console.print("\n")
        console.print(summary_table)
        
    except Exception as e:
        console.print(f"[red]Error:[/red] 파싱 실패: {e}")
        import traceback
        console.print(traceback.format_exc())
        return
    
    # 4. TUI 프리뷰
    console.print(f"\n[yellow]Step 4:[/yellow] Meta JSON 프리뷰")
    try:
        preview = TUI_MetaPreview()
        
        # JSON 미리보기 (처음 30줄만)
        json_str = meta.to_json()
        lines = json_str.split('\n')[:30]
        preview_json = '\n'.join(lines)
        if len(json_str.split('\n')) > 30:
            preview_json += "\n  ... (생략)"
        
        syntax = Syntax(preview_json, "json", theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title="[bold yellow]Generated Meta JSON (Preview)[/bold yellow]", border_style="yellow"))
        
    except Exception as e:
        console.print(f"[red]Warning:[/red] 프리뷰 생성 실패: {e}")
    
    # 5. 파일 저장
    console.print(f"\n[yellow]Step 5:[/yellow] Meta JSON 파일 저장 중...")
    output_path = "backend/data/outputs/real_tableau_converted.json"
    try:
        meta.save(output_path)
        console.print(f"[green]✓[/green] 저장 완료: [cyan]{output_path}[/cyan]")
    except Exception as e:
        console.print(f"[red]Error:[/red] 저장 실패: {e}")
    
    console.print("\n[bold green]변환 완료![/bold green]")
    console.print(f"생성된 Meta JSON 파일을 확인하세요: {output_path}")

if __name__ == "__main__":
    main()
