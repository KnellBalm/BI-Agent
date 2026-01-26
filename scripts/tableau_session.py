#!/usr/bin/env python3
"""
Tableau Meta JSON Converter - Interactive Session
계속 유지되는 대화형 세션으로 여러 작업을 연속으로 수행합니다
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.syntax import Syntax
    from rich.table import Table
    from rich.layout import Layout
    from rich.text import Text
except ImportError:
    print("❌ 'rich' 라이브러리가 필요합니다.")
    print("설치: python3 -m pip install rich")
    sys.exit(1)

import json
from backend.agents.bi_tool.tableau_meta_schema import TableauMetaSchemaEngine
from backend.orchestrator.tui_meta_preview import TUI_MetaPreview
from backend.agents.data_source.profiler import DataProfiler
from backend.orchestrator.analysis_view import AnalysisView

console = Console()

class TableauConverterSession:
    """대화형 세션 관리"""
    
    def __init__(self):
        self.converted_files = []
        self.current_meta = None
        self.running = True
    
    def show_header(self):
        """헤더 표시"""
        console.clear()
        console.print(Panel.fit(
            "[bold cyan]🎨 Tableau Meta JSON Converter[/bold cyan]\n"
            "[yellow]대화형 세션 모드[/yellow] - 'quit' 또는 'exit'로 종료",
            border_style="cyan"
        ))
        console.print()
    
    def show_menu(self):
        """메인 메뉴 표시"""
        console.print("\n[bold yellow]📋 메뉴[/bold yellow]")
        console.print("  [cyan]1.[/cyan] Tableau 파일 변환")
        console.print("  [cyan]2.[/cyan] 마지막 변환 결과 다시 보기")
        console.print("  [cyan]3.[/cyan] 변환 이력 보기")
        console.print("  [cyan]4.[/cyan] [bold magenta]데이터 프로파일링 (NEW!)[/bold magenta]")
        console.print("  [cyan]5.[/cyan] 도움말")
        console.print("  [cyan]q.[/cyan] 종료")
        console.print()

    def find_data_files(self):
        """데이터 파일(CSV, Excel) 검색"""
        search_paths = ["tmp", "/tmp", "."]
        found_files = []
        extensions = ["*.csv", "*.xlsx", "*.xls"]
        
        for path in search_paths:
            if not os.path.exists(path):
                continue
            for ext in extensions:
                for file in Path(path).glob(ext):
                    found_files.append(str(file))
        
        return found_files
    
    def find_tableau_files(self):
        """Tableau 파일 검색"""
        search_paths = ["tmp", "/tmp", "."]
        found_files = []
        
        for path in search_paths:
            if not os.path.exists(path):
                continue
            for file in Path(path).glob("*.twb*"):
                found_files.append(str(file))
        
        return found_files
    
    def select_file(self):
        """파일 선택"""
        console.print("\n[yellow]📁 파일 검색 중...[/yellow]")
        files = self.find_tableau_files()
        
        if not files:
            console.print("[red]❌ Tableau 파일을 찾을 수 없습니다.[/red]")
            console.print("tmp/ 폴더에 .twb 또는 .twbx 파일을 배치해주세요.")
            return None
        
        console.print(f"\n[green]✓[/green] {len(files)}개 발견\n")
        
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("#", style="cyan", width=4)
        table.add_column("파일명", style="white")
        table.add_column("크기", style="dim", justify="right")
        
        for i, file in enumerate(files, 1):
            size = os.path.getsize(file)
            size_str = f"{size:,}B" if size < 1024 else f"{size/1024:.1f}KB"
            if size >= 1024*1024:
                size_str = f"{size/(1024*1024):.2f}MB"
            table.add_row(str(i), os.path.basename(file), size_str)
        
        console.print(table)
        
        choice = Prompt.ask(
            "\n변환할 파일 번호",
            choices=[str(i) for i in range(1, len(files)+1)] + ['c'],
            default="c"
        )
        
        if choice == 'c':
            return None
        
        return files[int(choice)-1]
    
    def convert_file(self, file_path):
        """파일 변환"""
        console.print(f"\n[yellow]🔄 변환 중: {os.path.basename(file_path)}[/yellow]")
        
        try:
            # TWBX 압축 해제
            actual_twb = file_path
            if file_path.endswith('.twbx'):
                import zipfile, tempfile
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    twb_files = [f for f in zip_ref.namelist() if f.endswith('.twb')]
                    temp_dir = tempfile.mkdtemp()
                    zip_ref.extract(twb_files[0], temp_dir)
                    actual_twb = os.path.join(temp_dir, twb_files[0])
            
            # 파싱
            with console.status("[yellow]파싱 중...[/yellow]"):
                engine = TableauMetaSchemaEngine(actual_twb)
                self.current_meta = engine.to_meta_json()
            
            console.print("[green]✓[/green] 변환 완료!\n")
            
            # 요약 표시
            self.show_summary(self.current_meta)
            
            # 저장
            if Confirm.ask("\n파일로 저장하시겠습니까?", default=True):
                filename = Prompt.ask("파일명", default="tableau_converted.json")
                output_path = f"backend/data/outputs/{filename}"
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                self.current_meta.save(output_path)
                console.print(f"\n[green]✓[/green] 저장: [cyan]{output_path}[/cyan]")
                
                self.converted_files.append({
                    'source': file_path,
                    'output': output_path,
                    'worksheets': len(self.current_meta.worksheets)
                })
            
        except Exception as e:
            console.print(f"\n[red]❌ 오류:[/red] {e}")

    def run_profiling(self):
        """데이터 프로파일링 실행"""
        console.print("\n[bold magenta]🔍 데이터 프로파일링 세션[/bold magenta]")
        files = self.find_data_files()
        
        if not files:
            console.print("[red]❌ 데이터 파일(CSV, Excel)을 찾을 수 없습니다.[/red]")
            return

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="magenta", width=4)
        table.add_column("파일명", style="white")
        table.add_column("타입", style="dim")
        
        for i, file in enumerate(files, 1):
            table.add_row(str(i), os.path.basename(file), os.path.splitext(file)[1].upper())
        
        console.print(table)
        
        choice = Prompt.ask("\n프로파일링할 파일 번호 (취소: c)", default="c")
        if choice == 'c': return

        file_path = files[int(choice)-1]
        
        try:
            with console.status(f"[magenta]{os.path.basename(file_path)} 분석 중...[/magenta]"):
                profiler = DataProfiler()
                profiler.load_file(file_path)
                report = profiler.profile()
            
            view = AnalysisView(console=console)
            view.render_full_report(report)
            
        except Exception as e:
            console.print(f"\n[red]❌ 프로파일링 오류:[/red] {e}")
    
    def show_summary(self, meta):
        """요약 정보"""
        table = Table(title="📊 워크북 정보", show_header=False, box=None)
        table.add_column("", style="cyan", width=18)
        table.add_column("", style="bold white")
        
        table.add_row("데이터소스", f"{len(meta.datasources)}개")
        table.add_row("워크시트", f"{len(meta.worksheets)}개")
        table.add_row("계산 필드", f"{len(meta.calculated_fields)}개")
        
        if meta.worksheets:
            table.add_row("", "")
            for i, ws in enumerate(meta.worksheets[:3], 1):
                table.add_row(f"워크시트 #{i}", f"{ws.name} ({ws.visual_type})")
        
        console.print(table)
    
    def show_last_result(self):
        """마지막 결과 다시 보기"""
        if not self.current_meta:
            console.print("[yellow]변환된 파일이 없습니다.[/yellow]")
            return
        
        console.print("\n[bold yellow]📄 마지막 변환 결과[/bold yellow]\n")
        self.show_summary(self.current_meta)
        
        if Confirm.ask("\nJSON 미리보기를 보시겠습니까?", default=False):
            json_str = self.current_meta.to_json()
            lines = json_str.split('\n')[:40]
            syntax = Syntax('\n'.join(lines), "json", theme="monokai", line_numbers=True)
            console.print(Panel(syntax, border_style="yellow"))
    
    def show_history(self):
        """변환 이력"""
        if not self.converted_files:
            console.print("[yellow]변환 이력이 없습니다.[/yellow]")
            return
        
        console.print("\n[bold yellow]📜 변환 이력[/bold yellow]\n")
        
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("#", style="cyan", width=4)
        table.add_column("원본 파일", style="white")
        table.add_column("출력 파일", style="dim")
        table.add_column("워크시트", style="green", justify="center")
        
        for i, item in enumerate(self.converted_files, 1):
            table.add_row(
                str(i),
                os.path.basename(item['source']),
                os.path.basename(item['output']),
                f"{item['worksheets']}개"
            )
        
        console.print(table)
    
    def show_help(self):
        """도움말"""
        console.print("\n[bold yellow]📖 도움말[/bold yellow]\n")
        console.print("[cyan]이 도구는:[/cyan]")
        console.print("  • Tableau .twb/.twbx 파일을 분석합니다")
        console.print("  • 표준 Meta JSON 형식으로 변환합니다")
        console.print("  • 데이터소스, 워크시트, 계산 필드 정보를 추출합니다")
        console.print()
        console.print("[cyan]변환된 JSON 활용:[/cyan]")
        console.print("  • BI 도구 간 메타데이터 마이그레이션")
        console.print("  • 워크북 분석 및 문서화")
        console.print("  • 자동화된 리포트 생성")
        console.print()
        console.print("[cyan]파일 위치:[/cyan]")
        console.print("  • 입력: tmp/ 또는 /tmp/ 폴더")
        console.print("  • 출력: backend/data/outputs/ 폴더")
    
    def run(self):
        """메인 루프"""
        self.show_header()
        console.print("[green]세션을 시작합니다. 'quit'로 종료하세요.[/green]\n")
        
        while self.running:
            try:
                self.show_menu()
                
                choice = Prompt.ask(
                    "선택",
                    choices=['1', '2', '3', '4', '5', 'q', 'quit', 'exit'],
                    default='1'
                ).lower()
                
                if choice in ['q', 'quit', 'exit']:
                    console.print("\n[yellow]세션을 종료합니다. 안녕히 가세요! 👋[/yellow]")
                    break
                
                elif choice == '1':
                    file_path = self.select_file()
                    if file_path:
                        self.convert_file(file_path)
                
                elif choice == '2':
                    self.show_last_result()
                
                elif choice == '3':
                    self.show_history()
                
                elif choice == '4':
                    self.run_profiling()
                
                elif choice == '5':
                    self.show_help()
                
                input("\n[dim]Press Enter to continue...[/dim]")
                self.show_header()
                
            except KeyboardInterrupt:
                console.print("\n\n[yellow]Ctrl+C를 눌러 종료합니다.[/yellow]")
                break
            except Exception as e:
                console.print(f"\n[red]오류:[/red] {e}")
                input("\n[dim]Press Enter to continue...[/dim]")

def main():
    session = TableauConverterSession()
    session.run()

if __name__ == "__main__":
    main()
