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

_CHART_GUIDE: dict[str, dict[str, list[str]]] = {
    "tableau": {
        "line": [
            "**1단계: 데이터 소스 연결** — 상단 메뉴 Data > New Data Source",
            "**2단계: 날짜 필드 배치** — `{col0}` 필드를 Columns Shelf로 드래그",
            "**3단계: 수치 필드 배치** — `{col1}` 필드를 Rows Shelf로 드래그",
            "**4단계: 날짜 집계 설정** — Columns의 `{col0}` 우클릭 > Month 선택",
            "**5단계: 차트 타입** — Show Me 패널 > Lines (Continuous) 선택",
            "**6단계: 포맷** — 제목 더블클릭 편집, 축 우클릭 > Format으로 단위 설정",
        ],
        "bar": [
            "**1단계: 데이터 소스 연결** — Data > New Data Source",
            "**2단계: 범주 필드 배치** — `{col0}` 필드를 Columns Shelf로 드래그",
            "**3단계: 수치 필드 배치** — `{col1}` 필드를 Rows Shelf로 드래그",
            "**4단계: 정렬** — Rows Shelf의 `{col1}` 우클릭 > Sort > Descending",
            "**5단계: 차트 타입** — Show Me > Horizontal Bars 또는 Vertical Bars 선택",
        ],
        "pie": [
            "**1단계: 데이터 소스 연결** — Data > New Data Source",
            "**2단계: 범주 필드** — `{col0}` 필드를 Marks 카드의 Color 슬롯으로 드래그",
            "**3단계: 수치 필드** — `{col1}` 필드를 Marks 카드의 Angle 슬롯으로 드래그",
            "**4단계: 차트 타입** — Show Me > Pie Chart 선택",
            "**5단계: 레이블** — Marks > Label 체크, 비율(%) 표시 설정",
        ],
        "kpi": [
            "**1단계: 데이터 소스 연결** — Data > New Data Source",
            "**2단계: 수치 필드 배치** — `{col0}` 필드를 Rows Shelf로 드래그",
            "**3단계: 차트 타입** — Show Me > Text Table 선택",
            "**4단계: 크게 표시** — Marks 카드에서 Label 선택, 폰트 크기 키우기",
            "**5단계: 불필요한 축 제거** — 축 우클릭 > Hide Field Labels",
        ],
        "scatter": [
            "**1단계: 데이터 소스 연결** — Data > New Data Source",
            "**2단계: X축 수치 배치** — `{col0}` 필드를 Columns Shelf로 드래그",
            "**3단계: Y축 수치 배치** — `{col1}` 필드를 Rows Shelf로 드래그",
            "**4단계: 차트 타입** — Show Me > Scatter Plot 선택",
            "**5단계: 구분 색상** — 범주 필드를 Marks > Color 슬롯으로 드래그 (선택)",
        ],
        "heatmap": [
            "**1단계: 데이터 소스 연결** — Data > New Data Source",
            "**2단계: 행 차원** — `{col0}` 필드를 Rows Shelf로 드래그",
            "**3단계: 열 차원** — `{col1}` 필드를 Columns Shelf로 드래그",
            "**4단계: 색상 값** — 수치 필드를 Marks > Color 슬롯으로 드래그",
            "**5단계: 차트 타입** — Show Me > Heat Map 선택",
        ],
        "general": [
            "**1단계: 데이터 소스 연결** — Data > New Data Source > 소스 유형 선택",
            "**2단계: 필드 배치** — 왼쪽 Data 패널에서 필드를 Columns/Rows Shelf로 드래그",
            "**3단계: 차트 타입 선택** — 우측 Show Me 패널에서 원하는 차트 클릭",
            "**4단계: Marks 카드 조정** — Color, Size, Label 슬롯에 필드 추가",
            "**5단계: 포맷** — Format 메뉴로 제목, 축, 색상 조정",
        ],
    },
    "powerbi": {
        "line": [
            "**1단계: 데이터 불러오기** — Home > Get Data > 소스 선택",
            "**2단계: 시각화 선택** — Visualizations 패널에서 Line chart 아이콘 클릭",
            "**3단계: 날짜 필드 배치** — Fields 패널에서 `{col0}`을 Axis 버킷으로 드래그",
            "**4단계: 수치 필드 배치** — `{col1}`을 Values 버킷으로 드래그",
            "**5단계: 날짜 계층** — Axis의 `{col0}` 드롭다운 > 월(Month) 선택",
            "**6단계: 포맷** — Format pane(페인트브러시 아이콘)에서 제목·색상 조정",
        ],
        "bar": [
            "**1단계: 데이터 불러오기** — Home > Get Data",
            "**2단계: 시각화 선택** — Visualizations > Bar chart (가로) 또는 Column chart (세로) 선택",
            "**3단계: 범주 배치** — `{col0}`을 Axis 버킷으로 드래그",
            "**4단계: 수치 배치** — `{col1}`을 Values 버킷으로 드래그",
            "**5단계: 정렬** — Visual 우측 상단 ⋯ > Sort by `{col1}` > Sort descending",
        ],
        "pie": [
            "**1단계: 데이터 불러오기** — Home > Get Data",
            "**2단계: 시각화 선택** — Visualizations > Pie chart 또는 Donut chart",
            "**3단계: 범주 배치** — `{col0}`을 Legend 버킷으로 드래그",
            "**4단계: 수치 배치** — `{col1}`을 Values 버킷으로 드래그",
            "**5단계: 레이블** — Format pane > Detail labels > Value, Percent 표시",
        ],
        "kpi": [
            "**1단계: 데이터 불러오기** — Home > Get Data",
            "**2단계: 시각화 선택** — Visualizations > Card visual 선택",
            "**3단계: 수치 배치** — `{col0}`을 Fields 버킷으로 드래그",
            "**4단계: 집계 설정** — 버킷의 필드 드롭다운 > 집계 방식 선택(Sum/Average)",
            "**5단계: 포맷** — Format pane에서 폰트 크기, 단위(K/M) 설정",
        ],
        "scatter": [
            "**1단계: 데이터 불러오기** — Home > Get Data",
            "**2단계: 시각화 선택** — Visualizations > Scatter chart",
            "**3단계: X축 배치** — `{col0}`을 X Axis 버킷으로 드래그",
            "**4단계: Y축 배치** — `{col1}`을 Y Axis 버킷으로 드래그",
            "**5단계: 범주 색상** — 범주 필드를 Legend 버킷으로 드래그 (선택)",
        ],
        "heatmap": [
            "**1단계: 데이터 불러오기** — Home > Get Data",
            "**2단계: 시각화 선택** — Visualizations > Matrix",
            "**3단계: 행 배치** — `{col0}`을 Rows 버킷으로 드래그",
            "**4단계: 열 배치** — `{col1}`을 Columns 버킷으로 드래그",
            "**5단계: 값 배치** — 수치 필드를 Values 버킷으로 드래그",
            "**6단계: 조건부 서식** — Format pane > Cell elements > Background color 활성화",
        ],
        "general": [
            "**1단계: 데이터 불러오기** — Home > Get Data > 소스 유형 선택",
            "**2단계: 시각화 선택** — Visualizations 패널에서 차트 아이콘 클릭",
            "**3단계: 필드 배치** — Fields 패널에서 필드를 Axis / Values / Legend 버킷으로 드래그",
            "**4단계: 집계 설정** — 버킷 필드 드롭다운 > 집계 방식 선택",
            "**5단계: 포맷** — Format pane(페인트브러시 탭)에서 서식 조정",
        ],
    },
    "quicksight": {
        "line": [
            "**1단계: 분석 생성** — QuickSight 콘솔 > New analysis > Dataset 선택",
            "**2단계: 시각화 추가** — AutoGraph 또는 좌측 Visual types > Line chart",
            "**3단계: X축 배치** — `{col0}` 필드를 X axis (Field well)로 드래그",
            "**4단계: Y축 배치** — `{col1}` 필드를 Value (Field well)로 드래그",
            "**5단계: 집계 설정** — X axis 필드 드롭다운 > Aggregate by Month",
            "**6단계: 공유** — 상단 Publish > Publish dashboard",
        ],
        "bar": [
            "**1단계: 분석 생성** — New analysis > Dataset 선택",
            "**2단계: 시각화 선택** — Visual types > Bar chart",
            "**3단계: X축 배치** — `{col0}`을 X axis Field well로 드래그",
            "**4단계: Y축 배치** — `{col1}`을 Value Field well로 드래그",
            "**5단계: 정렬** — Visual 상단 Sort 아이콘 클릭",
        ],
        "kpi": [
            "**1단계: 분석 생성** — New analysis > Dataset 선택",
            "**2단계: 시각화 선택** — Visual types > KPI",
            "**3단계: 값 배치** — `{col0}`을 Value Field well로 드래그",
            "**4단계: 비교값 배치** — 비교 기간 필드를 Comparison value로 드래그 (선택)",
            "**5단계: 포맷** — Format visual에서 접두/접미사, 소수 자리 설정",
        ],
        "heatmap": [
            "**1단계: 분석 생성** — New analysis > Dataset 선택",
            "**2단계: 시각화 선택** — Visual types > Heat Map",
            "**3단계: 행 배치** — `{col0}`을 Rows Field well로 드래그",
            "**4단계: 열 배치** — `{col1}`을 Columns Field well로 드래그",
            "**5단계: 값 배치** — 수치 필드를 Values Field well로 드래그",
        ],
        "general": [
            "**1단계: 분석 생성** — New analysis > Dataset 선택",
            "**2단계: AutoGraph 활용** — 필드를 Field well로 드래그하면 QuickSight가 적합한 차트 자동 선택",
            "**3단계: 차트 타입 변경** — 좌측 Visual types 패널에서 원하는 타입 클릭",
            "**4단계: 필드 배치** — X axis / Value / Color Field well에 필드 드래그",
            "**5단계: 공유** — Publish > Publish dashboard > 사용자/그룹 지정",
        ],
    },
    "looker": {
        "line": [
            "**1단계: 보고서 생성** — Looker Studio > Create > Report > 데이터 소스 연결",
            "**2단계: 차트 추가** — Add a chart > Time series 또는 Line chart 선택",
            "**3단계: 날짜 Dimension 배치** — Setup 탭 > Dimension에 `{col0}` 추가",
            "**4단계: 수치 Metric 배치** — Metric에 `{col1}` 추가",
            "**5단계: 집계 설정** — Metric 필드 옆 집계 드롭다운 > SUM/AVG 선택",
            "**6단계: 공유** — 우측 상단 Share > 이메일 또는 링크 공유",
        ],
        "bar": [
            "**1단계: 보고서 생성** — Create > Report > 데이터 소스 연결",
            "**2단계: 차트 추가** — Add a chart > Bar chart 또는 Column chart 선택",
            "**3단계: Dimension 배치** — Setup > Dimension에 `{col0}` 추가",
            "**4단계: Metric 배치** — Metric에 `{col1}` 추가",
            "**5단계: 정렬** — Setup > Sort > `{col1}` Descending",
        ],
        "pie": [
            "**1단계: 보고서 생성** — Create > Report > 데이터 소스 연결",
            "**2단계: 차트 추가** — Add a chart > Pie chart 또는 Donut chart 선택",
            "**3단계: Dimension 배치** — Setup > Dimension에 `{col0}` 추가",
            "**4단계: Metric 배치** — Metric에 `{col1}` 추가",
            "**5단계: 레이블** — Style 탭 > Show data labels 체크",
        ],
        "kpi": [
            "**1단계: 보고서 생성** — Create > Report > 데이터 소스 연결",
            "**2단계: 차트 추가** — Add a chart > Scorecard 선택",
            "**3단계: Metric 배치** — Setup > Metric에 `{col0}` 추가",
            "**4단계: 비교** — Comparison date range 설정 (선택)",
            "**5단계: 포맷** — Style 탭 > Compact numbers, Prefix/Suffix 설정",
        ],
        "heatmap": [
            "**1단계: 보고서 생성** — Create > Report > 데이터 소스 연결",
            "**2단계: 차트 추가** — Add a chart > Pivot table 선택",
            "**3단계: 행 Dimension** — Setup > Row dimension에 `{col0}` 추가",
            "**4단계: 열 Dimension** — Column dimension에 `{col1}` 추가",
            "**5단계: 값 Metric** — Metric에 수치 필드 추가",
            "**6단계: 히트맵 색상** — Style > Heatmap 활성화",
        ],
        "general": [
            "**1단계: 보고서 생성** — Looker Studio > Create > Report",
            "**2단계: 데이터 소스 연결** — 팝업에서 Connector 선택 (BigQuery/Sheets/GA4 등)",
            "**3단계: 차트 추가** — 상단 Add a chart > 차트 타입 선택",
            "**4단계: 필드 배치** — 우측 Setup 탭 > Dimension / Metric 슬롯에 필드 추가",
            "**5단계: 포맷** — Style 탭에서 색상, 폰트, 레이블 조정",
        ],
    },
}

