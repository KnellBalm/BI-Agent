# bi_tool_guide() Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** BI 툴을 모르는 사용자가 자연어 의도만으로 Tableau/Power BI/QuickSight/Looker Studio의 차트 생성, 계산 수식, 기능 사용, 트러블슈팅 가이드를 얻을 수 있는 MCP 도구를 구현한다.

**Architecture:** 단일 함수 `bi_tool_guide(intent, columns, tool, situation)`가 내부에서 5개 모드(추천/차트생성/계산수식/기능사용/트러블슈팅)를 분기 처리한다. `_classify_intent()`가 모드를 결정하고, 각 모드 함수가 툴별 딕셔너리에서 단계를 조회해 마크다운 문자열을 반환한다. 매핑 안 된 케이스는 항상 폴백으로 처리 — `[ERROR]`는 잘못된 입력(intent 비어있음, 지원 안 되는 툴)에만 사용한다.

**Tech Stack:** Python 3.11+, FastMCP (기존 패턴 유지), 외부 의존성 추가 없음

---

## 파일 구조

| 액션 | 경로 | 역할 |
|------|------|------|
| Create | `bi_agent_mcp/tools/bi_tool_guide.py` | 메인 구현 — 키워드 딕셔너리, 분기 로직, 5개 모드 함수 |
| Modify | `bi_agent_mcp/server.py` | `bi_tool_guide` 등록 |
| Create | `tests/unit/test_bi_tool_guide.py` | 20개+ 단위 테스트 |

---

## Task 1: 기본 골격 + 에러 케이스 (TDD)

**Files:**
- Create: `bi_agent_mcp/tools/bi_tool_guide.py`
- Create: `tests/unit/test_bi_tool_guide.py`

- [ ] **Step 1: 실패하는 에러 케이스 테스트 작성**

`tests/unit/test_bi_tool_guide.py`:

```python
"""bi_tool_guide 단위 테스트."""
import pytest
from bi_agent_mcp.tools.bi_tool_guide import bi_tool_guide


class TestErrors:
    def test_empty_intent_returns_error(self):
        result = bi_tool_guide(intent="")
        assert "[ERROR]" in result
        assert "intent" in result

    def test_unknown_tool_returns_error(self):
        result = bi_tool_guide(intent="차트 만들기", tool="powerpoint")
        assert "[ERROR]" in result
        assert "tableau" in result.lower() or "지원하지 않는" in result

    def test_whitespace_intent_returns_error(self):
        result = bi_tool_guide(intent="   ")
        assert "[ERROR]" in result
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
python3 -m pytest tests/unit/test_bi_tool_guide.py -v 2>&1 | tail -10
```

Expected: `ModuleNotFoundError` 또는 `ImportError`

- [ ] **Step 3: 최소 골격 구현**

`bi_agent_mcp/tools/bi_tool_guide.py`:

```python
"""[Helper] BI 툴 시각화 가이드 — 차트/계산/기능/트러블슈팅 단계별 안내."""
from __future__ import annotations

_SUPPORTED_TOOLS = {"tableau", "powerbi", "quicksight", "looker"}

_TOOL_DOCS: dict[str, str] = {
    "tableau": "https://help.tableau.com/current/pro/desktop/en-us/",
    "powerbi": "https://learn.microsoft.com/en-us/power-bi/",
    "quicksight": "https://docs.aws.amazon.com/quicksight/latest/user/",
    "looker": "https://support.google.com/looker-studio/",
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


def _mode_recommend(intent: str, columns: str) -> str:
    """추천 모드 — 추후 구현."""
    return "## 추천\n\n(구현 중)"
```

- [ ] **Step 4: 에러 케이스 테스트 통과 확인**

```bash
python3 -m pytest tests/unit/test_bi_tool_guide.py::TestErrors -v
```

Expected: 3 passed

- [ ] **Step 5: 커밋**

```bash
git add bi_agent_mcp/tools/bi_tool_guide.py tests/unit/test_bi_tool_guide.py
git commit -m "feat: bi_tool_guide 골격 + 에러 케이스 (TDD)"
```

---

## Task 2: 추천 모드 (tool 미지정)

**Files:**
- Modify: `bi_agent_mcp/tools/bi_tool_guide.py`
- Modify: `tests/unit/test_bi_tool_guide.py`

- [ ] **Step 1: 추천 모드 테스트 작성**

`tests/unit/test_bi_tool_guide.py`에 추가:

```python
class TestRecommendMode:
    def test_no_tool_returns_chart_recommendation(self):
        result = bi_tool_guide(intent="월별 매출 추이를 보고 싶다")
        assert "라인" in result or "line" in result.lower()
        assert "tableau" in result.lower()
        assert "powerbi" in result.lower() or "power bi" in result.lower()

    def test_no_tool_pie_intent(self):
        result = bi_tool_guide(intent="카테고리별 비율을 보고 싶다")
        assert "파이" in result or "pie" in result.lower() or "도넛" in result

    def test_no_tool_unknown_intent_shows_general(self):
        result = bi_tool_guide(intent="완전히 모르는 의도")
        assert "tableau" in result.lower()
        assert "tool=" in result  # 다음 호출 안내 포함

    def test_no_tool_includes_next_step_hint(self):
        result = bi_tool_guide(intent="바 차트 만들기")
        assert "tool=" in result
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
python3 -m pytest tests/unit/test_bi_tool_guide.py::TestRecommendMode -v
```

Expected: 4 failed

- [ ] **Step 3: 추천 모드 구현**

`bi_tool_guide.py`에 추가/교체:

```python
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


def _fuzzy_match_chart(intent: str) -> str:
    """intent에서 chart_type 퍼지 매칭. 없으면 'general' 반환."""
    intent_lower = intent.lower()
    for chart_type, keywords in _CHART_KEYWORDS.items():
        for kw in keywords:
            if kw in intent_lower:
                return chart_type
    return "general"


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
```

- [ ] **Step 4: 추천 모드 테스트 통과 확인**

```bash
python3 -m pytest tests/unit/test_bi_tool_guide.py::TestRecommendMode -v
```

Expected: 4 passed

- [ ] **Step 5: 커밋**

```bash
git add bi_agent_mcp/tools/bi_tool_guide.py tests/unit/test_bi_tool_guide.py
git commit -m "feat: bi_tool_guide 추천 모드 구현"
```

---

## Task 3: 모드 분류기 (`_classify_intent`)

**Files:**
- Modify: `bi_agent_mcp/tools/bi_tool_guide.py`
- Modify: `tests/unit/test_bi_tool_guide.py`

- [ ] **Step 1: 분류기 테스트 작성**

