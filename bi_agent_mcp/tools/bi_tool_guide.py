"""[Helper] BI 툴 시각화 가이드 — 차트/계산/기능/트러블슈팅 단계별 안내."""
from __future__ import annotations

_SUPPORTED_TOOLS = {"tableau", "powerbi", "quicksight", "looker"}

_TOOL_DOCS: dict[str, str] = {
    "tableau": "https://help.tableau.com/current/pro/desktop/en-us/",
    "powerbi": "https://learn.microsoft.com/en-us/power-bi/",
    "quicksight": "https://docs.aws.amazon.com/quicksight/latest/user/",
    "looker": "https://support.google.com/looker-studio/",
}

_CHART_KEYWORDS: dict[str, list[str]] = {
    "line":        ["추이", "변화", "트렌드", "시계열", "선", "라인", "time series"],
    "bar":         ["비교", "순위", "막대", "바", "bar"],
    "stacked_bar": ["누적 막대", "누적 바", "stacked"],
    "pie":         ["비율", "구성", "파이", "원형", "도넛", "pie", "donut"],
    "scatter":     ["상관", "분포", "산점", "scatter"],
    "map":         ["지역", "지도", "맵", "위치", "map"],
    "funnel":      ["퍼널", "전환", "이탈", "funnel"],
    "heatmap":     ["코호트", "리텐션", "히트맵", "heatmap"],
    "kpi":         ["kpi", "요약", "핵심지표", "카드", "scorecard"],
    "histogram":   ["히스토그램", "histogram"],
    "treemap":     ["트리맵", "treemap"],
    "waterfall":   ["워터폴", "waterfall", "증감"],
    "area":        ["영역", "면적", "area"],
    "combo":       ["이중축", "dual", "combo", "혼합"],
}

_TOOL_DESCRIPTIONS: dict[str, str] = {
    "tableau": "드래그앤드롭으로 가장 직관적. Show Me 패널로 차트 자동 추천",
    "powerbi": "Excel 경험자에게 친숙한 UI. DAX 수식으로 강력한 계산",
    "quicksight": "AWS 데이터 소스 네이티브 연동. SPICE 인메모리 고속 처리",
    "looker": "Google 생태계 연동 강점. 다중 데이터 소스 Blend 지원",
}

_CHART_NAMES: dict[str, str] = {
    "line": "라인 차트 (시계열 추이)",
    "bar": "바/컬럼 차트 (범주 비교)",
    "stacked_bar": "누적 막대 차트 (구성 비교)",
    "pie": "파이/도넛 차트 (비율)",
    "scatter": "산점도 (상관관계)",
    "map": "지도 차트 (지리 분포)",
    "funnel": "퍼널 차트 (단계별 전환)",
    "heatmap": "히트맵 / 피벗 테이블 (코호트)",
    "kpi": "KPI 카드 / 스코어카드",
    "histogram": "히스토그램 (빈도 분포)",
    "treemap": "트리맵 (계층 구조)",
    "waterfall": "워터폴 차트 (누적 증감)",
    "area": "영역 차트 (추이 + 크기)",
    "combo": "콤보 차트 (이중 축)",
    "general": "범용 차트",
}


def bi_tool_guide(
    intent: str,
    columns: str = "",
    tool: str = "",
    situation: str = "",
) -> str:
    """[Helper] BI 툴 시각화 가이드.

    tool 미지정 → 차트 타입 추천 + 4개 툴 비교
    tool 지정   → 5개 모드(차트/계산/기능/트러블슈팅) 중 적합한 가이드 반환
    매핑 안 됨  → 폴백 가이드 반환 (에러 아님)

    Args:
        intent: 필수. "월별 매출 추이를 보고 싶다", "고객별 최초구매일 구하기"
        columns: 선택. "date, revenue, region" 또는 JSON
        tool: 선택. "tableau" / "powerbi" / "quicksight" / "looker"
        situation: 선택. 트러블슈팅 키워드. "연결 오류", "함수 오류"
    """
    if not intent or not intent.strip():
        return "[ERROR] intent는 필수 파라미터입니다. 예: '월별 매출 추이를 보고 싶다'"

    tool_lower = tool.strip().lower()
    if tool_lower and tool_lower not in _SUPPORTED_TOOLS:
        return (
            f"[ERROR] 지원하지 않는 툴입니다: '{tool}'. "
            "tool은 tableau / powerbi / quicksight / looker 중 하나여야 합니다."
        )

    if not tool_lower:
        return _mode_recommend(intent.strip(), columns.strip())

    return _dispatch(intent.strip(), columns.strip(), tool_lower, situation.strip())


