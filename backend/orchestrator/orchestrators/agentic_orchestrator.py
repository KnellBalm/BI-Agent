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
import inspect
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
    
    def execute(self, tool_name: str, arguments: Dict[str, Any], context: Dict[str, Any] = None) -> str:
        """도구를 실행하고 결과를 반환합니다."""
        if tool_name not in self._tools:
            return f"알 수 없는 도구: {tool_name}"
        try:
            func = self._tools[tool_name]["func"]
            
            # 함수 시그니처 검사
            sig = inspect.signature(func)
            call_args = arguments.copy()
            
            # context 파라미터가 있으면 주입
            if 'context' in sig.parameters:
                call_args['context'] = context
            
            return func(**call_args)
        except Exception as e:
            return f"도구 실행 오류 ({tool_name}): {str(e)}"
    
    @property
    def tool_names(self) -> List[str]:
        return list(self._tools.keys())


def _build_default_registry() -> ToolRegistry:
    """기본 도구 레지스트리를 생성합니다.

    전체 BI 파이프라인에 필요한 15개 도구를 등록합니다:
    - 데이터소스: list_connections, query_database, analyze_schema
    - 시각화: recommend_chart, generate_chart, apply_theme, calculate_layout
    - 인터랙션: setup_interactions, detect_drilldown
    - 분석: generate_summary, lint_report, suggest_questions
    - 출력: validate_json, export_report, preview_dashboard
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
    
    def query_database(query_description: str = "", context: Dict[str, Any] = None) -> str:
        """데이터베이스에 SQL 쿼리를 실행합니다. SELECT만 허용됩니다."""
        import sqlite3
        import os
        
        # ConnectionManager를 통한 동적 연결 정보 조회
        try:
            conn_mgr = ConnectionManager()
            active_connection = context.get('active_connection') if context else None
            
            if not active_connection:
                return "❌ 활성화된 데이터베이스 연결이 없습니다. 먼저 /connect 명령으로 DB에 연결하세요."
            
            conn_info = conn_mgr.get_connection(active_connection)
            if not conn_info:
                return f"❌ 연결 정보를 찾을 수 없습니다: {active_connection}"
            
            if conn_info.get('type') != 'sqlite':
                return f"❌ 현재 query_database 도구는 SQLite만 지원합니다. (현재 타입: {conn_info.get('type')})"
            
            db_path = conn_info.get('config', {}).get('path')
            if not db_path or not os.path.exists(db_path):
                return f"❌ DB 파일을 찾을 수 없습니다: {db_path}"
                
        except Exception as e:
            return f"❌ 연결 정보 로드 중 오류 발생: {str(e)}"
        
        query = query_description.strip()
        # SQL 블록 제거 (```sql ... ```)
        if "```" in query:
            lines = query.split("\n")
            query = "\n".join([l for l in lines if not l.startswith("```")])
        
        if not query.upper().startswith("SELECT"):
            return "❌ 올바른 SQL SELECT 쿼리를 입력하세요. (자연어는 자동으로 번역되지 않습니다.)"
        
        # 안전 검증: SELECT만 허용
        if any(kw in query.upper() for kw in ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE"]):
            return "⚠️ 읽기 전용 모드입니다. SELECT 쿼리만 허용됩니다."
        
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(query)
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description] if cur.description else []
            conn.close()
            
            if not rows:
                return f"[데이터 조회] 결과 없음 (SQL: {query})"
            
            result = f"[데이터 조회] {len(rows)}건 반환\n"
            result += f"SQL: {query}\n"
            result += f"컬럼: {', '.join(columns)}\n"
            result += "-" * 50 + "\n"
            for row in rows[:10]:  # 최대 10행 표시
                vals = [f"{columns[i]}={row[i]}" for i in range(len(columns))]
                result += "  " + " | ".join(vals) + "\n"
            if len(rows) > 10:
                result += f"  ... (총 {len(rows)}건)\n"
            return result
        except Exception as e:
            return f"쿼리 실행 오류: {str(e)} (SQL: {query})"
    
    def analyze_schema(table_name: str = "", context: Dict[str, Any] = None) -> str:
        """데이터베이스 테이블 구조를 분석합니다."""
        import sqlite3
        import os
        
        try:
            conn_mgr = ConnectionManager()
            active_connection = context.get('active_connection') if context else None
            
            if not active_connection:
                return "❌ 활성화된 데이터베이스 연결이 없습니다."
                
            conn_info = conn_mgr.get_connection(active_connection)
            if not conn_info:
                return f"❌ 연결 정보를 찾을 수 없습니다: {active_connection}"
                
            if conn_info.get('type') != 'sqlite':
                return f"❌ 현재 analyze_schema 도구는 SQLite만 지원합니다."
                
            db_path = conn_info.get('config', {}).get('path')
            if not db_path or not os.path.exists(db_path):
                return f"❌ DB 파일을 찾을 수 없습니다: {db_path}"
        except Exception as e:
            return f"❌ 연결 정보 로드 오류: {str(e)}"
        
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            
            # 테이블 목록 조회
            tables = cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_list = [t[0] for t in tables]
            
            if table_name and table_name not in table_list:
                conn.close()
                return f"테이블 '{table_name}'를 찾을 수 없습니다. 존재: {', '.join(table_list)}"
            
            targets = [table_name] if table_name else table_list
            result = f"[스키마 분석] DB: {os.path.basename(db_path)}\n"
            
            for tbl in targets:
                cols = cur.execute(f'PRAGMA table_info("{tbl}")').fetchall()
                count = cur.execute(f'SELECT COUNT(*) FROM "{tbl}"').fetchone()[0]
                result += f"\n📊 {tbl} ({count}행)\n"
                
                profile_data = []
                for c in cols:
                    col_name, col_type, notnull, default, pk = c[1], c[2], c[3], c[4], c[5]
                    # 유니크 값 카운트
                    unique = cur.execute(f'SELECT COUNT(DISTINCT "{col_name}") FROM "{tbl}"').fetchone()[0]
                    flags = []
                    if pk: flags.append("PK")
                    if notnull: flags.append("NOT NULL")
                    flag_str = f" [{', '.join(flags)}]" if flags else ""
                    result += f"  - {col_name}: {col_type}{flag_str} (유니크: {unique})\n"
                    profile_data.append({
                        "name": col_name, "type": col_type, "unique": unique
                    })
                
                # 샘플 데이터 2행
                samples = cur.execute(f'SELECT * FROM "{tbl}" LIMIT 2').fetchall()
                if samples:
                    col_names = [c[1] for c in cols]
                    result += "  샘플 데이터:\n"
                    for row in samples:
                        vals = [f"{col_names[i]}={row[i]}" for i in range(len(col_names))]
                        result += f"    {' | '.join(vals)}\n"
            
            conn.close()
            return result
        except Exception as e:
            return f"스키마 분석 오류: {str(e)}"
    
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

    def suggest_questions(analysis_context: str = "") -> str:
        """분석 결과를 기반으로 후속 질문을 자동 제안합니다."""
        from backend.agents.bi_tool.proactive_question_generator import ProactiveQuestionGenerator

        generator = ProactiveQuestionGenerator()

        # 샘플 컨텍스트 (실제로는 분석 결과 전달)
        sample_context = {
            "purpose": analysis_context or "매출 분석",
            "key_findings": ["Q4 매출 15% 증가", "온라인 채널 성장 주도"],
            "data_characteristics": {
                "has_time_dimension": True,
                "has_categories": True,
                "has_metrics": ["revenue", "quantity"]
            }
        }

        try:
            # asyncio.run() 대신 폴백 경로 직접 호출 (동기 함수)
            questions = generator._generate_fallback(sample_context)
        except Exception as e:
            return f"질문 생성 실패: {str(e)}"

        if not questions:
            return f"'{analysis_context}'에 대한 후속 질문을 생성하지 못했습니다."

        result = f"[후속 질문 제안] '{analysis_context}'에 대한 추가 분석 질문:\n"
        for i, q in enumerate(questions, 1):
            result += f"{i}. [{q.question_type.value.upper()}] {q.question}\n"
            if q.context:
                result += f"   → 이유: {q.context}\n"

        return result

    def _generate_fallback_questions(analysis_context: str = "") -> str:
        """LLM 실패 시 규칙 기반 폴백 질문 생성"""
        context = analysis_context or "데이터 분석"
        result = f"[후속 질문 제안] '{context}'에 대한 추가 분석 질문:\n"
        result += "1. [TEMPORAL] 시간에 따른 변화 추이는 어떤가요?\n"
        result += "   → 이유: 시계열 패턴 파악으로 트렌드 예측 가능\n"
        result += "2. [SEGMENT] 주요 세그먼트별로 나누어 보면 어떤 차이가 있나요?\n"
        result += "   → 이유: 세부 그룹별 특성 이해 및 타겟팅 전략 수립\n"
        result += "3. [CAUSAL] 주요 변화의 원인은 무엇인가요?\n"
        result += "   → 이유: 근본 원인 파악으로 실행 가능한 인사이트 도출\n"
        return result

    def preview_dashboard(report_path: str = "", auto_open: bool = True) -> str:
        """생성된 대시보드를 로컬 웹 서버에서 미리보기합니다."""
        from backend.utils.preview_server import get_preview_server
        import os
        import time

        server = get_preview_server()

        # 서버가 실행 중이 아니면 시작
        if not server.is_running:
            server.start(open_browser=False, daemon=True)
            time.sleep(0.5)  # 서버 시작 대기

        # 리포트 경로가 제공된 경우 등록
        if report_path and os.path.exists(report_path):
            report_id = f"report_{int(time.time())}"
            url = server.register_report(report_id, report_path)

            if auto_open:
                server.open_browser(report_id)

            return (f"[대시보드 미리보기]\n"
                    f"  서버: http://{server.host}:{server.port}\n"
                    f"  리포트 URL: {url}\n"
                    f"  브라우저 자동 오픈: {'예' if auto_open else '아니오'}")
        else:
            # 리포트 목록만 표시
            main_url = server.get_url()
            if auto_open:
                server.open_browser()
            return (f"[대시보드 미리보기 서버]\n"
                    f"  상태: {'실행 중' if server.is_running else '중지됨'}\n"
                    f"  URL: {main_url}\n"
                    f"  등록된 리포트: {len(server.reports)}개")

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
    registry.register("suggest_questions", "분석 결과 기반 후속 질문 자동 제안", suggest_questions,
                       {"analysis_context": "분석 설명"})
    registry.register("preview_dashboard", "대시보드 웹 미리보기", preview_dashboard,
                       {"report_path": "HTML 리포트 파일 경로", "auto_open": "브라우저 자동 오픈 여부 (true/false)"})

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
            
            # Context 전달
            result = self._registry.execute(action, arguments, context=state.get("context"))
            
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
            # Use active connection as part of the thread_id for state permanence per database
            active_conn = (context or {}).get("active_connection", "default")
            base_thread_id = (context or {}).get("thread_id", "session")
            thread_id = f"{base_thread_id}-{active_conn}"
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
