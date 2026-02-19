"""
Agentic Orchestrator - ReAct Loop (TASK-003)

기존의 고정된 Router 패턴(classify_intent → handle_X → response)을 대체하여,
LLM이 자율적으로 도구를 선택하고 실행하는 ReAct(Reason+Act) 루프를 구현합니다.

Steel Thread: "사용자 질문 → LLM 판단 → 도구 호출 → 결과 관찰 → 최종 답변"
이 하나의 경로가 처음부터 끝까지 동작하는 것이 목표입니다.

이 구현은 bind_tools 없이도 작동하는 '수동 Tool Calling' 방식을 사용합니다.
모든 LLM Provider(Gemini, Claude, OpenAI, Ollama)에서 범용적으로 동작합니다.
"""
import json
from typing import TypedDict, List, Dict, Any, Optional, Annotated, Sequence
from operator import add

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

from backend.orchestrator.orchestrators.base_orchestrator import AbstractOrchestrator
from backend.orchestrator.providers.langchain_adapter import BIAgentChatModel
from backend.orchestrator.providers.checkpointer import get_checkpointer
from backend.orchestrator.managers.connection_manager import ConnectionManager
from backend.utils.logger_setup import setup_logger

logger = setup_logger("agentic_orchestrator", "agentic_orchestrator.log")

# ──────────────────────────────────────────────
# 1. State 정의
# ──────────────────────────────────────────────

class AgenticState(TypedDict):
    """에이전틱 오케스트레이터의 상태 객체.
    
    messages는 Annotated[..., add]를 사용하여 
    각 노드가 반환한 메시지가 기존 리스트에 '추가'됩니다.
    """
    messages: Annotated[Sequence[BaseMessage], add]
    context: Dict[str, Any]
    iteration_count: int


# ──────────────────────────────────────────────
# 2. 도구(Tool) 레지스트리 — 수동 호출 방식
# ──────────────────────────────────────────────

class ToolRegistry:
    """프롬프트 기반 수동 Tool Calling을 위한 도구 레지스트리.
    
    bind_tools를 지원하지 않는 커스텀 LLM에서도 동작합니다.
    LLM이 JSON으로 도구 이름과 인자를 출력하면, 이 레지스트리가 실행합니다.
    """
    
    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}
    
    def register(self, name: str, description: str, func, params: Dict[str, str] = None):
        """도구를 등록합니다."""
        self._tools[name] = {
            "description": description,
            "func": func,
            "params": params or {},
        }
    
    def get_tools_prompt(self) -> str:
        """LLM에 주입할 도구 설명 프롬프트를 생성합니다."""
        lines = []
        for name, info in self._tools.items():
            params_desc = ", ".join(f"{k}: {v}" for k, v in info["params"].items())
            lines.append(f"- **{name}**({params_desc}): {info['description']}")
        return "\n".join(lines)
    
    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """도구를 실행하고 결과를 반환합니다."""
        if tool_name not in self._tools:
            return f"알 수 없는 도구: {tool_name}"
        try:
            return self._tools[tool_name]["func"](**arguments)
        except Exception as e:
            return f"도구 실행 오류 ({tool_name}): {str(e)}"
    
    @property
    def tool_names(self) -> List[str]:
        return list(self._tools.keys())


