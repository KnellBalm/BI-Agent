# bi_tool_guide() — 디자인 스펙 (v2)

**작성일:** 2026-04-02  
**상태:** 확정 (사용자 승인)  
**목표:** BI 툴을 모르는 사용자도 원하는 시각화를 만들 수 있도록, 의도 + 데이터 구조 기반의 단계별 가이드를 제공한다.  
**핵심 변경:** A안 채택 — 단일 함수 내부에서 그래프/워크플로우 분기 처리 (토큰 최소화 + 비전문가 대응)

---

## 1. 비전

> "BI 툴 사용법을 몰라도, 내가 원하는 차트가 무엇인지만 말하면 된다."

사용자가 "월별 매출 추이를 보고 싶다"처럼 의도를 말하면, 어떤 차트 타입이 적합한지 추천하고, 선택한 BI 툴에서 실제로 만드는 방법을 컬럼명까지 포함해 단계별로 안내한다.

Claude 1번 호출 → 완전한 가이드 반환. 내부 분기는 Python 코드가 처리.

---

## 2. 함수 시그니처

```python
def bi_tool_guide(
    intent: str,        # 필수. "월별 매출 추이를 보고 싶다"
    columns: str = "",  # 선택. "date, revenue, region" 또는 JSON 형태
    tool: str = "",     # 선택. "tableau" / "powerbi" / "quicksight" / "looker"
    situation: str = "" # 선택. "연결 오류", "필터 추가" 등 트러블슈팅 키워드
) -> str:
    """[Helper] BI 툴 시각화 가이드 (내부 분기형).

    tool 미지정 → 차트 타입 추천 + 4개 툴 비교
    tool 지정   → 해당 툴의 단계별 가이드 반환
    매핑 안 됨  → 폴백 가이드 반환 (에러 아님)
    """
```

---

## 3. 내부 분기 구조 (A안: 내부 그래프)

```
bi_tool_guide(intent, columns, tool, situation)
         │
         ├─ intent 비어있음 → [ERROR] 반환
         │
         ├─ tool 비어있음 → 추천 모드
         │    └─ _detect_chart_type(intent) → 차트 추천
         │         + 4개 툴 1줄 비교 + 다음 호출 안내
         │
         └─ tool 지정됨 → 가이드 모드
              │
              ├─ tool 지원 목록 밖 → [ERROR] 반환
              │
              ├─ situation 지정됨 → 트러블슈팅 노드
              │    └─ _detect_situation(situation)
              │         ├─ 매핑됨 → 툴별 상황 가이드 반환
              │         └─ 매핑 안 됨 → 범용 트러블슈팅 + 공식 문서 링크
              │
              └─ situation 없음 → 차트 생성 노드
                   └─ _detect_chart_type(intent)
                        ├─ 매핑됨 → 툴별 차트 단계 가이드 반환
                        └─ 매핑 안 됨 → 범용 차트 생성 워크플로우 폴백
```

---

## 4. 지원 범위 (공식 문서 기반)

### 4-1. 지원 툴

| 툴 | 파라미터 값 | 공식 차트 수 |
|----|------------|------------|
| Tableau Desktop/Online | `tableau` | 24가지 (Show Me 패널 기준) |
| Power BI Desktop/Service | `powerbi` | 30가지+ (Visualizations pane 기준) |
| Amazon QuickSight | `quicksight` | 27가지+ |
| Looker Studio (구 Data Studio) | `looker` | 30가지+ |

### 4-2. 차트 타입 키워드 매핑 (intent → chart_type)

퍼지 매칭으로 의도 키워드를 찾고, 없으면 `"general"` 폴백을 사용한다.