```python
from bi_agent_mcp.tools.bi_tool_guide import _classify_intent

class TestClassifyIntent:
    def test_chart_intent(self):
        assert _classify_intent("라인 차트 만들기", "") == "chart"

    def test_calc_intent(self):
        assert _classify_intent("고객별 최초구매일 구하기", "") == "calc"

    def test_calc_mom_intent(self):
        assert _classify_intent("MoM 성장률 계산", "") == "calc"

    def test_feature_intent_parameter(self):
        assert _classify_intent("매개변수 만들기", "") == "feature"

    def test_feature_intent_set(self):
        assert _classify_intent("집합 생성", "") == "feature"

    def test_troubleshoot_via_situation(self):
        assert _classify_intent("뭔가 이상함", "연결 오류") == "troubleshoot"

    def test_troubleshoot_via_intent(self):
        assert _classify_intent("연결이 안 된다", "") == "troubleshoot"

    def test_unknown_defaults_to_chart(self):
        assert _classify_intent("완전히 모르는 의도", "") == "chart"
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
python3 -m pytest tests/unit/test_bi_tool_guide.py::TestClassifyIntent -v
```

Expected: 8 failed (ImportError 또는 함수 없음)

- [ ] **Step 3: 분류기 구현**

`bi_tool_guide.py`에 추가:

```python
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
```

`_dispatch` 함수 업데이트:

```python
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
    return f"## {tool.upper()} 차트 가이드\n\n(Task 4에서 구현)"


def _mode_calc(intent: str, columns: str, tool: str) -> str:
    return f"## {tool.upper()} 계산 가이드\n\n(Task 5에서 구현)"


def _mode_feature(intent: str, tool: str) -> str:
    return f"## {tool.upper()} 기능 가이드\n\n(Task 6에서 구현)"


def _mode_troubleshoot(intent: str, situation: str, tool: str) -> str:
    return f"## {tool.upper()} 트러블슈팅\n\n(Task 7에서 구현)"
```

- [ ] **Step 4: 분류기 테스트 통과 확인**

```bash
python3 -m pytest tests/unit/test_bi_tool_guide.py::TestClassifyIntent -v
```

Expected: 8 passed

- [ ] **Step 5: 커밋**

```bash
git add bi_agent_mcp/tools/bi_tool_guide.py tests/unit/test_bi_tool_guide.py
git commit -m "feat: bi_tool_guide _classify_intent 구현"
```

---

## Task 4: 모드 1 — 차트 생성 가이드

**Files:**
- Modify: `bi_agent_mcp/tools/bi_tool_guide.py`
- Modify: `tests/unit/test_bi_tool_guide.py`

- [ ] **Step 1: 차트 생성 모드 테스트 작성**

```python
class TestChartMode:
    def test_tableau_line_chart_with_columns(self):
        result = bi_tool_guide(
            intent="월별 매출 추이",
            tool="tableau",
            columns="date, revenue",
        )
        assert "Columns Shelf" in result or "Rows Shelf" in result
        assert "date" in result
        assert "revenue" in result
        assert "1단계" in result or "**1" in result

    def test_powerbi_bar_chart(self):
        result = bi_tool_guide(intent="카테고리별 비교", tool="powerbi")
        assert "Axis" in result or "Values" in result
        assert "1단계" in result or "**1" in result

    def test_quicksight_kpi(self):
        result = bi_tool_guide(intent="KPI 카드", tool="quicksight", columns="revenue")
        assert "KPI" in result or "AutoGraph" in result

    def test_looker_fallback_unknown_chart(self):
        result = bi_tool_guide(intent="간트 차트 만들기", tool="looker")
        assert "[ERROR]" not in result
        assert "간트" in result or "가이드" in result or "Looker" in result

    def test_tableau_fallback_unknown_chart(self):
        result = bi_tool_guide(intent="완전히 모르는 차트", tool="tableau")
        assert "[ERROR]" not in result
        assert "단계" in result or "Tableau" in result
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
python3 -m pytest tests/unit/test_bi_tool_guide.py::TestChartMode -v
```

Expected: 5 failed

- [ ] **Step 3: 컬럼 파싱 + 주입 헬퍼 구현**

```python
def _parse_columns(columns: str) -> list[str]:
    """컬럼 문자열 파싱 → 리스트."""
    if not columns:
        return []
    # JSON 형태 시도
    import json
    try:
        parsed = json.loads(columns)
        if isinstance(parsed, list):
            return [str(c).strip() for c in parsed]
    except (json.JSONDecodeError, ValueError):
        pass
    # 쉼표 구분
    return [c.strip() for c in columns.split(",") if c.strip()]


def _inject_columns(template: str, col_list: list[str]) -> str:
    """템플릿의 {col0}, {col1} 플레이스홀더에 컬럼명 주입."""
    for i, col in enumerate(col_list):
        template = template.replace(f"{{col{i}}}", col)
    return template
```

- [ ] **Step 4: 차트 가이드 데이터 + `_mode_chart` 구현**

```python
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
        formatted_steps = []
        for step in steps:
            s = _inject_columns(step, col_list)
            formatted_steps.append(s)
    else:
        formatted_steps = [
            s.replace("{col0}", "<날짜/범주 필드>").replace("{col1}", "<수치 필드>")
            for s in steps
        ]

    lines = [header, ""] + formatted_steps
    if tool in _TOOL_DOCS:
        lines += ["", f"📖 공식 문서: {_TOOL_DOCS[tool]}"]

    return "\n".join(lines)
```

- [ ] **Step 4: 차트 모드 테스트 통과 확인**

```bash
python3 -m pytest tests/unit/test_bi_tool_guide.py::TestChartMode -v
```

Expected: 5 passed

- [ ] **Step 5: 커밋**

```bash
git add bi_agent_mcp/tools/bi_tool_guide.py tests/unit/test_bi_tool_guide.py
git commit -m "feat: bi_tool_guide 차트 생성 모드 (4개 툴 × 주요 차트 타입)"
```

---

## Task 5: 모드 2 — 계산/수식 가이드

**Files:**
- Modify: `bi_agent_mcp/tools/bi_tool_guide.py`
- Modify: `tests/unit/test_bi_tool_guide.py`

- [ ] **Step 1: 계산 모드 테스트 작성**

```python
class TestCalcMode:
    def test_tableau_lod_min_per_dim(self):
        result = bi_tool_guide(
            intent="고객별 최초구매일 구하기",
            tool="tableau",
            columns="customer_id, purchase_date",
        )
        assert "FIXED" in result or "MIN" in result
        assert "customer_id" in result or "{col0}" not in result

    def test_powerbi_mom_growth(self):
        result = bi_tool_guide(
            intent="MoM 성장률 계산",
            tool="powerbi",
            columns="date, revenue",
        )
        assert "DAX" in result or "DATEADD" in result or "DIVIDE" in result

    def test_quicksight_running_total(self):
        result = bi_tool_guide(intent="누적합 계산", tool="quicksight")
        assert "[ERROR]" not in result
        assert "runningSum" in result or "누적" in result or "calculated" in result.lower()

    def test_looker_ratio(self):
        result = bi_tool_guide(intent="전체 대비 비율 계산", tool="looker")
        assert "[ERROR]" not in result
        assert "%" in result or "비율" in result or "Calculated Field" in result

    def test_unknown_calc_fallback(self):
        result = bi_tool_guide(intent="알 수 없는 계산 수식", tool="tableau")
        # _classify_intent이 calc로 분류 안 되면 chart 폴백으로 감 — 테스트는 에러 없음만 확인
        assert "[ERROR]" not in result
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
python3 -m pytest tests/unit/test_bi_tool_guide.py::TestCalcMode -v
```