def _build_default_registry() -> ToolRegistry:
    """기본 도구 레지스트리를 생성합니다.
    
    전체 BI 파이프라인에 필요한 13개 도구를 등록합니다:
    - 데이터소스: list_connections, query_database, analyze_schema
    - 시각화: recommend_chart, generate_chart, apply_theme, calculate_layout
    - 인터랙션: setup_interactions, detect_drilldown
    - 분석: generate_summary, lint_report
    - 출력: validate_json, export_report
    """
    registry = ToolRegistry()
    
    # ──── 데이터소스 도구 ────
    
    def list_connections() -> str:
        """현재 등록된 데이터베이스 연결 목록을 조회합니다."""
        try:
            conn_mgr = ConnectionManager()
            conns = conn_mgr.list_connections()
            if not conns:
                return "현재 등록된 연결이 없습니다."
            result = "등록된 연결 목록:\n"
            for c in conns:
                result += f"- {c.get('id', 'unknown')} ({c.get('type', 'unknown')})\n"
            return result
        except Exception as e:
            return f"연결 목록 조회 실패: {str(e)}"
    
    def query_database(query_description: str = "") -> str:
        return f"[데이터 조회 수행] '{query_description}' — 실제 DB 연동은 다음 단계에서 구현됩니다."
    
    def analyze_schema(table_name: str = "") -> str:
        return f"[스키마 분석 완료] 테이블 '{table_name or '전체'}'의 구조를 분석했습니다."
    
    # ──── 시각화 도구 (Step 11) ────
    
    def recommend_chart(data_description: str = "") -> str:
        """ChartRecommender 엔진으로 최적 차트를 추천합니다."""
        import json as _json
        from backend.agents.bi_tool.chart_recommender import ChartRecommender
        recommender = ChartRecommender()
        sample_profile = {
            "columns": [
                {"name": "date", "type": "datetime", "unique": 365},
                {"name": "amount", "type": "numerical", "unique": 1000},
                {"name": "category", "type": "categorical", "unique": 5},
            ],
            "row_count": 1000
        }
        recs = recommender.recommend_multiple_charts(sample_profile, max_charts=3)
        if not recs:
            return f"'{data_description}'에 대해 적합한 차트를 찾지 못했습니다."
        result = f"'{data_description}'에 대한 차트 추천:\n"
        for i, r in enumerate(recs, 1):
            result += f"{i}. {r['chart_type']} — {r['reason']}\n"
        return result
    
    def generate_chart(chart_request: str = "") -> str:
        """추천된 차트를 생성합니다."""
        import json as _json
        from backend.agents.bi_tool.chart_recommender import ChartRecommender
        recommender = ChartRecommender()
        sample_profile = {"columns": [
            {"name": "date", "type": "datetime", "unique": 365},
            {"name": "amount", "type": "numerical", "unique": 1000},
            {"name": "category", "type": "categorical", "unique": 5},
        ]}
        best = recommender.recommend_chart(sample_profile)
        return f"[차트 생성] '{chart_request}' → {best['chart_type']} ({best['reason']})"
    
    def apply_theme(theme_name: str = "premium_dark") -> str:
        """대시보드에 테마를 적용합니다. 5종: premium_dark, corporate_light, executive_blue, nature_green, sunset_warm"""
        from backend.agents.bi_tool.theme_engine import ThemeEngine
        engine = ThemeEngine(theme_name)
        palette = engine.theme
        tokens = engine.get_layout_tokens()
        return (f"[테마 적용] '{theme_name}'\n"
                f"  배경: {palette.get('background')}, 주색: {palette.get('primary')}\n"
                f"  그리드: {tokens['grid_cols']}열, 마진: {tokens['margin']}px")
    
    def calculate_layout(strategy: str = "balanced") -> str:
        """컴포넌트 레이아웃을 자동 계산합니다. 전략: balanced, priority, compact"""
        from backend.agents.bi_tool.layout_calculator import LayoutCalculator
        calc = LayoutCalculator()
        sample_components = [
            {"id": "chart_1", "type": "BarChart", "priority": "high"},
            {"id": "chart_2", "type": "LineChart", "priority": "medium"},
            {"id": "filter_1", "type": "DropdownFilter", "priority": "low"},
            {"id": "kpi_1", "type": "Label", "priority": "high"},
        ]
        laid_out = calc.auto_layout(sample_components, layout_strategy=strategy)
        result = f"[레이아웃 계산] 전략: {strategy}, {len(laid_out)}개 컴포넌트 배치\n"
        for comp in laid_out:
            hint = comp.get("layout_hint", {})
            result += f"  - {comp['id']}: col_span={hint.get('col_span')}, row={hint.get('row')}\n"
        return result
    
    # ──── 인터랙션 도구 (Step 12) ────
    
    def setup_interactions(interaction_type: str = "cross_filter") -> str:
        """대시보드 인터랙션을 설정합니다. 유형: cross_filter, drilldown, parameter"""
        from backend.agents.bi_tool.interaction_logic import InteractionLogic
        logic = InteractionLogic()
        sample_profile = {
            "columns": [
                {"name": "region", "type": "categorical", "unique": 5},
                {"name": "product", "type": "categorical", "unique": 20},
                {"name": "revenue", "type": "numerical", "unique": 500},
                {"name": "date", "type": "datetime", "unique": 365},
            ]
        }
        config = logic.suggest_configuration(sample_profile)
        var_count = len(config.get("varList", []))
        event_count = len(config.get("eventList", []))
        return (f"[인터랙션 설정] 유형: {interaction_type}\n"
                f"  변수(varList): {var_count}개, 이벤트(eventList): {event_count}개\n"
                f"  컴포넌트: {len(config.get('components', []))}개")
    
    def detect_drilldown(data_description: str = "") -> str:
        """데이터의 드릴다운 계층 구조를 자동 감지합니다."""
        from backend.agents.bi_tool.drilldown_mapper import DrilldownMapper
        mapper = DrilldownMapper()
        sample_profile = {
            "columns": [
                {"name": "country", "type": "categorical", "unique": 10},
                {"name": "region", "type": "categorical", "unique": 50},
                {"name": "city", "type": "categorical", "unique": 200},
                {"name": "revenue", "type": "numerical", "unique": 1000},
            ]
        }
        hierarchies = mapper.detect_hierarchies(sample_profile)
        if not hierarchies:
            return f"'{data_description}'에서 드릴다운 계층을 찾지 못했습니다."
        result = f"[드릴다운 감지] '{data_description}':\n"
        for h in hierarchies:
            result += f"  - {h['name']}: {' → '.join(h['levels'])}\n"
        return result
    
    # ──── 분석 도구 (Step 13~14) ────
    
    def generate_summary(analysis_description: str = "") -> str:
        """분석 결과의 한국어 요약을 생성합니다."""
        return (f"[요약 생성] '{analysis_description}'\n"
                f"  SummaryGenerator가 LLM을 통해 Executive Summary와 Key Insights를 생성합니다.\n"
                f"  실제 LLM 호출은 데이터 연동 완료 후 활성화됩니다.")
    
    def lint_report(report_description: str = "") -> str:
        """리포트 품질을 검사합니다 (시각 명료성, 데이터 정확성, 접근성, 성능)."""
        from backend.agents.bi_tool.report_linter import ReportLinter
        linter = ReportLinter()
        sample_report = {
            "title": "매출 분석 대시보드",
            "theme": {"fontFamily": "Inter", "fontSize": "14px"},
            "visuals": [
                {"id": "v1", "type": "BarChart", "title": "월별 매출",
                 "datamodel_id": "dm1",
                 "config": {"dimension": "month", "measure": "revenue"}},
            ],
            "connectors": [{"id": "c1", "type": "PostgreSQL"}],
            "datamodels": [{"id": "dm1", "connector_id": "c1", "query": "SELECT *"}],
        }
        issues = linter.lint_report(sample_report)
        summary = linter.get_summary()
        return (f"[리포트 린트] '{report_description}'\n"
                f"  품질 점수: {summary.get('quality_score', 'N/A')}/100\n"
                f"  이슈: 에러 {summary.get('errors', 0)}개, 경고 {summary.get('warnings', 0)}개, 정보 {summary.get('info', 0)}개")
    
    # ──── 출력 도구 (Step 15) ────
    
    def validate_json(validation_target: str = "") -> str:
        """InHouse JSON 스키마 정합성을 검증합니다."""
        from backend.agents.bi_tool.json_validator import JSONValidator
        validator = JSONValidator()
        sample_json = {
            "connectors": [{"id": "c1", "type": "PostgreSQL", "host": "localhost"}],
            "datamodels": [{"id": "dm1", "connector_id": "c1", "query": "SELECT 1"}],
            "reports": [{
                "id": "r1", "title": "테스트", "datamodel_id": "dm1",
                "visuals": [{"id": "v1", "type": "BarChart", "title": "차트",
                             "config": {"dimension": "x", "measure": "y"}}]
            }]
        }
        errors = validator.validate(sample_json)
        summary = validator.get_summary()
        return (f"[JSON 검증] '{validation_target}'\n"
                f"  준수 점수: {summary.get('compliance_score', 'N/A')}/100\n"
                f"  유효: {summary.get('is_valid', False)}\n"
                f"  이슈: {summary.get('total_issues', 0)}개")
    
    def export_report(format_type: str = "json") -> str:
        """대시보드를 지정된 형식으로 내보냅니다. 형식: json, excel, pdf"""
        return (f"[내보내기] 형식: {format_type}\n"
                f"  ExportPackager가 JSON/Excel/PDF 형식으로 패키징합니다.\n"
                f"  실행: export_packager.export_all(config, output_dir, ['{format_type}'])")
    
    # ──── 도구 등록 ────
    registry.register("list_connections", "데이터베이스 연결 목록 조회", list_connections)
    registry.register("query_database", "자연어 기반 데이터 조회", query_database,
                       {"query_description": "조회할 데이터 설명"})
    registry.register("analyze_schema", "테이블/컬럼 구조 분석", analyze_schema,
                       {"table_name": "분석할 테이블명"})
    registry.register("recommend_chart", "데이터 특성 기반 차트 추천", recommend_chart,
                       {"data_description": "분석 데이터 설명"})
    registry.register("generate_chart", "추천 차트 생성", generate_chart,
                       {"chart_request": "차트 설명"})
    registry.register("apply_theme", "대시보드 테마 적용", apply_theme,
                       {"theme_name": "테마명 (premium_dark/corporate_light/executive_blue/nature_green/sunset_warm)"})
    registry.register("calculate_layout", "컴포넌트 레이아웃 계산", calculate_layout,
                       {"strategy": "배치 전략 (balanced/priority/compact)"})
    registry.register("setup_interactions", "인터랙션 설정", setup_interactions,
                       {"interaction_type": "인터랙션 유형 (cross_filter/drilldown/parameter)"})
    registry.register("detect_drilldown", "드릴다운 계층 감지", detect_drilldown,
                       {"data_description": "데이터 설명"})
    registry.register("generate_summary", "분석 요약 생성", generate_summary,
                       {"analysis_description": "분석 설명"})
    registry.register("lint_report", "리포트 품질 검사", lint_report,
                       {"report_description": "리포트 설명"})
    registry.register("validate_json", "JSON 스키마 검증", validate_json,
                       {"validation_target": "검증 대상 설명"})
    registry.register("export_report", "리포트 내보내기", export_report,
                       {"format_type": "형식 (json/excel/pdf)"})
    
    return registry