_CALC_KEYWORDS: list[str] = [
    "최초", "첫번째", "min", "max", "최솟값", "최댓값",
    "mom", "전월", "전기", "성장률", "증감률",
    "누적합", "running sum", "러닝",
    "비율", "전체 대비", "퍼센트",
    "이동 평균", "7일 평균", "moving avg",
    "순위", "랭킹", "rank",
    "조건부", "if 계산", "case",
    "lod", "세부 수준", "fixed", "include", "exclude",
    "dax", "측정값", "measure", "계산 필드", "calculated field",
    "수식", "formula", "함수 작성",
]

_FEATURE_KEYWORDS: list[str] = [
    "매개변수", "parameter",
    "집합", "set",
    "그룹", "group", "묶기",
    "드릴다운", "drill", "계층", "hierarchy",
    "액션", "action", "클릭 연결",
    "북마크", "bookmark",
    "슬라이서", "slicer",
    "크로스 필터", "cross filter",
    "퍼블리시", "배포", "공유",
    "인터랙티브 필터",
]

_TROUBLESHOOT_KEYWORDS: list[str] = [
    "오류", "에러", "error", "안 된다", "안됨", "실패",
    "연결 안", "connection", "인증", "oauth",
    "차트 안 나", "빈 차트", "안 보임",
    "값이 이상", "결과 이상", "틀림", "다름",
    "함수 오류", "수식 오류", "invalid",
    "null", "빈값", "0으로",
    "두 배", "overcounting", "중복",
    "새로고침", "refresh", "업데이트 안",
]