Expected: 일부 failed (구현 중 placeholder 반환)

- [ ] **Step 3: 계산 가이드 데이터 + `_mode_calc` 구현**

```python
_CALC_TYPE_KEYWORDS: dict[str, list[str]] = {
    "min_per_dim":   ["최초", "첫번째", "min", "최솟값", "earliest", "first purchase"],
    "max_per_dim":   ["마지막", "최근", "max", "최댓값", "latest", "last"],
    "mom_growth":    ["mom", "전월", "전기 대비", "성장률", "증감률", "month over month"],
    "running_total": ["누적합", "running sum", "러닝", "cumulative"],
    "ratio":         ["비율", "전체 대비", "퍼센트", "proportion", "% of total"],
    "moving_avg":    ["이동 평균", "7일 평균", "rolling", "moving avg"],
    "rank":          ["순위", "랭킹", "rank"],
    "conditional":   ["조건부", "if 계산", "case", "when"],
    "lod":           ["lod", "세부 수준", "fixed", "include", "exclude"],
    "dax_measure":   ["dax", "측정값", "measure"],
}

_CALC_GUIDE: dict[str, dict[str, list[str]]] = {
    "tableau": {
        "min_per_dim": [
            "**방법: LOD Expression (FIXED)**",
            "",
            "Analysis 메뉴 > Create Calculated Field 클릭",
            "이름 입력: `{col0}_최초_{col1}`",
            "수식 입력:",
            "```",
            "{{FIXED [{col0}] : MIN([{col1}])}}",
            "```",
            "OK 클릭 → Data 패널에 새 필드 생성됨",
            "",
            "> 참고: `FIXED`는 뷰 필터와 독립적으로 `{col0}` 기준으로 `{col1}`의 최솟값을 계산합니다.",
        ],
        "mom_growth": [
            "**방법: Table Calculation — LOOKUP**",
            "",
            "Analysis > Create Calculated Field",
            "이름: `MoM 성장률`",
            "수식:",
            "```",
            "(SUM([{col1}]) - LOOKUP(SUM([{col1}]), -1)) / ABS(LOOKUP(SUM([{col1}]), -1))",
            "```",
            "날짜 필드를 Columns Shelf에 Month 단위로 배치 후 이 필드를 뷰에 추가",
            "필드 우클릭 > Edit Table Calculation > Compute using: Date",
        ],
        "running_total": [
            "**방법: Table Calculation — RUNNING_SUM**",
            "",
            "Analysis > Create Calculated Field",
            "이름: `누적 {col1}`",
            "수식:",
            "```",
            "RUNNING_SUM(SUM([{col1}]))",
            "```",
            "필드 우클릭 > Edit Table Calculation > 집계 방향 확인",
        ],
        "ratio": [
            "**방법: TOTAL() 또는 FIXED LOD**",
            "",
            "Analysis > Create Calculated Field",
            "이름: `{col1} 비율`",
            "수식 (뷰 레벨 기준):",
            "```",
            "SUM([{col1}]) / TOTAL(SUM([{col1}]))",
            "```",
            "또는 전체 기준:",
            "```",
            "SUM([{col1}]) / {{FIXED : SUM([{col1}])}}",
            "```",
        ],
        "rank": [
            "**방법: RANK() Table Calculation**",
            "",
            "Analysis > Create Calculated Field",
            "이름: `{col0} 순위`",
            "수식:",
            "```",
            "RANK(SUM([{col1}]))",
            "```",
            "필드 우클릭 > Edit Table Calculation > Compute using: {col0}",
            "내림차순 정렬: RANK(SUM([{col1}]), 'desc')",
        ],
        "general_calc": [
            "**계산 필드 생성 방법**",
            "",
            "1. Analysis 메뉴 > Create Calculated Field",
            "2. 이름 입력 후 수식 작성",
            "3. 편집기 하단 'The calculation is valid' 확인",
            "4. OK 클릭 → Data 패널에 새 필드 생성",
            "",
            "주요 계산 타입:",
            "- Basic: `[Sales] * 1.1`",
            "- Aggregate: `AVG([Discount])`",
            "- Table Calc: `RUNNING_SUM(SUM([Sales]))`",
            "- LOD: `{FIXED [Region] : SUM([Sales])}`",
        ],
    },
    "powerbi": {
        "min_per_dim": [
            "**방법: DAX MINX + FILTER**",
            "",
            "Modeling 탭 > New Measure",
            "수식:",
            "```dax",
            "{col0}_최초_{col1} =",
            "MINX(",
            "    FILTER('테이블', '테이블'[{col0}] = EARLIER('테이블'[{col0}])),",
            "    '테이블'[{col1}]",
            ")",
            "```",
            "또는 각 고객의 최초일을 별도 테이블로 계산:",
            "```dax",
            "최초_{col1} = MINX(RELATEDTABLE('주문테이블'), '주문테이블'[{col1}])",
            "```",
        ],
        "mom_growth": [
            "**방법: DAX DATEADD + DIVIDE**",
            "",
            "Modeling > New Measure",
            "수식:",
            "```dax",
            "전월_{col1} =",
            "CALCULATE(",
            "    SUM('테이블'[{col1}]),",
            "    DATEADD('날짜테이블'[Date], -1, MONTH)",
            ")",
            "",
            "MoM_성장률 =",
            "DIVIDE(",
            "    SUM('테이블'[{col1}]) - [전월_{col1}],",
            "    [전월_{col1}]",
            ")",
            "```",
        ],
        "running_total": [
            "**방법: DAX CALCULATE + FILTER**",
            "",
            "Modeling > New Measure",
            "수식:",
            "```dax",
            "누적_{col1} =",
            "CALCULATE(",
            "    SUM('테이블'[{col1}]),",
            "    FILTER(",
            "        ALL('날짜테이블'),",
            "        '날짜테이블'[Date] <= MAX('날짜테이블'[Date])",
            "    )",
            ")",
            "```",
        ],
        "ratio": [
            "**방법: DAX DIVIDE + ALL**",
            "",
            "Modeling > New Measure",
            "수식:",
            "```dax",
            "{col1}_비율 =",
            "DIVIDE(",
            "    SUM('테이블'[{col1}]),",
            "    CALCULATE(SUM('테이블'[{col1}]), ALL('테이블'))",
            ")",
            "```",
        ],
        "rank": [
            "**방법: DAX RANKX**",
            "",
            "Modeling > New Measure",
            "수식:",
            "```dax",
            "{col0}_순위 =",
            "RANKX(",
            "    ALL('테이블'[{col0}]),",
            "    SUM('테이블'[{col1}]),",
            "    ,",
            "    DESC",
            ")",
            "```",
        ],
        "general_calc": [
            "**Power BI 계산 필드 생성 방법**",
            "",
            "1. Modeling 탭 > New Measure 클릭",
            "2. 수식 표시줄에 DAX 수식 입력",
            "3. 측정값은 Fields 패널에 계산기 아이콘으로 표시됨",
            "",
            "주요 DAX 함수:",
            "- `SUM([col])`, `AVERAGE([col])`, `COUNT([col])`",
            "- `CALCULATE(expr, filter)` — 필터 컨텍스트 수정",
            "- `DIVIDE(a, b)` — 0으로 나누기 안전 처리",
            "- `DATEADD(date, n, MONTH)` — 날짜 이동",
        ],
    },
    "quicksight": {
        "min_per_dim": [
            "**방법: Calculated Field — min() 집계**",
            "",
            "Data pane 상단 Add calculated field 클릭",
            "이름: `{col0}_최초_{col1}`",
            "수식:",
            "```",
            "min({col1})",
            "```",
            "Field well에서 `{col0}`을 그룹 Dimension으로, 생성된 필드를 Value로 배치",
        ],
        "mom_growth": [
            "**방법: periodOverPeriodDifference 함수**",
            "",
            "Data pane > Add calculated field",
            "이름: `MoM 성장률`",
            "수식:",
            "```",
            "periodOverPeriodDifference(sum({col1}), {col0}, MONTH, 1) /",
            "periodOverPeriodLastValue(sum({col1}), {col0}, MONTH, 1)",
            "```",
        ],
        "running_total": [
            "**방법: runningSum 함수**",
            "",
            "Data pane > Add calculated field",
            "이름: `누적_{col1}`",
            "수식:",
            "```",
            "runningSum(sum({col1}), [{col0} ASC])",
            "```",
        ],
        "general_calc": [
            "**QuickSight 계산 필드 생성 방법**",
            "",
            "1. 분석(Analysis) 화면에서 Data pane 상단 'Add calculated field' 클릭",
            "2. 필드명 입력 후 수식 에디터에서 함수/연산자/기존 필드 조합",
            "3. 'Apply' 클릭",
            "",
            "주요 함수:",
            "- `sum({col})`, `avg({col})`, `min({col})`, `max({col})`",
            "- `ifelse(condition, true_val, false_val)`",
            "- `dateDiff({date1}, {date2}, 'DD')`",
            "- `runningSum(sum({col}), [{date} ASC])`",
        ],
    },
    "looker": {
        "min_per_dim": [
            "**방법: Data Source에서 Calculated Field 생성**",
            "",
            "Resource > Manage added data sources > 데이터 소스 편집",
            "Add a field > 이름: `{col0}_최초_{col1}`",
            "수식 (BigQuery 기준):",
            "```sql",
            "MIN({col1}) OVER (PARTITION BY {col0})",
            "```",
            "또는 BigQuery 집계 후 조인 방식 권장",
        ],
        "mom_growth": [
            "**방법: Date comparison 기능 활용**",
            "",
            "차트의 Setup 탭 > Comparison date range 활성화",
            "또는 Calculated Field:",
            "이름: `MoM 성장률`",
            "수식 (BigQuery 기준):",
            "```",
            "(SUM({col1}) - SUM({col1}_prev)) / SUM({col1}_prev)",
            "```",
            "전월 데이터는 BigQuery에서 LAG 함수로 사전 처리 권장",
        ],
        "general_calc": [
            "**Looker Studio 계산 필드 생성 방법**",
            "",
            "1. 차트 선택 > Setup 탭 > Metric 영역 > Add field > Create field",
            "2. 또는 Resource > Manage added data sources > 데이터 소스 편집 > Add a field",
            "3. 필드명 입력 후 수식 작성",
            "",
            "주요 함수:",
            "- `SUM({col})`, `AVG({col})`, `MAX({col})`, `MIN({col})`",
            "- `CASE WHEN condition THEN val1 ELSE val2 END`",
            "- `CONCAT({col1}, ' ', {col2})`",
            "- 데이터 소스 레벨 계산 필드는 모든 차트에서 재사용 가능",
        ],
    },
}