def _dispatch(intent: str, columns: str, tool: str, situation: str) -> str:
    """모드 분기 — 추후 구현."""
    return f"## {tool.upper()} 가이드\n\n(구현 중)"


def _fuzzy_match_chart(intent: str) -> str:
    """intent에서 chart_type 퍼지 매칭. 없으면 'general' 반환."""
    intent_lower = intent.lower()
    for chart_type, keywords in _CHART_KEYWORDS.items():
        for kw in keywords:
            if kw in intent_lower:
                return chart_type
    return "general"


def _chart_reason(chart_type: str) -> str:
    reasons = {
        "line": "시간 축 변화 추이를 보기에 가장 직관적입니다.",
        "bar": "범주 간 값을 비교할 때 가장 효과적입니다.",
        "stacked_bar": "전체 구성과 각 부분의 크기를 동시에 볼 수 있습니다.",
        "pie": "전체 대비 비율을 한눈에 보여줍니다. 카테고리가 5개 이하일 때 권장.",
        "scatter": "두 변수 간의 상관관계와 군집을 발견할 수 있습니다.",
        "map": "지리적 분포와 지역별 차이를 시각화합니다.",
        "funnel": "단계별 전환율과 이탈이 가장 많은 구간을 확인합니다.",
        "heatmap": "코호트별 리텐션이나 매트릭스 형태의 데이터를 표현합니다.",
        "kpi": "단일 핵심 지표를 강조해서 보여줍니다.",
        "histogram": "연속 데이터의 분포와 빈도를 확인합니다.",
        "treemap": "계층 구조 데이터를 면적으로 표현합니다.",
        "waterfall": "증감 흐름과 누적 합계 추이를 보여줍니다.",
        "area": "추이와 함께 데이터 크기를 강조합니다.",
        "combo": "두 개의 지표를 서로 다른 축으로 비교합니다.",
    }
    return reasons.get(chart_type, "")


def _mode_recommend(intent: str, columns: str) -> str:
    """tool 미지정 — 차트 추천 + 4개 툴 비교."""
    chart_type = _fuzzy_match_chart(intent)
    chart_name = _CHART_NAMES.get(chart_type, "범용 차트")

    lines = [f"## BI 툴 가이드: {intent}", ""]

    if chart_type != "general":
        lines += [f"### 추천 차트: **{chart_name}**", ""]
        lines += [_chart_reason(chart_type), ""]
    else:
        lines += ["### 차트 타입을 특정하지 못했습니다", ""]
        lines += ["아래 툴 중 하나를 선택하면 일반적인 차트 생성 방법을 안내합니다.", ""]

    lines += ["### 툴별 특징", ""]
    for tool_key, desc in _TOOL_DESCRIPTIONS.items():
        lines.append(f"- **{tool_key}**: {desc}")

    lines += [
        "",
        "### 다음 단계",
        "",
        "툴을 선택하면 단계별 상세 가이드를 제공합니다:",
        "```",
        f'bi_tool_guide(intent="{intent}", tool="tableau")',
        f'bi_tool_guide(intent="{intent}", tool="powerbi")',
        f'bi_tool_guide(intent="{intent}", tool="quicksight")',
        f'bi_tool_guide(intent="{intent}", tool="looker")',
        "```",
    ]
    return "\n".join(lines)