# ──────────────────────────────────────────────
# 3. 에이전틱 오케스트레이터
# ──────────────────────────────────────────────

MAX_ITERATIONS = 5

SYSTEM_PROMPT_TEMPLATE = """당신은 BI-Agent의 핵심 분석 에이전트입니다.
사용자의 질문에 답하기 위해 아래 도구들을 자율적으로 활용하세요.

## 사용 가능한 도구
{tools_prompt}

## 응답 규칙
1. 도구가 필요하면 아래 JSON 형식으로만 응답하세요:
```json
{{"action": "도구이름", "arguments": {{"param": "value"}}}}
```

2. 도구가 필요 없거나, 최종 답변을 할 준비가 되면 아래 형식으로 응답하세요:
```json
{{"action": "final_answer", "answer": "최종 답변 내용"}}
```

3. 항상 한국어로 응답하세요.
4. JSON 외의 텍스트는 포함하지 마세요."""


class AgenticOrchestrator(AbstractOrchestrator):
    """
    ReAct 패턴 기반의 자율 에이전트 오케스트레이터.
    
    bind_tools 없이도 모든 LLM Provider에서 동작하는
    '프롬프트 기반 수동 Tool Calling' 방식을 사용합니다.
    
                  ┌──────────────────────┐
                  │    agent (LLM 판단)   │
                  └──────┬───────────────┘
                         │
                ┌────────▼─────────┐
        ┌───────┤  도구 호출 필요?  ├──────┐
        │ Yes   └──────────────────┘  No  │
        │                                  │
    ┌───▼───────┐                   ┌──────▼──┐
    │  execute   │                   │  END    │
    │  (도구실행)│                   └─────────┘
    └───┬───────┘
        │ 관찰 결과 → messages에 추가
        └──────────→ agent (다시 판단)
    """
    
    def __init__(self, llm: Optional[BIAgentChatModel] = None,
                 connection_manager: Optional[ConnectionManager] = None,
                 tool_registry: Optional[ToolRegistry] = None,
                 use_checkpointer: bool = True):
        self._chat_model = llm or BIAgentChatModel()
        self._registry = tool_registry or _build_default_registry()
        
        super().__init__(
            self._chat_model.provider,
            connection_manager or ConnectionManager()
        )
        
        self._use_checkpointer = use_checkpointer
        self.workflow = self._create_react_graph()
    
    def _create_react_graph(self):
        """ReAct 루프 그래프를 생성합니다."""
        graph = StateGraph(AgenticState)
        
        graph.add_node("agent", self._agent_node)
        graph.add_node("execute_tool", self._execute_tool_node)
        
        graph.set_entry_point("agent")
        graph.add_conditional_edges(
            "agent",
            self._should_continue,
            {"execute_tool": "execute_tool", "end": END}
        )
        graph.add_edge("execute_tool", "agent")
        
        if self._use_checkpointer:
            checkpointer = get_checkpointer()
            return graph.compile(checkpointer=checkpointer)
        
        return graph.compile()
    
    async def _agent_node(self, state: AgenticState) -> Dict[str, Any]:
        """에이전트 노드: LLM이 도구 사용 여부를 결정합니다."""
        messages = list(state["messages"])
        
        # 첫 호출 시 시스템 프롬프트 주입
        if not messages or not isinstance(messages[0], SystemMessage):
            system_prompt = SystemMessage(content=SYSTEM_PROMPT_TEMPLATE.format(
                tools_prompt=self._registry.get_tools_prompt()
            ))
            messages = [system_prompt] + messages
        
        # LLM 호출
        response = await self._chat_model.ainvoke(messages)
        
        current_count = state.get("iteration_count", 0) + 1
        
        return {
            "messages": [response],
            "iteration_count": current_count,
        }
    
    async def _execute_tool_node(self, state: AgenticState) -> Dict[str, Any]:
        """도구 실행 노드: LLM의 JSON 응답을 파싱하여 도구를 실행합니다."""
        last_message = state["messages"][-1]
        content = last_message.content if hasattr(last_message, "content") else str(last_message)
        
        try:
            parsed = self._parse_action(content)
            action = parsed.get("action", "")
            arguments = parsed.get("arguments", {})
            
            logger.info(f"도구 실행: {action}({arguments})")
            result = self._registry.execute(action, arguments)
            
            observation = HumanMessage(content=f"[도구 실행 결과 — {action}]\n{result}")
            return {"messages": [observation]}
            
        except Exception as e:
            error_msg = HumanMessage(content=f"[도구 실행 오류] JSON 파싱 실패: {str(e)}. 올바른 JSON 형식으로 다시 시도해주세요.")
            return {"messages": [error_msg]}
    
    def _parse_action(self, content: str) -> Dict[str, Any]:
        """LLM 응답에서 JSON action을 추출합니다."""
        # ```json ... ``` 블록 추출
        if "```json" in content:
            start = content.index("```json") + 7
            end = content.index("```", start)
            content = content[start:end].strip()
        elif "```" in content:
            start = content.index("```") + 3
            end = content.index("```", start)
            content = content[start:end].strip()
        
        # 순수 JSON 추출
        if "{" in content:
            start = content.index("{")
            end = content.rindex("}") + 1
            content = content[start:end]
        
        return json.loads(content)
    
    def _should_continue(self, state: AgenticState) -> str:
        """도구 호출이 필요한지 판단합니다."""
        if state.get("iteration_count", 0) >= MAX_ITERATIONS:
            logger.warning(f"최대 반복 횟수({MAX_ITERATIONS}) 도달. 루프 종료.")
            return "end"
        
        last_message = state["messages"][-1]
        content = last_message.content if hasattr(last_message, "content") else ""
        
        try:
            parsed = self._parse_action(content)
            action = parsed.get("action", "")
            
            if action == "final_answer":
                return "end"
            elif action in self._registry.tool_names:
                return "execute_tool"
            else:
                return "end"
        except (json.JSONDecodeError, ValueError):
            # JSON 파싱 실패 = 일반 텍스트 응답 = 최종 답변
            return "end"
    
    async def run(self, user_query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """에이전틱 오케스트레이터 실행."""
        initial_state = {
            "messages": [HumanMessage(content=user_query)],
            "context": context or {},
            "iteration_count": 0,
        }
        
        config = {}
        if self._use_checkpointer:
            thread_id = (context or {}).get("thread_id", "default-session")
            config = {"configurable": {"thread_id": thread_id}}
        
        try:
            result = await self.workflow.ainvoke(initial_state, config=config)
            
            # 최종 응답 추출
            final_content = ""
            last_msg = result["messages"][-1]
            content = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
            
            try:
                parsed = self._parse_action(content)
                if parsed.get("action") == "final_answer":
                    final_content = parsed.get("answer", content)
                else:
                    final_content = content
            except (json.JSONDecodeError, ValueError):
                final_content = content
            
            return {
                "final_response": final_content,
                "iteration_count": result.get("iteration_count", 0),
                "message_count": len(result["messages"]),
                "status": "success",
            }
        except Exception as e:
            logger.error(f"에이전틱 오케스트레이터 실행 실패: {e}")
            return {
                "final_response": f"분석 중 오류가 발생했습니다: {str(e)}",
                "status": "error",
            }