def _fuzzy_match_calc(intent: str) -> str:
    """intent에서 calc_type 퍼지 매칭. 없으면 'general_calc' 반환."""
    intent_lower = intent.lower()
    for calc_type, keywords in _CALC_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in intent_lower:
                return calc_type
    return "general_calc"


def _mode_calc(intent: str, columns: str, tool: str) -> str:
    """계산/수식 가이드 반환."""
    calc_type = _fuzzy_match_calc(intent)
    col_list = _parse_columns(columns)

    tool_guide = _CALC_GUIDE.get(tool, {})
    steps = tool_guide.get(calc_type) or tool_guide.get("general_calc", [])

    tool_upper = tool.upper() if tool != "looker" else "Looker Studio"
    calc_labels = {
        "min_per_dim": "최솟값/최초값 (차원별)",
        "max_per_dim": "최댓값/최근값 (차원별)",
        "mom_growth": "전월 대비 성장률 (MoM)",
        "running_total": "누적합 (Running Total)",
        "ratio": "전체 대비 비율",
        "moving_avg": "이동 평균",
        "rank": "순위 (Rank)",
        "conditional": "조건부 계산",
        "lod": "세부 수준 계산 (LOD)",
        "dax_measure": "DAX 측정값",
        "general_calc": "계산 필드 (일반)",
    }
    calc_name = calc_labels.get(calc_type, "계산 필드")

    header = f"## {tool_upper} — {calc_name}"
    if calc_type == "general_calc":
        header += f"\n\n> '{intent}'에 대한 정확한 계산식 매핑이 없습니다. 계산 필드 생성 일반 방법을 안내합니다."

    formatted = []
    for step in steps:
        s = step
        for i, col in enumerate(col_list):
            s = s.replace(f"{{col{i}}}", col)
        # 미치환 플레이스홀더 처리
        import re
        s = re.sub(r"\{col\d+\}", "<필드명>", s)
        formatted.append(s)

    lines = [header, ""] + formatted
    if tool in _TOOL_DOCS:
        lines += ["", f"📖 공식 문서: {_TOOL_DOCS[tool]}"]

    return "\n".join(lines)
