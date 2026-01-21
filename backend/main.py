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

from backend.orchestrator.orchestrator import Orchestrator
from backend.orchestrator.quota_manager import QuotaManager
from backend.orchestrator.connection_manager import ConnectionManager
from backend.orchestrator.llm_provider import GeminiProvider
from backend.agents.data_source.data_source_agent import DataSourceAgent
from backend.agents.bi_tool.bi_tool_agent import BIToolAgent
from backend.agents.bi_tool.json_parser import BIJsonParser

async def interactive_loop():
    print("=== BI Agent Interactive CLI ===")
    print("명령어: 'exit', 'quit'로 종료")
    print("팁: '데이터베이스 목록 보여줘' 또는 '새 연결 등록해줘' 등으로 연결 관리 가능")
    
    # 설정 로드
    quota_manager = QuotaManager()
    project_id = os.getenv("GCP_PROJECT_ID")
    if project_id and project_id != "your-project-id":
        print(f"[System]: GCP 프로젝트({project_id})와 할당량 동기화를 시도합니다...")
        await quota_manager.sync_with_gcp(project_id)
    
    llm = GeminiProvider(quota_manager=quota_manager)
    conn_manager = ConnectionManager()
    
    # 에이전트 초기화
    data_agent = DataSourceAgent()
    bi_json_path = "backend/data/bi_solution.json"
    parser = BIJsonParser(bi_json_path)
    bi_agent = BIToolAgent(parser=parser)
    orchestrator = Orchestrator(llm=llm, data_agent=data_agent, bi_agent=bi_agent, connection_manager=conn_manager)
    
    # 테스트용 프로젝트가 등록되어 있지 않으면 미리 등록 (예시)
    if not conn_manager.get_connection("test_pg"):
        test_connection_info = {
            "type": "postgres",
            "server_path": os.path.abspath("backend/mcp_servers/postgres_server.js"),
            "config": {
                "DB_HOST": os.getenv("DB_HOST", "localhost"),
                "DB_PORT": os.getenv("DB_PORT", "5432"),
                "DB_NAME": os.getenv("DB_NAME", "postgres"),
                "DB_USER": os.getenv("DB_USER", "postgres"),
                "DB_PASSWORD": os.getenv("DB_PASSWORD", "")
            }
        }
        conn_manager.register_connection("test_pg", test_connection_info)
    
    context = {} # 더 이상 명시적인 connection_info 주입 불필요 (Manager에서 관리)

    while True:
        try:
            user_input = input("\n[User]: ")
            if user_input.lower() in ['exit', 'quit']:
                break
            
            if not user_input.strip():
                continue
                
            print("[Agent]: 생각 중...")
            result = await orchestrator.run(user_input, context=context)
            
            print(f"\n[Agent]: {result['final_response']}")
            
        except KeyboardInterrupt:
            print("\n[Agent]: 프로그램을 종료합니다. 이용해 주셔서 감사합니다!")
            break
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                print("\n[Agent]: ⚠️ 죄송합니다. 현재 API 사용량이 초과되었습니다 (Quota Exceeded).")
                print("잠시 후(약 1분) 다시 시도해 주시거나, API 설정을 확인해 주세요.")
            else:
                print(f"\n[Agent]: ❌ 예상치 못한 오류가 발생했습니다: {error_msg}")

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
