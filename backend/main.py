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
from backend.orchestrator.interaction_ui import InteractionUI
from backend.orchestrator.dashboard_view import DashboardView

console = Console()

async def interactive_loop():
    # 초기화
    ui = InteractionUI()
    dashboard = DashboardView(console=console)
    quota_manager = QuotaManager()
    conn_manager = ConnectionManager()
    data_agent = DataSourceAgent()
    
    # 설정 로드
    project_id = os.getenv("GCP_PROJECT_ID")
    if project_id and project_id != "your-project-id":
        with console.status("[bold green]GCP 할당량 동기화 중..."):
            await quota_manager.sync_with_gcp(project_id)
    
    # LLM Provider 설정
    gemini = GeminiProvider(quota_manager=quota_manager)
    ollama = OllamaProvider()
    llm = FailoverLLMProvider(primary=gemini, secondary=ollama)
    
    bi_json_path = os.getenv("BI_JSON_PATH", "backend/data/bi_solution.json")
    parser = BIJsonParser(bi_json_path)
    bi_agent = BIToolAgent(parser=parser)
    orchestrator = Orchestrator(llm=llm, data_agent=data_agent, bi_agent=bi_agent, connection_manager=conn_manager)
    
    # 기본 연결 등록
    if not conn_manager.get_connection("test_pg"):
        test_connection_info = {
            "type": "postgres",
            "server_path": os.path.abspath("backend/mcp_servers/postgres_server.js"),
            "config": {
                "DB_HOST": "localhost", "DB_PORT": "5432", "DB_NAME": "postgres", "DB_USER": "postgres"
            }
        }
        conn_manager.register_connection("test_pg", test_connection_info)
    
    # 시스템 정보 수집 함수
    def get_system_snapshot():
        conns = conn_manager.list_connections()
        return {
            "llm_type": f"Failover ({llm.primary.__class__.__name__})",
            "db_connection": "Connected" if conns else "No Connections",
            "quota": quota_manager.get_status_summary() if hasattr(quota_manager, 'get_status_summary') else "Sync Enabled"
        }

    # '대문(Front Door)' 출력
    dashboard.draw(get_system_snapshot())
    
    context = {}

    while True:
        try:
            user_input = Prompt.ask("\n[bold green]➜[/bold green] [white]질문을 입력하거나 슬래시(/) 명령어를 사용하세요[/white]")
            
            if not user_input.strip():
                continue

            # 슬래시 명령어 처리
            if user_input.startswith("/"):
                cmd = user_input.lower().split()[0]
                if cmd in ["/exit", "/quit", "/종료"]:
                    console.print("[bold red]프로그램을 종료합니다. Bye![/bold red]")
                    break
                elif cmd == "/clear":
                    dashboard.draw(get_system_snapshot())
                    continue
                elif cmd == "/help":
                    console.print(dashboard.render_tips())
                    continue
                elif cmd == "/list":
                    conns = conn_manager.list_connections()
                    table = Table(title="Connection List", box=box.ROUNDED)
                    table.add_column("ID", style="cyan")
                    table.add_column("Type", style="green")
                    for c in conns:
                        table.add_row(c['id'], c['type'])
                    console.print(table)
                    continue
                # 기타 명령어는 orchestrator가 처리하도록 하되, 힌트 제공 가능

            # 일반 질문 처리
            ui.add_log(f"User Request: {user_input}")
            ui.show_announcement("에이전트가 분석 중입니다...")
            
            with console.status("[bold yellow]사고 과정 (Chain of Thought)...", spinner="bouncingBar"):
                result = await orchestrator.run(user_input, context=context)
            
            # 최종 응답 출력 (Gemini 스타일 박스 요약)
            response_text = result.get('final_response', result.get('bi_result', '결과가 없습니다.'))
            ui.show_final_response(response_text)
            
            # 데이터 결과 시각화
            if "data_result" in result and result["data_result"]:
                table = ui.create_data_table(result["data_result"])
                console.print(table)
            
            ui.add_log("Task completed successfully.", level="SUCCESS")

        except KeyboardInterrupt:
            console.print("\n[bold red]Interrupted. 종료합니다.[/bold red]")
            break
        except Exception as e:
            ui.add_log(f"Error: {str(e)}", level="ERROR")
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
        sample_bi = {"datamodel": [], "report": []}
        with open(bi_json_path, "w", encoding="utf-8") as f:
            json.dump(sample_bi, f, indent=4)
            
    asyncio.run(interactive_loop())
