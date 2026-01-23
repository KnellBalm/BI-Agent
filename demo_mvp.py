"""
Interactive Demo Script for Tableau Meta JSON MVP
Showcases the complete "Natural Language to Tableau Meta JSON" pipeline with TUI
"""
import asyncio
import time
from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from backend.agents.bi_tool.meta_generator import TableauMetaGenerator
from backend.agents.bi_tool.nl_intent_parser import ChartIntent
from backend.orchestrator.tui_meta_preview import TUI_MetaPreview
from backend.orchestrator.interaction_ui import InteractionUI

class MVPDemo:
    def __init__(self):
        self.console = Console()
        self.generator = TableauMetaGenerator()
        self.preview = TUI_MetaPreview()
        self.ui = InteractionUI()

    def show_welcome(self):
        """환영 메시지"""
        welcome_text = """
[bold cyan]Tableau Meta JSON Generator MVP[/bold cyan]
[yellow]"자연어 질문 → Tableau 메타데이터 생성"[/yellow]

[dim]Powered by:[/dim]
• Natural Language Intent Parser (Claude's T2)
• Tableau Meta JSON Schema (Claude's T1)
• RAG Knowledge Base (Antigravity's T3)
• Meta Generation Pipeline (Antigravity's T5)
• Premium TUI v2 (Antigravity's T6)
"""
        self.console.print(Panel(welcome_text, border_style="cyan", expand=False))
        time.sleep(2)

    async def run_demo_scenario(self, scenario_name: str, user_input: str, intent: ChartIntent):
        """개별 데모 시나리오 실행"""
        self.console.clear()
        
        # 1. 시나리오 소개
        self.console.print(f"\n[bold magenta]Demo Scenario: {scenario_name}[/bold magenta]")
        self.console.print(f"[cyan]사용자 입력:[/cyan] \"{user_input}\"")
        self.console.print("[dim]\nProcessing...[/dim]")
        time.sleep(1)

        # 2. Intent Parsing 결과
        self.console.print("\n[yellow]Step 1: Natural Language Intent Parsing[/yellow]")
        self.console.print(f"  └ Chart Type: [green]{intent.visual_type}[/green]")
        self.console.print(f"  └ Dimensions: [blue]{', '.join(intent.dimensions)}[/blue]")
        self.console.print(f"  └ Measures: [blue]{', '.join(intent.measures)}[/blue]")
        time.sleep(1.5)

        # 3. RAG Context Retrieval
        self.console.print("\n[yellow]Step 2: RAG Knowledge Base Search[/yellow]")
        context = self.generator.rag.search_context(user_input)
        self.console.print(f"  └ Retrieved {len(context)} characters of context")
        self.console.print(f"  └ Optimizing schema for [cyan]{intent.visual_type}[/cyan] chart")
        time.sleep(1.5)

        # 4. Meta JSON Generation
        self.console.print("\n[yellow]Step 3: Tableau Meta JSON Generation[/yellow]")
        meta = self.generator._build_meta_from_intent(intent)
        self.console.print(f"  └ Generated worksheet: [green]{meta.worksheets[0].name}[/green]")
        self.console.print(f"  └ Datasource: [blue]{meta.datasources[0].name}[/blue]")
        time.sleep(1.5)

        # 5. TUI Preview
        self.console.print("\n[yellow]Step 4: TUI Meta Preview[/yellow]")
        preview_layout = self.preview.render_preview(meta.to_dict())
        
        with Live(preview_layout, refresh_per_second=4):
            time.sleep(3)

        # 6. Save
        filename = f"demo_{scenario_name.replace(' ', '_')}.json"
        save_msg = self.preview.save_json(meta.to_dict(), filename)
        self.console.print(f"\n{save_msg}")
        
        self.console.print("\n[dim]Press Enter to continue...[/dim]")
        input()

    async def run(self):
        """전체 데모 실행"""
        self.show_welcome()

        demos = [
            {
                "name": "Monthly Sales Trend",
                "input": "월별 매출 추이를 보여주는 라인 차트를 만들어줘",
                "intent": ChartIntent(
                    action="create",
                    visual_type="line",
                    datasource="sales_data",
                    dimensions=["Month"],
                    measures=["Sales"],
                    filters=[],
                    title="Monthly Sales Trend",
                    aggregation="SUM"
                )
            },
            {
                "name": "Category Comparison",
                "input": "카테고리별 수익을 막대 그래프로 비교해줘",
                "intent": ChartIntent(
                    action="create",
                    visual_type="bar",
                    datasource="products",
                    dimensions=["Category"],
                    measures=["Profit"],
                    filters=[],
                    title="Profit by Category",
                    aggregation="SUM"
                )
            }
        ]

        for demo in demos:
            await self.run_demo_scenario(demo["name"], demo["input"], demo["intent"])

        # 최종 메시지
        self.console.clear()
        self.console.print(Panel(
            "[bold green]Demo Complete![/bold green]\n\n"
            "모든 생성된 JSON 파일은 [cyan]backend/data/outputs/[/cyan]에 저장되었습니다.\n"
            "TUI 프리뷰를 통해 각 Meta JSON의 구조를 확인했습니다.",
            border_style="green",
            expand=False
        ))

if __name__ == "__main__":
    demo = MVPDemo()
    asyncio.run(demo.run())