```

- [ ] **Step 4: 계산 모드 테스트 통과 확인**

```bash
python3 -m pytest tests/unit/test_bi_tool_guide.py::TestCalcMode -v
```

Expected: 5 passed

- [ ] **Step 5: 커밋**

```bash
git add bi_agent_mcp/tools/bi_tool_guide.py tests/unit/test_bi_tool_guide.py
git commit -m "feat: bi_tool_guide 계산/수식 모드 (LOD, DAX, runningSum 등)"
```

---

## Task 6: 모드 3 — 기능 사용 가이드

**Files:**
- Modify: `bi_agent_mcp/tools/bi_tool_guide.py`
- Modify: `tests/unit/test_bi_tool_guide.py`

- [ ] **Step 1: 기능 모드 테스트 작성**

```python
class TestFeatureMode:
    def test_tableau_parameter(self):
        result = bi_tool_guide(intent="매개변수 만들기", tool="tableau")
        assert "Parameter" in result or "매개변수" in result
        assert "1단계" in result or "**1" in result

    def test_tableau_set(self):
        result = bi_tool_guide(intent="집합 생성", tool="tableau")
        assert "Set" in result or "집합" in result

    def test_powerbi_slicer(self):
        result = bi_tool_guide(intent="슬라이서 추가", tool="powerbi")
        assert "Slicer" in result or "슬라이서" in result

    def test_unknown_feature_fallback(self):
        result = bi_tool_guide(intent="알 수 없는 기능 설정", tool="tableau")
        assert "[ERROR]" not in result
        assert "tableau" in result.lower() or "Tableau" in result
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
python3 -m pytest tests/unit/test_bi_tool_guide.py::TestFeatureMode -v
```

Expected: 4 failed

- [ ] **Step 3: 기능 가이드 데이터 + `_mode_feature` 구현**

```python
_FEATURE_TYPE_KEYWORDS: dict[str, list[str]] = {
    "parameter":       ["매개변수", "parameter", "파라미터"],
    "set":             ["집합", " set", "세트"],
    "group":           ["그룹", "group", "묶기"],
    "interactive_filter": ["인터랙티브 필터", "퀵 필터", "슬라이서", "slicer", "filter control"],
    "drill":           ["드릴다운", "drill", "계층", "hierarchy"],
    "action":          ["액션", "action", "클릭 연결", "url action"],
    "bookmark":        ["북마크", "bookmark", "custom view"],
    "publish":         ["퍼블리시", "배포", "공유", "publish", "share"],
    "cross_filter":    ["크로스 필터", "cross filter"],
}

_FEATURE_GUIDE: dict[str, dict[str, list[str]]] = {
    "tableau": {
        "parameter": [
            "**Tableau Parameter 생성**",
            "",
            "1. 왼쪽 Data 패널 빈 공간 우클릭 > Create Parameter",
            "2. 이름, 데이터 타입, 허용 값(전체/목록/범위) 설정",
            "3. OK 클릭 → Parameters 섹션에 생성됨",
            "4. 파라미터 우클릭 > Show Parameter → 뷰에 컨트롤 위젯 표시",
            "5. 계산 필드에서 파라미터 참조: `[파라미터명]`",
            "",
            "활용 예: 날짜 범위 파라미터로 동적 필터링",
            "```",
            "[Order Date] >= [Start Date Parameter] AND [Order Date] <= [End Date Parameter]",
            "```",
        ],
        "set": [
            "**Tableau Set 생성**",
            "",
            "**조건 기반 Set (동적):**",
            "1. Data 패널에서 Dimension 필드 우클릭 > Create > Set",
            "2. 'Condition' 탭 > 조건 설정 (예: SUM([Sales]) > 10000)",
            "3. OK 클릭",
            "",
            "**수동 선택 Set (정적):**",
            "1. Data 패널에서 Dimension 우클릭 > Create > Set",
            "2. 'General' 탭 > 원하는 멤버 체크박스 선택",
            "3. OK 클릭",
            "",
            "Set은 IN/OUT 두 값을 가지며, Marks > Color에 드래그하면 강조 표시 가능",
        ],
        "drill": [
            "**Tableau 계층(Hierarchy) 생성**",
            "",
            "1. Data 패널에서 부모 Dimension 필드 우클릭 > Hierarchy > Create Hierarchy",
            "2. 이름 입력 후 OK",
            "3. 자식 Dimension 필드를 계층 아래로 드래그",
            "4. Shelf에 계층 배치 후 + 버튼으로 드릴다운",
        ],
        "action": [
            "**Tableau Dashboard Action 생성**",
            "",
            "Dashboard > Actions > Add Action 클릭",
            "",
            "**Filter Action (클릭으로 다른 시트 필터링):**",
            "- Action type: Filter",
            "- Source sheet: 클릭할 시트 선택",
            "- Target sheet: 필터 적용될 시트 선택",
            "- Run action on: Select (클릭 시)",
            "",
            "**URL Action (외부 링크 열기):**",
            "- Action type: URL",
            "- URL에 필드 값 포함 가능: `https://example.com/<[Field]>`",
        ],
        "general_feature": [
            "**Tableau 주요 기능 목록**",
            "",
            "- **Parameter**: 사용자 입력 동적 변수 (Data 패널 우클릭 > Create Parameter)",
            "- **Set**: 조건 기반 데이터 부분집합 (Dimension 우클릭 > Create > Set)",
            "- **Group**: 여러 멤버를 하나로 묶기 (Dimension 우클릭 > Create > Group)",
            "- **Hierarchy**: 드릴다운 계층 구조 (우클릭 > Hierarchy > Create Hierarchy)",
            "- **Filter Action**: 클릭으로 다른 시트 필터링 (Dashboard > Actions)",
            "- **URL Action**: 클릭으로 외부 URL 열기",
            "- **Publish**: Server > Publish Workbook",
        ],
    },
    "powerbi": {
        "interactive_filter": [
            "**Power BI Slicer 추가**",
            "",
            "1. Visualizations 패널에서 Slicer 아이콘 클릭",
            "2. Fields 패널에서 필터할 필드를 Field 버킷으로 드래그",
            "3. Format pane > Slicer settings에서 스타일 선택:",
            "   - Dropdown: 드롭다운 목록",
            "   - List: 체크박스 목록",
            "   - Between: 숫자/날짜 범위 슬라이더",
            "4. 동일 페이지의 다른 시각화에 자동으로 필터 적용됨",
        ],
        "drill": [
            "**Power BI 드릴다운 설정**",
            "",
            "**Auto date/time 활용 (날짜 필드):**",
            "1. 날짜 필드를 Axis 버킷에 배치",
            "2. Fields 패널에서 날짜 필드 확장 > Date Hierarchy 확인",
            "3. 시각화 상단의 ▼ 아이콘으로 Year > Quarter > Month > Day 드릴다운",
            "",
            "**커스텀 계층:**",
            "1. Model view에서 Dimension 필드 드래그하여 계층 생성",
            "2. 상위 > 하위 순서로 배치",
        ],
        "bookmark": [
            "**Power BI Bookmark 생성**",
            "",
            "1. View 탭 > Bookmarks 패널 열기",
            "2. 원하는 필터/슬라이서 상태 설정",
            "3. Bookmarks 패널 > Add 클릭",
            "4. 북마크 이름 입력",
            "5. 버튼(Button)에 북마크 연결: Insert > Button > Action > Bookmark 선택",
        ],
        "general_feature": [
            "**Power BI 주요 기능 목록**",
            "",
            "- **Slicer**: 캔버스 위 인터랙티브 필터 위젯 (Visualizations > Slicer)",
            "- **Drillthrough**: 상세 페이지로 컨텍스트 이동 (Visual 우클릭 > Drillthrough)",
            "- **Bookmark**: 필터/슬라이서 상태 저장 (View > Bookmarks)",
            "- **Q&A**: 자연어 질의 시각화 (Insert > Q&A)",
            "- **Decomposition Tree**: AI 기반 다차원 탐색",
            "- **Publish**: Home > Publish > Workspace 선택",
        ],
    },
    "quicksight": {
        "interactive_filter": [
            "**QuickSight Filter Control 추가**",
            "",
            "1. 분석 화면 좌측 Filter 패널 열기 > Add filter 클릭",
            "2. 필터할 필드 선택",
            "3. 조건 설정 (값 선택, 날짜 범위 등)",
            "4. 'Add to sheet' 토글 활성화 → Sheet에 인터랙티브 컨트롤 위젯 표시",
        ],
        "publish": [
            "**QuickSight Dashboard 퍼블리시**",
            "",
            "1. 분석 완료 후 상단 Publish 버튼 클릭",
            "2. Publish dashboard 선택",
            "3. 대시보드 이름 입력",
            "4. 공유할 사용자/그룹 지정",
            "5. View 또는 Co-owner 권한 설정 후 Publish",
        ],
        "general_feature": [
            "**QuickSight 주요 기능 목록**",
            "",
            "- **Filter Control**: Sheet에 인터랙티브 필터 위젯 (Filter 패널 > Add to sheet)",
            "- **Parameter**: 동적 값 변수 (Manage parameters에서 생성)",
            "- **ML Insights**: 이상 탐지·예측 (Visual > Add Insight)",
            "- **Small Multiples**: 격자형 반복 차트",
            "- **Publish**: 상단 Publish 버튼 > Dashboard 이름·권한 설정",
        ],
    },
    "looker": {
        "interactive_filter": [
            "**Looker Studio Filter Control 추가**",
            "",
            "1. 보고서 편집 모드 > Add a control 클릭",
            "2. 컨트롤 유형 선택:",
            "   - Drop-down list: 단일/다중 선택",
            "   - Date Range Control: 날짜 범위",
            "   - Slider: 숫자 범위",
            "3. Setup 탭 > Control field 설정",
            "4. 컨트롤이 영향을 줄 차트 선택 (같은 데이터 소스의 차트 자동 연결)",
        ],
        "publish": [
            "**Looker Studio 보고서 공유**",
            "",
            "1. 우측 상단 Share 버튼 클릭",
            "2. 이메일 입력 후 View 또는 Edit 권한 부여",
            "3. 링크 공유: 'Change to anyone with the link' 설정",
            "4. PDF 내보내기: File > Download > PDF",
            "5. 이메일 예약 발송: File > Schedule email delivery",
        ],
        "general_feature": [
            "**Looker Studio 주요 기능 목록**",
            "",
            "- **Date Range Control**: 보고서 전체 날짜 범위 조정",
            "- **Drop-down Filter**: 차원 기준 필터 위젯",
            "- **Data Control**: 보고서에서 사용할 Dataset 선택",
            "- **Blended Data**: 최대 5개 소스 JOIN (Resource > Manage blended data)",
            "- **Cross-filter**: 차트 클릭 시 다른 차트 자동 필터링 (Setup > Cross-filtering)",
            "- **Share**: 우측 상단 Share 버튼",
        ],
    },
}