def _parse_columns(columns: str) -> list[str]:
    """컬럼 문자열 파싱 → 리스트."""
    if not columns:
        return []
    import json
    try:
        parsed = json.loads(columns)
        if isinstance(parsed, list):
            return [str(c).strip() for c in parsed]
    except (json.JSONDecodeError, ValueError):
        pass
    return [c.strip() for c in columns.split(",") if c.strip()]


def _inject_columns(template: str, col_list: list[str]) -> str:
    """템플릿의 {col0}, {col1} 플레이스홀더에 컬럼명 주입."""
    for i, col in enumerate(col_list):
        template = template.replace(f"{{col{i}}}", col)
    return template


def _classify_intent(intent: str, situation: str) -> str:
    """intent + situation → 모드 결정.

    Returns: 'chart' | 'calc' | 'feature' | 'troubleshoot'
    """
    # situation 있으면 트러블슈팅 우선
    if situation.strip():
        return "troubleshoot"

    intent_lower = intent.lower()

    # 트러블슈팅 키워드
    if any(kw in intent_lower for kw in _TROUBLESHOOT_KEYWORDS):
        return "troubleshoot"

    # 계산/수식 키워드
    if any(kw in intent_lower for kw in _CALC_KEYWORDS):
        return "calc"

    # 기능 사용 키워드
    if any(kw in intent_lower for kw in _FEATURE_KEYWORDS):
        return "feature"

    # 기본: 차트 생성 모드
    return "chart"


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
    mode = _classify_intent(intent, situation)
    if mode == "chart":
        return _mode_chart(intent, columns, tool)
    if mode == "calc":
        return _mode_calc(intent, columns, tool)
    if mode == "feature":
        return _mode_feature(intent, tool)
    return _mode_troubleshoot(intent, situation, tool)


