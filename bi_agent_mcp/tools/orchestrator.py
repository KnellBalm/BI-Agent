"""BI 분석 오케스트레이터 — bi_start, bi_orchestrate."""
from __future__ import annotations

from bi_agent_mcp.tools.db import _connections, get_schema
from bi_agent_mcp.tools.text_to_sql import generate_sql
from bi_agent_mcp.tools.bi_helper import bi_tool_selector
from bi_agent_mcp.tools.helper import hypothesis_helper
from bi_agent_mcp.tools.analysis import suggest_analysis

_GUIDE_TRIGGERS = [
    "어떻게", "방법", "뭐부터", "가이드", "어떤 도구", "무엇을",
    "설명", "추천해", "알려줘 방법", "how", "what tool", "guide",
]

_ORCHESTRATOR_TRIGGERS = [
    "분석해", "분석해줘", "왜", "원인", "파악해", "알아봐",
    "찾아줘", "계산해", "비교해", "어떻게 됐어", "어떤지", "얼마나",
    "떨어졌", "올랐", "늘었", "줄었", "analyze", "why", "cause",
]

_INTENT_MAP = [
    (["매출", "revenue", "sales", "하락", "감소"], "revenue_decline"),
    (["이탈", "churn", "retention"], "churn_increase"),
    (["전환", "conversion", "퍼널", "funnel", "드롭"], "conversion_drop"),
    (["성장", "growth", "증가", "신규"], "user_growth"),
    (["마케팅", "marketing", "캠페인", "campaign", "roas", "cac"], "marketing_effectiveness"),
    (["프로덕트", "product", "기능", "feature", "활성"], "product_performance"),
]


def _classify_intent(query: str) -> str:
    q = query.lower()
    for keywords, problem_type in _INTENT_MAP:
        if any(kw in q for kw in keywords):
            return problem_type
    return "general"


def _guide_mode(query: str) -> str:
    lines = [
        "## BI 분석 가이드",
        "",
        f"**요청:** {query}",
        "",
        bi_tool_selector(query),
    ]
    return "\n".join(lines)


def bi_start(query: str, conn_id: str = "") -> str:
    """[Orchestrator] 자연어 요청을 받아 가이드 모드 또는 오케스트레이터 모드로 분기합니다.

    Args:
        query: 자연어 분석 요청. 예: "이번 달 매출 왜 떨어졌어?", "A/B 테스트 어떻게 해?"
        conn_id: connect_db로 등록한 연결 ID (선택, 없으면 첫 번째 연결 사용)
    """
    if not conn_id and not _connections:
        return (
            "## 데이터 소스 연결이 필요합니다\n\n"
            "분석을 시작하려면 먼저 데이터 소스를 연결하세요.\n\n"
            "**DB 연결:**\n"
            "```\n"
            "connect_db(conn_id='mydb', db_type='postgresql', host='...', port=5432, "
            "database='...', username='...', password='...')\n"
            "```\n\n"
            "**파일 연결:**\n"
            "```\n"
            "connect_file(file_path='/path/to/data.csv', conn_id='myfile')\n"
            "```\n\n"
            "연결 후 다시 요청해 주세요."
        )

    query_lower = query.lower()
    is_guide = any(kw in query_lower for kw in _GUIDE_TRIGGERS)
    is_orchestrator = any(kw in query_lower for kw in _ORCHESTRATOR_TRIGGERS)

    if is_guide and not is_orchestrator:
        return _guide_mode(query)

    effective_conn = conn_id or next(iter(_connections), "")
    if effective_conn:
        return bi_orchestrate(query, effective_conn)

    return _guide_mode(query)


def bi_orchestrate(query: str, conn_id: str, output: str = "report") -> str:
    """[Orchestrator] 자연어 분석 요청을 end-to-end 분석 계획으로 변환합니다.

    Args:
        query: 자연어 분석 요청. 예: "이번 달 매출 왜 떨어졌어?"
        conn_id: connect_db로 등록한 연결 ID
        output: 출력 형식. "report" (기본) 또는 "dashboard"
    """
    if conn_id not in _connections:
        return (
            f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다. "
            f"list_connections()로 연결 목록을 확인하세요."
        )

    progress: list[str] = []

    schema = get_schema(conn_id)
    progress.append("→ 연결 및 스키마 확인 완료")

    problem_type = _classify_intent(query)
    progress.append(f"→ 분석 의도 분류: {problem_type}")

    hypothesis = hypothesis_helper(problem_type, data_context=schema[:500])
    tool_guide = bi_tool_selector(query)
    progress.append("→ 분석 도구 및 가설 프레임워크 수립 완료")

    sql_context = generate_sql(conn_id, query)
    progress.append("→ SQL 생성 컨텍스트 준비 완료")

    analysis_guide = suggest_analysis(schema[:1000], query)
    progress.append("→ 분석 방향 수립 완료")

    next_steps = [
        f"1. 위 **SQL 생성** 섹션의 SQL을 `run_query(conn_id='{conn_id}', sql='...')`로 실행하세요",
        f"2. 결과를 받아 **분석 도구 가이드**의 핵심 도구(예: `revenue_analysis`, `trend_analysis`)를 호출하세요",
        f"3. 분석 완료 후 `generate_report(sections=[{{\"title\": \"분석 결과\", \"content\": \"...\"}}])`로 보고서를 저장하세요",
    ]
    if output == "dashboard":
        next_steps.append(
            f"4. 또는 `generate_dashboard(data='...', charts=[{{\"type\": \"line\", \"x\": \"날짜\", \"y\": \"매출\"}}])`로 대시보드를 생성하세요"
        )

    lines = [
        "# BI 분석 실행 계획",
        "",
        f"**요청:** {query}",
        f"**연결:** {conn_id}",
        "",
        "## 실행 로그",
        "\n".join(progress),
        "",
        "---",
        "",
        "## 1단계: SQL 생성",
        "",
        sql_context,
        "",
        "---",
        "",
        "## 2단계: 분석 도구 가이드",
        "",
        tool_guide,
        "",
        "---",
        "",
        "## 3단계: 가설 프레임워크",
        "",
        hypothesis,
        "",
        "---",
        "",
        "## 4단계: 분석 방향",
        "",
        analysis_guide,
        "",
        "---",
        "",
        "## 다음 실행 순서",
        "",
        *next_steps,
    ]

    return "\n".join(lines)