def _fuzzy_match_feature(intent: str) -> str:
    """intent에서 feature_type 퍼지 매칭. 없으면 'general_feature' 반환."""
    intent_lower = intent.lower()
    for ftype, keywords in _FEATURE_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in intent_lower:
                return ftype
    return "general_feature"


def _mode_feature(intent: str, tool: str) -> str:
    """기능 사용 가이드 반환."""
    feature_type = _fuzzy_match_feature(intent)
    tool_guide = _FEATURE_GUIDE.get(tool, {})
    steps = tool_guide.get(feature_type) or tool_guide.get("general_feature", [])

    tool_upper = tool.upper() if tool != "looker" else "Looker Studio"
    feature_labels = {
        "parameter": "매개변수 (Parameter)",
        "set": "집합 (Set)",
        "group": "그룹 (Group)",
        "interactive_filter": "인터랙티브 필터",
        "drill": "드릴다운 / 계층",
        "action": "액션 (Action)",
        "bookmark": "북마크 (Bookmark)",
        "publish": "퍼블리시 / 공유",
        "cross_filter": "크로스 필터",
        "general_feature": "기능 안내",
    }
    feature_name = feature_labels.get(feature_type, "기능")
    header = f"## {tool_upper} — {feature_name}"
    if feature_type == "general_feature":
        header += f"\n\n> '{intent}'에 대한 정확한 기능 매핑이 없습니다. {tool_upper} 주요 기능을 안내합니다."

    lines = [header, ""] + steps
    if tool in _TOOL_DOCS:
        lines += ["", f"📖 공식 문서: {_TOOL_DOCS[tool]}"]
    return "\n".join(lines)
```

- [ ] **Step 4: 기능 모드 테스트 통과 확인**

```bash
python3 -m pytest tests/unit/test_bi_tool_guide.py::TestFeatureMode -v
```

Expected: 4 passed

- [ ] **Step 5: 커밋**

```bash
git add bi_agent_mcp/tools/bi_tool_guide.py tests/unit/test_bi_tool_guide.py
git commit -m "feat: bi_tool_guide 기능 사용 모드 (매개변수/집합/드릴/필터 등)"
```

---

## Task 7: 모드 4 — 트러블슈팅 가이드

**Files:**
- Modify: `bi_agent_mcp/tools/bi_tool_guide.py`
- Modify: `tests/unit/test_bi_tool_guide.py`

- [ ] **Step 1: 트러블슈팅 모드 테스트 작성**

```python
class TestTroubleshootMode:
    def test_powerbi_connection_error(self):
        result = bi_tool_guide(
            intent="연결이 안 된다",
            tool="powerbi",
            situation="연결 오류",
        )
        assert "Gateway" in result or "게이트웨이" in result or "연결" in result
        assert "[ERROR]" not in result

    def test_tableau_calc_syntax_error(self):
        result = bi_tool_guide(
            intent="함수 오류 발생",
            tool="tableau",
            situation="함수 오류",
        )
        assert "valid" in result.lower() or "수식" in result or "오류" in result

    def test_tableau_aggregation_error(self):
        result = bi_tool_guide(intent="값이 두 배로 나와", tool="tableau")
        assert "[ERROR]" not in result
        assert "집계" in result or "LOD" in result or "중복" in result

    def test_unknown_situation_fallback(self):
        result = bi_tool_guide(
            intent="뭔가 이상함",
            tool="quicksight",
            situation="완전 모르는 상황",
        )
        assert "[ERROR]" not in result
        assert "docs.aws.amazon.com" in result or "quicksight" in result.lower()
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
python3 -m pytest tests/unit/test_bi_tool_guide.py::TestTroubleshootMode -v
```

Expected: 4 failed

- [ ] **Step 3: 트러블슈팅 가이드 데이터 + `_mode_troubleshoot` 구현**

```python
_SITUATION_TYPE_KEYWORDS: dict[str, list[str]] = {
    "connection_error":   ["연결 오류", "connection", "데이터 소스 오류", "연결 안", "db 연결"],
    "auth_error":         ["인증 오류", "로그인 실패", "oauth", "권한 오류", "인증 실패"],
    "viz_error":          ["차트 안 나", "빈 차트", "시각화 오류", "안 보임", "표시 안"],
    "refresh_error":      ["새로고침 오류", "refresh", "업데이트 안", "갱신 실패"],
    "calc_syntax_error":  ["함수 오류", "수식 오류", "invalid calculation", "계산 오류"],
    "calc_wrong_result":  ["결과 이상", "값이 이상", "틀림", "다름", "예상과 다"],
    "null_handling":      ["null", "빈값", "0으로 나", "누락"],
    "aggregation_error":  ["두 배", "overcounting", "중복 집계", "값이 두 배"],
}

