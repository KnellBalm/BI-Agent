from typing import Dict, Any, List, Optional
from backend.orchestrator.orchestrators.base_orchestrator import AbstractOrchestrator
from backend.agents.bi_tool.bi_tool_agent import BIToolAgent
from backend.agents.bi_tool.guide_assistant import GuideAssistant
from backend.agents.bi_tool.tableau_metadata import TableauMetadataEngine
from backend.agents.bi_tool.pbi_logic_generator import PBILogicGenerator
from backend.agents.bi_tool.cloud_bi_connector import CloudBIConnector

class InteractionOrchestrator(AbstractOrchestrator):
    """
    사용자의 요청에 따라 Ask(가이드) 및 Agent(수정) 모드를 관리하는 총괄 오케스트레이터
    """
    def __init__(self, bi_agent: Optional[BIToolAgent] = None):
        super().__init__()
        self.bi_agent = bi_agent
        self.guide = GuideAssistant()
        self.pbi = PBILogicGenerator()
        self.cloud = CloudBIConnector()
        # Tableau 엔진은 파일 로드 시점에 동적으로 생성하거나 주입 가능

    def detect_intent(self, user_input: str) -> str:
        """
        사용자 입력을 분석하여 'ask'(가이드) 혹은 'agent'(수행) 모드를 판단합니다.
        """
        agent_keywords = ["수정", "변경", "생성", "추가", "연동", "update", "create", "change"]
        if any(kw in user_input for kw in agent_keywords):
            return "agent"
        return "ask"

    async def run(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        AbstractOrchestrator.run 인터페이스 구현
        """
        tool_type = context.get("tool_type", "native") if context else "native"
        mode = context.get("mode") if context else None
        return self.handle_request(user_input, tool_type, mode, context)

    def handle_request(self, user_input: str, tool_type: str, mode: Optional[str] = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        사용자 요청을 처리하여 모드별 최적의 결과를 반환합니다.
        """
        if not mode:
            mode = self.detect_intent(user_input)
            
        result = {"mode": mode, "tool": tool_type, "input": user_input}
        
        if mode == "ask":
            # 1. Ask Mode (Guide-First via RAG)
            action_type = "general"
            if "색" in user_input: action_type = "change_color"
            elif "필터" in user_input: action_type = "add_filter"
            elif "파라미터" in user_input: action_type = "parameter"
            
            guide_text = self.guide.generate_ui_guide(tool_type, action_type, context=context)
            result["response"] = guide_text
            
        elif mode == "agent":
            # 2. Agent Mode (Automation-First)
            if tool_type == "native" and self.bi_agent:
                result["response"] = "기존 BI 솔루션의 메타데이터 자동 수정 루틴을 시작합니다."
            elif tool_type == "tableau":
                result["response"] = "Tableau XML(.twb) 엔진을 통해 메타데이터 수정을 준비합니다."
            elif tool_type == "powerbi":
                dax = self.pbi.generate_dax("custom_metric")
                result["response"] = f"Power BI를 위한 DAX 수식을 생성했습니다: {dax}"
            elif tool_type in ["looker", "looker_studio"]:
                url = self.cloud.generate_looker_studio_url("sales_dashboard", "New Report", [])
                result["response"] = f"Looker Studio 템플릿 기반 리포트 생성 URL입니다: {url}"
            elif tool_type == "quicksight":
                guide = self.cloud.get_sdk_guide("quicksight", "analysis-123")
                result["response"] = f"Quicksight 배포를 위한 가이드와 명령어를 생성했습니다.\n{guide}"
            else:
                result["response"] = f"{tool_type} 에이전트 기능을 수행합니다."
                
        return result

    def handle_interactive_trigger(self, params: Dict[str, Any], profile: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process interactive parameters and invoke InHouseGenerator.

        Uses InteractionLogic to suggest components and dynamic queries based
        on the data profile.
        """
        from backend.agents.bi_tool.inhouse_generator import InHouseGenerator
        from backend.agents.bi_tool.interaction_logic import InteractionLogic
        
        # 1. Analyze profile to get suggested interaction config
        logic = InteractionLogic()
        config = logic.suggest_configuration(profile or {})
        
        # 2. Build Dashboard
        generator = InHouseGenerator(profile or {})
        generator.build_connector()
        
        # Build datamodel with suggested dynamic query
        generator.build_datamodel(
            name="auto_dataset", 
            base_query=config["dynamic_query"], 
            param_definitions=config["params"]
        )
        
        # Build report with suggested visuals and var/event lists
        generator.build_report(
            title="Automated Interactive Dashboard",
            components=config["visuals"],
            var_list=config["varList"],
            event_list=config["eventList"]
        )
        
        import tempfile
        output_path = os.path.join(tempfile.gettempdir(), "generated_dashboard.json")
        generator.dump_to_file(output_path)
        return {"status": "success", "path": output_path, "config": config}

