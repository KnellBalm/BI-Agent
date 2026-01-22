import asyncio
import os
import warnings
import logging
from dotenv import load_dotenv
from typing import Dict, Any

# 라이브러리 경고 메시지 숨기기
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# 로깅 설정: 시스템 로그는 파일로, 사용자에게는 간결하게
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='backend/data/system.log',
    filemode='a'
)
# 콘솔에는 로그가 직접 나오지 않도록 조정
logger = logging.getLogger()
for handler in logger.handlers:
    if not isinstance(handler, logging.FileHandler):
        logger.removeHandler(handler)

# .env 파일 로드
load_dotenv()

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.prompt import Prompt
from rich.text import Text
from rich.progress import SpinnerColumn, Progress, TextColumn

from backend.orchestrator.orchestrator import Orchestrator
from backend.orchestrator.quota_manager import QuotaManager
from backend.orchestrator.connection_manager import ConnectionManager
from backend.orchestrator.llm_provider import GeminiProvider, OllamaProvider, FailoverLLMProvider
from backend.agents.data_source.data_source_agent import DataSourceAgent
from backend.agents.bi_tool.bi_tool_agent import BIToolAgent
from backend.agents.bi_tool.json_parser import BIJsonParser

console = Console()

async def interactive_loop():
    console.clear()
    console.print(Panel.fit(
        "[bold cyan]BI Agent Professional Workspace[/bold cyan]\n"
        "[dim]Terminal User Interface (TUI) powered by Rich[/dim]",
        border_style="bright_blue"
    ))
    
    console.print("[yellow]팁: '데이터베이스 목록' 또는 '새 연결 등록' 등으로 연결 관리 가능[/yellow]")
    
    # 설정 로드
    quota_manager = QuotaManager()
    project_id = os.getenv("GCP_PROJECT_ID")
    if project_id and project_id != "your-project-id":
        with console.status("[bold green]GCP 할당량 동기화 중..."):
            await quota_manager.sync_with_gcp(project_id)
    
    # LLM Provider 설정 (Failover: Gemini -> Ollama)
    gemini = GeminiProvider(quota_manager=quota_manager)
    ollama = OllamaProvider()
    llm = FailoverLLMProvider(primary=gemini, secondary=ollama)
    
    conn_manager = ConnectionManager()
    data_agent = DataSourceAgent()
    bi_json_path = os.getenv("BI_JSON_PATH", "backend/data/bi_solution.json")
    parser = BIJsonParser(bi_json_path)
    bi_agent = BIToolAgent(parser=parser)
    orchestrator = Orchestrator(llm=llm, data_agent=data_agent, bi_agent=bi_agent, connection_manager=conn_manager)
    
    # 기본 연결 등록 (최초 실행 시)
    if not conn_manager.get_connection("test_pg"):
        test_connection_info = {
            "type": "postgres",
            "server_path": os.path.abspath("backend/mcp_servers/postgres_server.js"),
            "config": {
                "DB_HOST": "localhost", "DB_PORT": "5432", "DB_NAME": "postgres", "DB_USER": "postgres"
            }
        }
        conn_manager.register_connection("test_pg", test_connection_info)
    
    context = {}

    while True:
        try:
            user_input = Prompt.ask("\n[bold green]➜[/bold green] [white]어떤 작업을 도와드릴까요?[/white]")
            if user_input.lower() in ['exit', 'quit', '종료']:
                console.print("[bold red]프로그램을 종료합니다.[/bold red]")
                break
            
            if not user_input.strip():
                continue
                
            with console.status("[bold yellow]에이전트가 사고하는 중... (Chain of Thought)", spinner="dots"):
                result = await orchestrator.run(user_input, context=context)
            
            # 사고 과정 시각화 (Mockup for now, could be integrated into Orchestrator)
            # console.print(Panel(Text("사고 과정: ...", style="dim"), title="CoT", border_style="dim"))
            
            # 최종 응답 출력
            response_text = result.get('final_response', result.get('bi_result', '결과가 없습니다.'))
            console.print(Panel(Text(response_text), title="[bold cyan]Agent Response[/bold cyan]", border_style="cyan"))
            
            # 데이터 결과가 있는 경우 표로 출력
            if "data_result" in result and result["data_result"]:
                import pandas as pd
                df = pd.DataFrame(result["data_result"])
                if not df.empty:
                    table = Table(title="[bold blue]Data View[/bold blue]", show_header=True, header_style="bold magenta")
                    for col in df.columns:
                        table.add_column(col)
                    for _, row in df.head(10).iterrows(): # 최대 10개만
                        table.add_row(*[str(v) for v in row.values])
                    console.print(table)
                    if len(df) > 10:
                        console.print(f"[dim]... and {len(df)-10} more rows[/dim]")

        except KeyboardInterrupt:
            console.print("\n[bold red]Interrupted. 종료합니다.[/bold red]")
            break
        except Exception as e:
            console.print(Panel(f"[bold red]Error:[/bold red] {str(e)}", title="System Error", border_style="red"))

    # 리소스 정리
    await data_agent.close_all()
    await quota_manager.close()

if __name__ == "__main__":
    if not os.path.exists("backend/data"):
        os.makedirs("backend/data")
    
    # bi_solution.json이 없는 경우 샘플 생성
    bi_json_path = "backend/data/bi_solution.json"
    if not os.path.exists(bi_json_path):
        import json
        sample_bi = {
            "datamodel": [],
            "report": []
        }
        with open(bi_json_path, "w", encoding="utf-8") as f:
            json.dump(sample_bi, f, indent=4)
            
    asyncio.run(interactive_loop())