_SITUATION_GUIDE: dict[str, dict[str, list[str]]] = {
    "tableau": {
        "connection_error": [
            "**Tableau 데이터 소스 연결 오류 해결**",
            "",
            "1. 상단 Data 메뉴 > 데이터 소스 이름 > Edit Connection",
            "2. 서버 주소, 포트, 데이터베이스 이름 재확인",
            "3. DB 드라이버 설치 확인 (help.tableau.com/driver-download)",
            "4. 방화벽/VPN 설정 확인 — Tableau Server IP 허용 필요",
            "5. Tableau Server 연결 시: Server > Sign In > URL 재입력",
        ],
        "calc_syntax_error": [
            "**Tableau 계산 필드 오류 해결**",
            "",
            "1. Analysis > Edit Calculated Field 열기",
            "2. 편집기 하단 오류 메시지 확인",
            "3. 일반적인 원인:",
            "   - 대괄호 누락: `[Field Name]` 형식 필수",
            "   - 집계 혼용: `SUM([Sales]) + [Profit]` → `SUM([Sales]) + SUM([Profit])`",
            "   - 따옴표: 문자열은 작은따옴표 `'text'`, 필드명은 대괄호",
            "4. 'The calculation is valid' 메시지 확인 후 OK",
        ],
        "calc_wrong_result": [
            "**Tableau 집계 결과 이상 해결**",
            "",
            "1. 집계 함수 확인: 필드 우클릭 > Measure > SUM/AVG/COUNT 중 올바른 것 선택",
            "2. 중복 데이터 확인: Analysis > View Data로 원본 데이터 확인",
            "3. 날짜 집계 레벨 확인: Columns Shelf의 날짜 필드 드롭다운 > 올바른 단위 선택",
            "4. 필터 영향 확인: Filters Shelf에 의도하지 않은 필터 여부 확인",
            "5. LOD 사용 고려: 뷰 레벨과 독립적인 계산 필요시 FIXED LOD 사용",
        ],
        "aggregation_error": [
            "**Tableau 중복 집계 오류 해결**",
            "",
            "1. 데이터 소스 Join 확인: Data Source 탭 > Join 유형 확인 (LEFT → INNER 변경 시도)",
            "2. 중복 행 확인: `{FIXED : COUNT([Primary Key])}` 로 중복 행 수 파악",
            "3. COUNTD 사용: COUNT 대신 COUNTD([Primary Key])로 고유 수 집계",
            "4. LOD 적용: `{FIXED [Dimension] : SUM([Measure])}` 로 집계 레벨 고정",
        ],
        "general_troubleshoot": [
            "**Tableau 일반 문제 해결 순서**",
            "",
            "1. Data 패널에서 데이터 소스 연결 상태 확인",
            "2. Analysis > View Data로 원본 데이터 확인",
            "3. 필터 일시 제거 후 결과 재확인",
            "4. 새 워크시트에서 동일 작업 재시도",
        ],
    },
    "powerbi": {
        "connection_error": [
            "**Power BI 데이터 소스 연결 오류 해결**",
            "",
            "1. Home > Transform data > Data source settings에서 자격증명 확인",
            "2. 온-프레미스 데이터: 온-프레미스 데이터 게이트웨이 설치/업데이트 확인",
            "   - 게이트웨이 버전이 구식이면 GatewayNotReachable 오류 발생",
            "3. Power BI Service 새로고침 오류 시:",
            "   - 브라우저 캐시 삭제",
            "   - `https://app.powerbi.com?alwaysPromptForContentProviderCreds=true` 접속으로 자격증명 갱신",
            "4. OAuth 만료 (Dynamics CRM, SharePoint): 동일 계정으로 재인증",
        ],
        "calc_syntax_error": [
            "**Power BI DAX 수식 오류 해결**",
            "",
            "1. Modeling 탭 > 측정값 선택 > 수식 표시줄에서 오류 메시지 확인",
            "2. 일반적인 원인:",
            "   - 테이블명 누락: `SUM([Sales])` → `SUM('테이블'[Sales])`",
            "   - 따옴표: 테이블명은 작은따옴표, 열명은 대괄호",
            "   - CALCULATE 안에서 SUM 없이 필터 사용 불가",
            "3. Quick Measure 활용: Modeling > Quick measures에서 패턴 참고",
        ],
        "aggregation_error": [
            "**Power BI 중복 집계 오류 해결**",
            "",
            "1. Model view에서 테이블 간 관계(Relationship) 확인",
            "   - 다대다(M:N) 관계가 있으면 중복 집계 발생 가능",
            "2. 관계 카디널리티 변경: 1:N으로 재설정",
            "3. COUNTROWS 대신 DISTINCTCOUNT 사용",
            "4. CALCULATE + ALL()로 필터 컨텍스트 재설정",
        ],
        "general_troubleshoot": [
            "**Power BI 일반 문제 해결 순서**",
            "",
            "1. Home > Transform data에서 데이터 미리보기 확인",
            "2. View > Performance analyzer로 느린 시각화 진단",
            "3. 시각화 삭제 후 새로 추가하여 재현 확인",
            "4. File > Options > Data Load 설정 확인",
        ],
    },
    "quicksight": {
        "connection_error": [
            "**QuickSight 데이터 소스 연결 오류 해결**",
            "",
            "오류 코드별 해결:",
            "- `CONNECTION_FAILURE` / `UNROUTABLE_HOST`: VPC 설정 및 Security Group 확인",
            "- `DATA_SOURCE_AUTH_FAILED`: 자격증명 재입력 (Manage data sources > Edit)",
            "- `SSL_CERTIFICATE_VALIDATION_FAILURE`: SSL 설정 확인",
            "- `IAM_ROLE_NOT_AVAILABLE`: QuickSight IAM 역할 권한 확인",
            "- `S3_FILE_INACCESSIBLE`: S3 버킷 정책 및 QuickSight 접근 권한 확인",
        ],
        "general_troubleshoot": [
            "**QuickSight 일반 문제 해결**",
            "",
            "1. Dataset 새로고침: Datasets > Dataset 선택 > Refresh now",
            "2. SPICE 용량 초과: Datasets > SPICE capacity 확인",
            "3. Visual 오류: Visual 우측 상단 ⋯ > Edit 또는 Delete 후 재생성",
        ],
    },
    "looker": {
        "connection_error": [
            "**Looker Studio 데이터 소스 연결 오류 해결**",
            "",
            "1. Resource > Manage added data sources > 데이터 소스 선택 > Edit connection",
            "2. 오류별 해결:",
            "   - 권한 오류: Owner's Credentials로 전환 (데이터 소스 편집 > Credentials)",
            "   - 데이터 소스 삭제됨: 새 데이터 소스 추가",
            "   - 인증 만료: Looker Studio의 Google Account 접근 철회 후 재연결",
            "3. 최후 수단 공식 순서:",
            "   a. 깨진 차트 선택 > 데이터 소스 교체",
            "   b. Refresh fields",
            "   c. 데이터 소스 재연결",
            "   d. 데이터 소스 제거 후 재추가",
        ],
        "general_troubleshoot": [
            "**Looker Studio 일반 문제 해결**",
            "",
            "1. 보고서 새로고침: Ctrl+Shift+R (Windows) / Cmd+Shift+R (Mac)",
            "2. 데이터 소스 새로고침: Resource > Manage data sources > Refresh fields",
            "3. 차트 삭제 후 재생성",
            "4. 다른 브라우저/시크릿 모드에서 접속 시도",
        ],
    },
}