| 의도 키워드 | 매핑 chart_type | 공식 차트 이름 |
|------------|----------------|--------------|
| 추이, 변화, 트렌드, 시계열, 선 | `line` | Tableau: Lines / Power BI: Line chart / QS: Line Chart / Looker: Time Series |
| 비교, 순위, 막대, 바 | `bar` | Tableau: Horizontal/Vertical Bars / Power BI: Bar/Column chart / QS: Bar Chart / Looker: Bar Chart |
| 누적 막대, 누적 바, stacked | `stacked_bar` | Tableau: Stacked Bars / Power BI: Stacked bar/column / QS: 100% Stacked / Looker: Stacked Bar |
| 비율, 구성, 파이, 원형, 도넛 | `pie` | Tableau: Pie Chart / Power BI: Pie/Donut chart / QS: Pie/Donut Chart / Looker: Pie/Donut |
| 상관, 분포, 산점, scatter | `scatter` | Tableau: Scatter Plot / Power BI: Scatter/Bubble chart / QS: Scatter Plot / Looker: Scatter Chart |
| 지역, 지도, 맵, 위치 | `map` | Tableau: Symbol Map, Filled Map / Power BI: Map / QS: Geospatial Map / Looker: Geo Chart |
| 퍼널, 전환, 이탈, funnel | `funnel` | Tableau: 직접 지원 없음(바 차트 변형) / Power BI: Funnel chart / QS: Funnel Chart / Looker: 없음(커뮤니티) |
| 코호트, 리텐션 | `heatmap` | Tableau: Heat Map / Power BI: Matrix / QS: Heat Map / Looker: Pivot Table |
| KPI, 요약, 핵심지표, 카드 | `kpi` | Tableau: Text Table / Power BI: Card visual / QS: KPI / Looker: Scorecard |
| 히스토그램, 분포 | `histogram` | Tableau: Histogram / Power BI: Column chart(구간) / QS: Histogram / Looker: 없음(바 차트 변형) |
| 박스, 사분위, boxplot | `boxplot` | Tableau: Box-and-Whisker / Power BI: Box plot(AppSource) / QS: Box Plot / Looker: 없음 |
| 트리맵, treemap | `treemap` | Tableau: Treemap / Power BI: Treemap / QS: Tree Map / Looker: Treemap |
| 워터폴, waterfall, 증감 | `waterfall` | Tableau: Gantt 변형 / Power BI: Waterfall chart / QS: Waterfall Chart / Looker: 커뮤니티 |
| 버블, bubble | `bubble` | Tableau: Packed Bubbles / Power BI: Bubble chart / QS: 없음 / Looker: 버블 |
| 영역, 면적, area | `area` | Tableau: Area Charts / Power BI: Area chart / QS: Line Chart(영역 옵션) / Looker: Area Chart |
| 이중축, dual, combo | `combo` | Tableau: Dual Lines / Power BI: Combo chart / QS: Combo Chart / Looker: Combo Chart |
| 간트, gantt | `gantt` | Tableau: Gantt Bar / Power BI: 없음(AppSource) / QS: 없음 / Looker: 없음 |
| 워드클라우드, 텍스트 빈도 | `wordcloud` | Tableau: Word Cloud / Power BI: Word Cloud(AppSource) / QS: Word Cloud / Looker: 없음 |
| **매핑 안 됨** | `general` | **폴백: 범용 차트 생성 워크플로우** |

### 4-3. 상황(situation) 키워드 매핑

| 상황 키워드 | 매핑 situation_type |
|-----------|-------------------|
| 연결 오류, DB 연결, 데이터 소스, connection | `connection_error` |
| 인증 오류, 로그인 실패, OAuth, 권한 | `auth_error` |
| 차트 안 나옴, 빈 차트, 시각화 오류 | `viz_error` |
| 필터 추가, 필터 설정, 날짜 필터 | `filter` |
| 날짜 집계, 월별, 주별, 날짜 그룹 | `date_aggregation` |
| 계산 필드, 수식, MoM, 성장률, 계산 컬럼 | `calculated_field` |
| 퍼블리시, 배포, 공유, publish | `publish` |
| 차트 바꾸기, 그래프 변경, 차트 타입 | `change_chart_type` |
| **매핑 안 됨** | `general_troubleshoot` | → 범용 + 공식 문서 링크 |

---

## 5. 구현 구조

### 파일 레이아웃

```
bi_agent_mcp/tools/bi_tool_guide.py   # 신규 생성
bi_agent_mcp/server.py                # bi_tool_guide 등록 추가
tests/unit/test_bi_tool_guide.py      # 신규 생성
```

### 내부 구조 (bi_tool_guide.py)