def _mode_chart(intent: str, columns: str, tool: str) -> str:
    """차트 생성 가이드 반환."""
    chart_type = _fuzzy_match_chart(intent)
    col_list = _parse_columns(columns)

    tool_guide = _CHART_GUIDE.get(tool, {})
    steps = tool_guide.get(chart_type) or tool_guide.get("general", [])

    chart_name = _CHART_NAMES.get(chart_type, "차트")
    tool_upper = tool.upper() if tool != "looker" else "Looker Studio"

    header = f"## {tool_upper} — {chart_name}"
    if chart_type == "general":
        header += f"\n\n> '{intent}'에 대한 정확한 차트 매핑이 없습니다. 일반적인 차트 생성 워크플로우를 안내합니다."

    if col_list:
        formatted_steps = [_inject_columns(step, col_list) for step in steps]
    else:
        formatted_steps = [
            s.replace("{col0}", "<날짜/범주 필드>").replace("{col1}", "<수치 필드>")
            for s in steps
        ]

    lines = [header, ""] + formatted_steps
    if tool in _TOOL_DOCS:
        lines += ["", f"📖 공식 문서: {_TOOL_DOCS[tool]}"]

    return "\n".join(lines)


def _mode_calc(intent: str, columns: str, tool: str) -> str:
    return f"## {tool.upper()} 계산 가이드\n\n(Task 5에서 구현)"


def _mode_feature(intent: str, tool: str) -> str:
    return f"## {tool.upper()} 기능 가이드\n\n(Task 6에서 구현)"


def _mode_troubleshoot(intent: str, situation: str, tool: str) -> str:
    return f"## {tool.upper()} 트러블슈팅\n\n(Task 7에서 구현)"


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