def _fuzzy_match_situation(intent: str, situation: str) -> str:
    """intent + situation에서 situation_type 매핑. 없으면 'general_troubleshoot'."""
    text = (intent + " " + situation).lower()
    for stype, keywords in _SITUATION_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return stype
    return "general_troubleshoot"


def _mode_troubleshoot(intent: str, situation: str, tool: str) -> str:
    """트러블슈팅 가이드 반환."""
    sit_type = _fuzzy_match_situation(intent, situation)
    tool_guide = _SITUATION_GUIDE.get(tool, {})
    steps = tool_guide.get(sit_type) or tool_guide.get("general_troubleshoot", [])

    tool_upper = tool.upper() if tool != "looker" else "Looker Studio"
    sit_labels = {
        "connection_error": "데이터 소스 연결 오류",
        "auth_error": "인증/권한 오류",
        "viz_error": "시각화 오류",
        "refresh_error": "새로고침 오류",
        "calc_syntax_error": "계산 수식 오류",
        "calc_wrong_result": "잘못된 계산 결과",
        "null_handling": "NULL/빈값 처리",
        "aggregation_error": "중복 집계 오류",
        "general_troubleshoot": "일반 트러블슈팅",
    }
    sit_name = sit_labels.get(sit_type, "트러블슈팅")
    header = f"## {tool_upper} — {sit_name}"
    if sit_type == "general_troubleshoot":
        header += f"\n\n> 정확한 오류 유형을 특정하지 못했습니다. 공식 문서를 참고하세요."

    lines = [header, ""] + steps
    if tool in _TOOL_DOCS:
        lines += ["", f"📖 공식 문서: {_TOOL_DOCS[tool]}"]
    return "\n".join(lines)
```

- [ ] **Step 4: 트러블슈팅 모드 테스트 통과 확인**

```bash
python3 -m pytest tests/unit/test_bi_tool_guide.py::TestTroubleshootMode -v
```

Expected: 4 passed

- [ ] **Step 5: 커밋**

```bash
git add bi_agent_mcp/tools/bi_tool_guide.py tests/unit/test_bi_tool_guide.py
git commit -m "feat: bi_tool_guide 트러블슈팅 모드 (시스템 오류 + 계산 디버깅)"
```

---

## Task 8: server.py 등록 + 전체 테스트

**Files:**
- Modify: `bi_agent_mcp/server.py`
- Modify: `tests/unit/test_bi_tool_guide.py`

- [ ] **Step 1: 통합 테스트 추가**

```python
class TestIntegration:
    """end-to-end 케이스 — 실제 반환값 사람이 읽을 수 있는지 확인."""

    def test_full_tableau_line_chart(self):
        result = bi_tool_guide(
            intent="월별 매출 추이",
            tool="tableau",
            columns="order_date, revenue",
        )
        assert "order_date" in result
        assert "revenue" in result
        assert "Columns Shelf" in result

    def test_full_powerbi_mom_dax(self):
        result = bi_tool_guide(
            intent="MoM 성장률 계산",
            tool="powerbi",
            columns="date, sales",
        )
        assert "DATEADD" in result or "DAX" in result
        assert "sales" in result

    def test_full_quicksight_connection_error(self):
        result = bi_tool_guide(
            intent="연결 오류",
            tool="quicksight",
            situation="연결 오류",
        )
        assert "VPC" in result or "CONNECTION" in result or "연결" in result

    def test_full_looker_parameter(self):
        result = bi_tool_guide(intent="매개변수 만들기", tool="looker")
        # looker는 parameter 가이드 없으므로 general_feature 반환
        assert "[ERROR]" not in result
        assert "Looker Studio" in result

    def test_doc_link_included(self):
        result = bi_tool_guide(intent="차트 만들기", tool="tableau")
        assert "help.tableau.com" in result
```

- [ ] **Step 2: 전체 테스트 통과 확인**

```bash
python3 -m pytest tests/unit/test_bi_tool_guide.py -v
```

Expected: 모두 passed (20개+)

- [ ] **Step 3: 도구 수 확인**

```bash
python3 -c "from bi_agent_mcp.server import mcp; print(len(mcp._tool_manager._tools))"
```

현재 도구 수 기록해두기 (등록 후 +1 확인용)

- [ ] **Step 4: server.py 등록**

`bi_agent_mcp/server.py`의 `if __name__ == "__main__":` 바로 앞에 추가:

```python
# bi_tool_guide — BI 툴 시각화 가이드 (5개 모드: 추천/차트/계산/기능/트러블슈팅)
from bi_agent_mcp.tools.bi_tool_guide import bi_tool_guide
register_tool(bi_tool_guide, is_core=False)
```

- [ ] **Step 5: 도구 수 증가 확인**

```bash
python3 -c "from bi_agent_mcp.server import mcp; print(len(mcp._tool_manager._tools))"
```

Expected: 이전 수 + 1

- [ ] **Step 6: 전체 테스트 스위트 실행**

```bash
python3 -m pytest tests/unit/ -q --no-header 2>&1 | tail -5
```

Expected: 커버리지 80%+ 유지, 실패 없음

- [ ] **Step 7: 최종 커밋**

```bash
git add bi_agent_mcp/server.py tests/unit/test_bi_tool_guide.py
git commit -m "feat: bi_tool_guide server.py 등록 및 통합 테스트 추가"
```

---

## 완료 기준 체크리스트

- [ ] `bi_tool_guide()` 함수가 server.py에 등록됨
- [ ] 5개 모드 모두 동작: 추천 / 차트 / 계산 / 기능 / 트러블슈팅
- [ ] 4개 툴 모두 커버: tableau / powerbi / quicksight / looker
- [ ] 매핑 안 된 케이스는 폴백 반환 (`[ERROR]` 없음)
- [ ] 컬럼명이 제공되면 가이드에 실제 컬럼명 포함
- [ ] 단위 테스트 20개+ 통과
- [ ] 전체 테스트 커버리지 80%+ 유지