```python
# ── 지원 툴 ──────────────────────────────────────────────────────────────────
_SUPPORTED_TOOLS = {"tableau", "powerbi", "quicksight", "looker"}

_TOOL_DOCS = {
    "tableau":   "https://help.tableau.com/current/pro/desktop/en-us/",
    "powerbi":   "https://learn.microsoft.com/en-us/power-bi/",
    "quicksight":"https://docs.aws.amazon.com/quicksight/latest/user/",
    "looker":    "https://support.google.com/looker-studio/",
}

# ── 키워드 매핑 ───────────────────────────────────────────────────────────────
_CHART_KEYWORDS: dict[str, list[str]]    # chart_type → [키워드 리스트]
_SITUATION_KEYWORDS: dict[str, list[str]] # situation_type → [키워드 리스트]

# ── 가이드 데이터 (툴별 × 타입별 단계) ─────────────────────────────────────────
_CHART_GUIDE: dict[str, dict[str, list[str]]]
# 예: _CHART_GUIDE["tableau"]["line"] = ["1단계: ...", "2단계: ..."]

_CHART_FALLBACK: dict[str, list[str]]
# 예: _CHART_FALLBACK["tableau"] = ["1단계: 데이터 소스 연결", ...]

_SITUATION_GUIDE: dict[str, dict[str, list[str]]]
_SITUATION_FALLBACK: dict[str, list[str]]  # + 공식 문서 링크 포함

# ── 툴별 UI 용어 사전 (컬럼명 치환에 사용) ───────────────────────────────────
_TOOL_TERMS = {
    "tableau":    {"dimension_shelf": "Columns/Rows Shelf", "measure_shelf": "Rows Shelf", ...},
    "powerbi":    {"dimension_shelf": "Axis 버킷", "measure_shelf": "Values 버킷", ...},
    "quicksight": {"dimension_shelf": "X axis (Field well)", "measure_shelf": "Value (Field well)", ...},
    "looker":     {"dimension_shelf": "Dimension 슬롯", "measure_shelf": "Metric 슬롯", ...},
}

# ── 헬퍼 함수 ──────────────────────────────────────────────────────────────────
def _detect_chart_type(intent: str) -> str:
    """intent 키워드 퍼지 매칭 → chart_type 또는 'general'"""

def _detect_situation(situation: str) -> str:
    """situation 키워드 퍼지 매칭 → situation_type 또는 'general_troubleshoot'"""

def _parse_columns(columns: str) -> list[str]:
    """컬럼 문자열 파싱 → 리스트 (쉼표 구분 또는 JSON)"""

def _inject_columns(steps: list[str], col_list: list[str], tool: str) -> str:
    """단계 리스트에 실제 컬럼명을 치환하여 마크다운 문자열로 반환"""

def _recommend_mode(intent: str, columns: str) -> str:
    """tool 미지정 시 차트 추천 + 툴별 비교 반환"""

def _guide_mode(intent: str, columns: str, tool: str, situation: str) -> str:
    """tool 지정 시 단계별 가이드 반환 (차트 생성 또는 트러블슈팅)"""

# ── 메인 함수 (MCP 등록) ────────────────────────────────────────────────────────
def bi_tool_guide(intent, columns, tool, situation) -> str:
```

### 핵심 데이터 구조 예시

```python
_CHART_GUIDE = {
    "tableau": {
        "line": [
            "**1단계: 데이터 소스 연결**\n   - 상단 메뉴 Data > New Data Source",
            "**2단계: 날짜 필드 배치**\n   - {date_col}을 Columns Shelf로 드래그",
            "**3단계: 수치 필드 배치**\n   - {measure_col}을 Rows Shelf로 드래그",
            "**4단계: 날짜 집계 설정**\n   - Columns의 {date_col} 우클릭 > Month",
            "**5단계: 차트 타입**\n   - Show Me 패널 > Lines (Continuous) 선택",
        ],
        "general": [  # 폴백
            "**1단계: 데이터 소스 연결**",
            "**2단계: 필드를 Columns/Rows Shelf로 드래그**",
            "**3단계: Show Me 패널에서 원하는 차트 타입 선택**",
            "**4단계: Marks 카드에서 Color/Size/Label 조정**",
            "**5단계: Format 메뉴로 서식 지정**",
        ],
    },
    # ... powerbi, quicksight, looker 동일 구조
}
```

---

## 6. 툴별 UI 용어 매핑 (컬럼 배치 안내에 사용)

| 개념 | Tableau | Power BI | QuickSight | Looker Studio |
|------|---------|----------|------------|--------------|
| 날짜/범주 배치 | Columns Shelf | Axis 버킷 | X axis (Field well) | Dimension 슬롯 |
| 수치 배치 | Rows Shelf | Values 버킷 | Value (Field well) | Metric 슬롯 |
| 색상 구분 | Marks > Color | Legend 버킷 | Color (Field well) | Color dimension |
| 필터 | Filters Shelf | Filters pane | Filter pane | Filter Control |
| 계산 필드 | Calculated Field (Analysis 메뉴) | DAX Measure (Modeling > New Measure) | Calculated Field (Add calculated field) | Calculated Field (Data pane) |
| 게시/공유 | Server > Publish Workbook | Home > Publish | Publish dashboard | Share 버튼 |
| 날짜 집계 | 날짜 우클릭 > Month/Quarter | Auto Date/Time 계층 드릴다운 | Date field > Aggregate by Month | Date dimension > Aggregation 설정 |

