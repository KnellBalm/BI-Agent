import json
from datetime import datetime
from typing import TypedDict, List, Dict, Any, Union, Optional
from langgraph.graph import StateGraph, END
from backend.orchestrator.llm_provider import LLMProvider, GeminiProvider
from backend.orchestrator.connection_manager import ConnectionManager
from backend.agents.data_source.data_source_agent import DataSourceAgent
from backend.agents.bi_tool.bi_tool_agent import BIToolAgent

class AgentState(TypedDict):
    """
    Agent의 상태를 관리하는 객체
    """
    user_query: str
    intent: str  # 'data_query', 'bi_modification', 'general', 'connection_mgnt'
    messages: List[Dict[str, str]]
    next_node: str
    data_result: Any
    bi_result: Any
    final_response: str
    context: Dict[str, Any] # connection_info 등을 포함

class Orchestrator:
    """
    전체 Agent 시스템을 조율하는 메인 클래스 (LangGraph 기반)
    """
    def __init__(self, llm: Optional[LLMProvider] = None, 
                 data_agent: Optional[DataSourceAgent] = None,
                 bi_agent: Optional[BIToolAgent] = None,
                 connection_manager: Optional[ConnectionManager] = None):
        self.llm = llm or GeminiProvider()
        self.data_agent = data_agent
        self.bi_agent = bi_agent
        self.connection_manager = connection_manager or ConnectionManager()
        self.workflow = self._create_workflow()

    def _create_workflow(self) -> StateGraph:
        workflow = StateGraph(AgentState)

        # 1. 의도 분류 노드
        workflow.add_node("classify_intent", self._classify_intent)
        # 2. 데이터 처리 노드
        workflow.add_node("handle_data", self._handle_data)
        # 3. BI 처리 노드
        workflow.add_node("handle_bi", self._handle_bi)
        # 4. 연결 관리 노드
        workflow.add_node("connection_mgnt", self._handle_connection_mgnt)
        # 5. 최종 응답 생성 노드
        workflow.add_node("generate_response", self._generate_response)

        # 간선 정의
        workflow.set_entry_point("classify_intent")
        
        workflow.add_conditional_edges(
            "classify_intent",
            self._route_by_intent,
            {
                "data": "handle_data",
                "bi": "handle_bi",
                "connection_mgnt": "connection_mgnt",
                "general": "generate_response"
            }
        )

        workflow.add_edge("handle_data", "generate_response")
        workflow.add_edge("handle_bi", "generate_response")
        workflow.add_edge("connection_mgnt", "generate_response")
        workflow.add_edge("generate_response", END)

        return workflow.compile()

    async def _classify_intent(self, state: AgentState) -> Dict[str, Any]:
        prompt = f"""
다음 사용자 질문의 의도를 하나로 분류하세요:
질문: "{state['user_query']}"

분류 기준:
- 'data': 데이터베이스 조회, 매출 확인, 통계 등 데이터가 필요한 경우
- 'bi': 대시보드 수정, 필드 추가, 차트 변경 등 BI 도구 설정이 필요한 경우
- 'connection_mgnt': 데이터베이스 연결 등록, 삭제, 목록 조회 등 연결 관리 작업
- 'general': 그 외 일반적인 대화

응답은 오직 'data', 'bi', 'connection_mgnt', 'general' 중 하나만 하세요.
"""
        res = await self.llm.generate(prompt)
        intent = res.strip().lower()
        return {"intent": intent}

    def _route_by_intent(self, state: AgentState) -> str:
        if state["intent"] == "data":
            return "data"
        elif state["intent"] == "bi":
            return "bi"
        elif state["intent"] == "connection_mgnt":
            return "connection_mgnt"
        else:
            return "general"

    async def _handle_data(self, state: AgentState) -> Dict[str, Any]:
        if not self.data_agent:
            return {"final_response": "Data agent is not initialized."}
        
        # 실제 데이터 조회 로직
        conn_info = state["context"].get("connection_info")
        conn_id = state["context"].get("connection_id")
        
        # ID로 연결 정보 조회 시도
        if not conn_info and conn_id:
            conn_info = self.connection_manager.get_connection(conn_id)
            
        if not conn_info:
            # 등록된 연결이 하나뿐이라면 그것을 자동으로 사용 (편의성)
            conns = self.connection_manager.list_connections()
            if len(conns) == 1:
                conn_info = conns[0]
        
        if not conn_info:
            return {"final_response": "연결 정보(Connection Info)를 찾을 수 없습니다. 먼저 연결을 등록해 주세요."}
        
        try:
            if conn_info.get("type") == "excel":
                df = await self.data_agent.read_excel(conn_info, state["user_query"])
            else:
                df = await self.data_agent.query_database(conn_info, state["user_query"])
            return {"data_result": df.to_dict()}
        except Exception as e:
            return {"final_response": f"데이터 조회 중 오류가 발생했습니다: {str(e)}"}

    async def _handle_bi(self, state: AgentState) -> Dict[str, Any]:
        if not self.bi_agent:
            return {"final_response": "BI tool agent is not initialized."}
        
        # 이전 데이터 조회 결과(있다면)를 컨텍스트로 제공
        data_insight = ""
        if state.get("data_result"):
            data_insight = f"\n이전 데이터 조회 결과: {json.dumps(state['data_result'], ensure_ascii=False)[:500]}..."

        # BI 수정 로직 (LLM을 사용하여 함수 호출 파라미터 추출)
        prompt = f"""
당신은 BI 전문가입니다. 사용자의 요청을 분석하여 BI 에이전트의 적절한 메서드를 호출하기 위한 JSON을 생성하세요.
사용자 요청: "{state['user_query']}"{data_insight}

현재 사용 가능한 메서드와 파라미터:
1. add_field_to_datamodel: {{"method": "add_field_to_datamodel", "params": {{"datamodel_name": "...", "field_info": {{ "name": "...", "type": "..." }}}}}}
2. update_dataset_query: {{"method": "update_dataset_query", "params": {{"datamodel_name": "...", "new_query": "..."}}}}
3. update_visual_text: {{"method": "update_visual_text", "params": {{"report_name": "...", "element_id": "...", "new_text": "..."}}}}
4. set_data_to_visual: {{"method": "update_visual_text", "params": {{"report_name": "...", "element_id": "...", "new_text": "데이터 반영 완료"}}}} (예시)

응답은 오직 위 형식의 JSON 하나만 하세요. 매칭되는 것이 없으면 {{"method": "none"}} 이라고 하세요.

JSON:"""
        res = await self.llm.generate(prompt)
        try:
            # JSON 파싱
            clean_res = res.strip()
            if "{" in clean_res:
                clean_res = clean_res[clean_res.find("{"):clean_res.rfind("}")+1]
            call_info = json.loads(clean_res)
            
            method_name = call_info.get("method")
            params = call_info.get("params", {})
            
            if method_name == "add_field_to_datamodel":
                success = self.bi_agent.add_field_to_datamodel(**params)
            elif method_name == "update_dataset_query":
                success = self.bi_agent.update_dataset_query(**params)
            elif method_name == "update_visual_text":
                success = self.bi_agent.update_visual_text(**params)
            elif method_name == "none":
                return {"bi_result": "요청하신 작업을 수행할 적절한 방법을 찾지 못했습니다."}
            else:
                return {"bi_result": f"알 수 없는 메서드입니다: {method_name}"}
            
            if success:
                self.bi_agent.parser.save() # 변경사항 저장
                return {"bi_result": f"성공적으로 '{method_name}' 작업을 완료했습니다."}
            else:
                return {"bi_result": f"'{method_name}' 작업에 실패했습니다. 대상(데이터 모델 등)이 존재하는지 확인해 주세요."}
                
        except Exception as e:
            return {"bi_result": f"BI 작업 파싱 및 실행 중 오류가 발생했습니다: {str(e)}"}

    async def _handle_connection_mgnt(self, state: AgentState) -> Dict[str, Any]:
        """연결 등록, 삭제, 조회 등 관리 작업을 수행합니다."""
        user_q = state["user_query"]
        
        # 1. 목록 조회
        if any(w in user_q for w in ["목록", "리스트", "다 보여줘"]):
            conns = self.connection_manager.list_connections()
            if not conns:
                return {"bi_result": "현재 등록된 연결이 없습니다."}
            
            res_text = "현재 등록된 연결 목록:\n"
            for c in conns:
                res_text += f"- **{c['id']}** ({c['type']})\n"
            return {"bi_result": res_text}
            
        # 2. 등록/추가
        if any(w in user_q for w in ["등록", "추가", "새 연결"]):
            prompt = f"""
데이터베이스/엑셀 연결 정보를 추출하세요.
문구: "{user_q}"

JSON:
{{
  "id": "고유ID",
  "type": "postgres, mysql, excel 중 하나",
  "server_path": "MCP 서버 파일 절대 경로 (있을 경우)",
  "file_path": "엑셀 파일 경로 (있을 경우)",
  "config": {{ "DB_HOST": "...", "DB_USER": "..." }}
}}
"""
            res = await self.llm.generate(prompt)
            try:
                clean_res = res.strip()
                if "{" in clean_res:
                    clean_res = clean_res[clean_res.find("{"):clean_res.rfind("}")+1]
                conn_info = json.loads(clean_res)
                conn_id = conn_info.pop("id", f"conn_{int(datetime.now().timestamp())}")
                self.connection_manager.register_connection(conn_id, conn_info)
                return {"bi_result": f"연결 '{conn_id}'가 등록되었습니다."}
            except Exception as e:
                return {"bi_result": f"정보 추출 실패: {str(e)}"}

        # 3. 삭제
        if any(w in user_q for w in ["삭제", "지워", "제거"]):
            prompt = f"다음 문구에서 삭제할 연결 ID를 추출하세요: '{user_q}'\nID만 응답하세요."
            conn_id = await self.llm.generate(prompt)
            conn_id = conn_id.strip()
            
            if self.connection_manager.delete_connection(conn_id):
                return {"bi_result": f"연결 '{conn_id}'를 삭제했습니다."}
            else:
                return {"bi_result": f"연결 '{conn_id}'를 찾을 수 없어 삭제에 실패했습니다."}

        # 4. 상태 확인 (Ping)
        if any(w in user_q for w in ["상태", "테스트", "연결 확인", "핑"]):
            prompt = f"다음 문구에서 확인할 연결 ID를 추출하세요: '{user_q}'\nID만 응답하세요."
            conn_id = await self.llm.generate(prompt)
            conn_id = conn_id.strip()
            
            ping_res = await self.connection_manager.ping_connection(conn_id)
            return {"bi_result": ping_res["message"]}
            
        return {"bi_result": "명령을 이해하지 못했습니다. (목속, 등록, 삭제, 상태 확인 중 입력해 주세요)"}

    async def _generate_response(self, state: AgentState) -> Dict[str, Any]:
        data_res = state.get("data_result")
        bi_res = state.get("bi_result")
        user_q = state["user_query"]
        
        if data_res:
            # 데이터 결과를 바탕으로 답변 생성
            prompt = f"""
다음은 사용자의 질문과 그에 대한 데이터베이스 조회 결과입니다.
질문: "{user_q}"
데이터(dict): {data_res}

이 데이터를 바탕으로 사용자에게 친절하고 전문적인 답변을 작성하세요.
필요하다면 데이터의 요약이나 인사이트를 포함하세요.
"""
            response = await self.llm.generate(prompt)
        elif bi_res:
            response = f"BI 도구 수정을 시작합니다: {bi_res}\n공사가 완료되면 알려드릴게요!"
        else:
            response = await self.llm.generate(f"사용자의 질문에 대해 일반적으로 답하세요: {user_q}")
            
        return {"final_response": response}

    async def run(self, user_query: str, context: Dict[str, Any] = None):
        """작업 실행"""
        initial_state = {
            "user_query": user_query,
            "messages": [{"role": "user", "content": user_query}],
            "context": context or {}
        }
        return await self.workflow.ainvoke(initial_state)