---

## 7. 에러 처리

```python
# intent 비어있음
return "[ERROR] intent는 필수 파라미터입니다. 예: '월별 매출 추이를 보고 싶다'"

# 알 수 없는 툴 (tool이 지정됐지만 지원 목록 밖)
return "[ERROR] 지원하지 않는 툴입니다. tool은 tableau / powerbi / quicksight / looker 중 하나여야 합니다."

# 차트/상황 매핑 안 됨 → 에러 아님, 폴백 반환 (명시적으로 안내 포함)
# 예: "'{intent}'에 대한 정확한 가이드는 없지만, Tableau 일반 워크플로우를 안내합니다."
```

---

## 8. 테스트 계획

| 테스트 케이스 | 예상 결과 |
|-------------|----------|
| `bi_tool_guide("월별 추이")` (tool 없음) | 추천 모드: 라인 차트 추천 + 4개 툴 비교 |
| `bi_tool_guide("월별 추이", tool="tableau", columns="date, revenue")` | Tableau 라인 차트 5단계 가이드 (컬럼명 포함) |
| `bi_tool_guide("워터폴 차트", tool="looker")` | 폴백: "정확한 가이드 없음 + Looker 범용 워크플로우" |
| `bi_tool_guide("연결이 안 된다", tool="powerbi", situation="연결 오류")` | Power BI 연결 오류 트러블슈팅 |
| `bi_tool_guide("이상한 질문", tool="powerbi", situation="알 수 없는 상황")` | 폴백: 범용 트러블슈팅 + 공식 문서 링크 |
| `bi_tool_guide("", tool="tableau")` | `[ERROR] intent는 필수 파라미터` |
| `bi_tool_guide("차트", tool="unknown_tool")` | `[ERROR] 지원하지 않는 툴` |
| `bi_tool_guide("KPI", tool="quicksight", columns="revenue")` | QuickSight KPI 시각화 가이드 |
| `bi_tool_guide("코호트", tool="looker")` | Looker Studio Pivot Table 기반 코호트 가이드 |
| 각 4개 툴 × 주요 3개 차트 타입 = 12케이스 | 모두 단계 포함 반환 |

최소 2개/함수 (정상 + 에러) 원칙, 총 15개+ 테스트 목표.

---

## 9. server.py 등록

```python
# bi_tool_guide — BI 툴 시각화 가이드 (추천 + 단계별 안내, 내부 분기형)
from bi_agent_mcp.tools.bi_tool_guide import bi_tool_guide
mcp.tool()(bi_tool_guide)
```

---

## 10. 성공 기준

```
bi_tool_guide("월별 매출 추이", columns="date, revenue", tool="tableau")
→ "date"를 Columns Shelf로 드래그 등 컬럼명 포함 5단계 가이드

bi_tool_guide("매출 추이를 보고싶다")
→ 라인 차트 추천 + 4개 툴 비교 + 다음 호출 안내

bi_tool_guide("연결이 안 된다", tool="powerbi", situation="연결 오류")
→ GatewayNotReachable 포함 Power BI 연결 오류 트러블슈팅

bi_tool_guide("워터폴 차트가 필요해", tool="looker")
→ "정확한 가이드는 없지만..." + 범용 차트 생성 워크플로우
```

---

## 부록: 툴별 공식 문서 참조

| 툴 | 차트 타입 문서 |
|---|--------------|
| Tableau | [Use Show Me](https://help.tableau.com/current/pro/desktop/en-us/buildauto_showme.htm) · [Build Common Chart Types](https://help.tableau.com/current/pro/desktop/en-us/dataview_examples.htm) |
| Power BI | [Visualization types](https://learn.microsoft.com/en-us/power-bi/visuals/power-bi-visualization-types-for-reports-and-q-and-a) |
| QuickSight | [Visual types](https://docs.aws.amazon.com/quicksight/latest/user/working-with-visual-types.html) |
| Looker Studio | [Types of charts](https://support.google.com/looker-studio/answer/13590887) |
