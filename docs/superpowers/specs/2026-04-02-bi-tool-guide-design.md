# bi_tool_guide() — 디자인 스펙 (v3)

**작성일:** 2026-04-02  
**상태:** 확정 (사용자 승인)  
**목표:** BI 툴을 모르는 사용자도 차트 생성, 계산 수식, 기능 사용, 트러블슈팅 전 영역을 AI 가이드로 해결할 수 있도록 한다.  
**아키텍처:** A안 — 단일 함수 내부에서 5개 모드로 분기 (토큰 최소화 + 비전문가 대응)

---

## 1. 비전

> "BI 툴 사용법을 몰라도, 내가 원하는 것만 말하면 된다."

차트 만들기부터 LOD 수식 작성, 매개변수·집합·필터 생성, 함수 오류 디버깅, 연결 오류 해결까지 — BI 툴 사용의 전 영역을 커버한다.

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

## 3. 내부 분기 구조 (A안: 5개 모드)

```
bi_tool_guide(intent, columns, tool, situation)
         │
         ├─ intent 비어있음 → [ERROR] 반환
         │
         ├─ tool 비어있음 → [모드 0] 추천 모드
         │    └─ 차트 타입 추천 + 4개 툴 비교 + 다음 호출 안내
         │
         └─ tool 지정됨
              │
              ├─ tool 지원 목록 밖 → [ERROR] 반환
              │
              └─ _classify_intent(intent, situation) → 모드 결정
                   │
                   ├─ [모드 1] 차트 생성
                   │    └─ 의도: "라인 차트", "바 차트", "KPI 만들기" 등
                   │         ├─ 차트 타입 매핑됨 → 툴별 단계 가이드
                   │         └─ 매핑 안 됨 → 범용 차트 워크플로우 폴백
                   │
                   ├─ [모드 2] 계산/수식
                   │    └─ 의도: "최초구매일", "MoM 성장률", "누적합", "LOD"
                   │         계산 타입 매핑됨 → 툴별 수식 가이드
                   │         (Tableau: Calc Field/LOD, Power BI: DAX,
                   │          QuickSight: Calc Field, Looker: Calc Field)
                   │         매핑 안 됨 → 범용 계산 필드 생성 폴백
                   │
                   ├─ [모드 3] 기능 사용
                   │    └─ 의도: "매개변수", "집합", "드릴다운", "액션", "북마크"
                   │         기능 타입 매핑됨 → 툴별 기능 설정 가이드
                   │         매핑 안 됨 → 해당 툴 기능 목록 안내 폴백
                   │
                   └─ [모드 4] 트러블슈팅
                        ├─ 시스템 오류: "연결 오류", "인증 실패", "차트 안 나옴"
                        │    → 툴별 시스템 트러블슈팅 가이드
                        ├─ 계산 디버깅: "함수 오류", "잘못된 결과값", "집계 이상"
                        │    → 툴별 수식 오류 해결 가이드
                        └─ 매핑 안 됨 → 범용 트러블슈팅 + 공식 문서 링크
```

### 모드 분류 기준 (`_classify_intent`)

| 신호 | 모드 |
|------|------|
| situation 지정됨 | 모드 4 (트러블슈팅) 우선 |
| intent에 차트 타입 키워드 | 모드 1 |
| intent에 함수/수식/계산 키워드 | 모드 2 |
| intent에 기능 키워드 (매개변수, 집합 등) | 모드 3 |
| intent에 오류/안됨/이상 키워드 | 모드 4 |
| 기타 (특정 모드 감지 안 됨) | 모드 1 폴백 |

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

### 4-3. 계산/수식 키워드 매핑 (모드 2)

| 의도 키워드 | 매핑 calc_type | 툴별 구현 방식 |
|------------|--------------|--------------|
| 최초, 첫번째, MIN, 최솟값 | `min_per_dim` | Tableau: `{FIXED [dim] : MIN([col])}` / Power BI: `MINX(FILTER(...))` / QS: `min()` / Looker: MIN metric |
| 마지막, 최근, MAX, 최댓값 | `max_per_dim` | 위와 동일하되 MAX 적용 |
| 전월 대비, MoM, 전기 대비, 증감률 | `mom_growth` | Tableau: `LOOKUP` / Power BI: `DATEADD + DIVIDE` / QS: `periodOverPeriodDifference` / Looker: 날짜 오프셋 |
| 누적합, 러닝합, running sum | `running_total` | Tableau: `RUNNING_SUM` / Power BI: `CALCULATE + FILTER` / QS: `runningSum` / Looker: running_total |
| 비율, 전체 대비, % | `ratio_to_total` | Tableau: `SUM([x]) / TOTAL(SUM([x]))` / Power BI: `DIVIDE + ALL` / QS: `percentOfTotal` / Looker: 비율 metric |
| 이동 평균, 7일 평균 | `moving_avg` | Tableau: `WINDOW_AVG` / Power BI: `AVERAGEX + DATESINPERIOD` / QS: `windowAvg` / Looker: `mean` with window |
| 순위, 랭킹, rank | `rank` | Tableau: `RANK()` / Power BI: `RANKX` / QS: `rank` / Looker: `rank` measure |
| 조건부 집계, IF 계산, CASE | `conditional_calc` | Tableau: `IF/CASE` / Power BI: `IF/SWITCH` / QS: `ifelse` / Looker: `case when` |
| LOD, 세부 수준, 고정 | `lod` | Tableau 전용: `{FIXED}`, `{INCLUDE}`, `{EXCLUDE}` |
| DAX, 측정값, measure | `dax_measure` | Power BI 전용: DAX 수식 작성 가이드 |
| **매핑 안 됨** | `general_calc` | 각 툴의 계산 필드 생성 범용 가이드 |

### 4-4. 기능 사용 키워드 매핑 (모드 3)

| 의도 키워드 | 매핑 feature_type | 설명 |
|------------|-----------------|------|
| 매개변수, parameter | `parameter` | Tableau Parameter / Power BI What-if parameter / QS Parameter / Looker Parameter |
| 집합, set | `set` | Tableau Set (조건부 또는 수동) |
| 그룹, group, 묶기 | `group` | Tableau Group / Power BI Group / QS Group / Looker |
| 필터, filter, 인터랙티브 필터 | `interactive_filter` | Tableau Quick Filter / Power BI Slicer / QS Filter Control / Looker Date Range Control |
| 드릴다운, drill, 계층 | `drill` | Tableau Hierarchy / Power BI Date Hierarchy + Drill / QS 드릴다운 / Looker |
| 액션, action, 클릭 연결 | `action` | Tableau Action (Filter/URL/Highlight) / Power BI Drillthrough + Bookmarks |
| 북마크, bookmark | `bookmark` | Power BI Bookmark / Tableau Custom View |
| 공유 필터, 크로스 필터 | `cross_filter` | Power BI Cross-filter / Looker Cross-filter |
| 퍼블리시, 공유, 배포 | `publish` | 각 툴별 게시/공유 절차 |
| **매핑 안 됨** | `general_feature` | 해당 툴의 주요 기능 목록 안내 |

### 4-5. 트러블슈팅 키워드 매핑 (모드 4)

**시스템 오류:**

| 상황 키워드 | 매핑 situation_type |
|-----------|-------------------|
| 연결 오류, DB 연결, 데이터 소스, connection | `connection_error` |
| 인증 오류, 로그인 실패, OAuth, 권한 | `auth_error` |
| 차트 안 나옴, 빈 차트, 시각화 오류 | `viz_error` |
| 새로고침 오류, refresh, 업데이트 안 됨 | `refresh_error` |
| 퍼블리시 오류, 배포 안 됨 | `publish_error` |

**계산 디버깅:**

| 상황 키워드 | 매핑 situation_type |
|-----------|-------------------|
| 함수 오류, 수식 오류, invalid calculation | `calc_syntax_error` |
| 결과값 이상, 집계 틀림, 값이 다름 | `calc_wrong_result` |
| NULL 처리, 빈값, 0으로 나옴 | `null_handling` |
| 중복 집계, 값이 두 배, overcounting | `aggregation_error` |

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
_TOOL_DOCS: dict[str, str]          # 툴 → 공식 문서 URL

# ── 키워드 매핑 딕셔너리 ──────────────────────────────────────────────────────
_CHART_KEYWORDS:     dict[str, list[str]]  # chart_type → 키워드 리스트
_CALC_KEYWORDS:      dict[str, list[str]]  # calc_type → 키워드 리스트
_FEATURE_KEYWORDS:   dict[str, list[str]]  # feature_type → 키워드 리스트
_SITUATION_KEYWORDS: dict[str, list[str]]  # situation_type → 키워드 리스트

# ── 가이드 데이터 (모드별 × 툴별 × 타입별) ───────────────────────────────────
_CHART_GUIDE:     dict[str, dict[str, list[str]]]  # tool → chart_type → steps
_CALC_GUIDE:      dict[str, dict[str, list[str]]]  # tool → calc_type → steps
_FEATURE_GUIDE:   dict[str, dict[str, list[str]]]  # tool → feature_type → steps
_SITUATION_GUIDE: dict[str, dict[str, list[str]]]  # tool → situation_type → steps

# ── 폴백 (매핑 안 될 때) ───────────────────────────────────────────────────────
_CHART_FALLBACK:     dict[str, list[str]]  # tool → 범용 차트 생성 단계
_CALC_FALLBACK:      dict[str, list[str]]  # tool → 범용 계산 필드 생성 단계
_FEATURE_FALLBACK:   dict[str, list[str]]  # tool → 주요 기능 목록 안내
_SITUATION_FALLBACK: dict[str, list[str]]  # tool → 범용 트러블슈팅 + 공식 문서

# ── 툴별 UI 용어 사전 ─────────────────────────────────────────────────────────
_TOOL_TERMS: dict[str, dict[str, str]]     # 컬럼명 치환에 사용

# ── 헬퍼 함수 ──────────────────────────────────────────────────────────────────
def _classify_intent(intent: str, situation: str) -> str:
    """intent + situation → 모드 결정
    반환값: 'recommend' | 'chart' | 'calc' | 'feature' | 'troubleshoot'
    """

def _fuzzy_match(text: str, keyword_map: dict[str, list[str]]) -> str | None:
    """키워드 맵에서 퍼지 매칭 → matched_type 또는 None"""

def _parse_columns(columns: str) -> list[str]:
    """컬럼 문자열 파싱 → 리스트"""

def _inject_columns(steps: list[str], col_list: list[str], tool: str) -> str:
    """단계 리스트에 컬럼명 치환 후 마크다운 반환"""

def _mode_recommend(intent: str, columns: str) -> str:
def _mode_chart(intent: str, columns: str, tool: str) -> str:
def _mode_calc(intent: str, columns: str, tool: str) -> str:
def _mode_feature(intent: str, tool: str) -> str:
def _mode_troubleshoot(intent: str, situation: str, tool: str) -> str:

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

**모드 0 — 추천:**
| 테스트 케이스 | 예상 결과 |
|-------------|----------|
| `bi_tool_guide("매출 추이를 보고싶다")` | 라인 차트 추천 + 4개 툴 비교 |

**모드 1 — 차트 생성:**
| 테스트 케이스 | 예상 결과 |
|-------------|----------|
| `bi_tool_guide("월별 추이", tool="tableau", columns="date, revenue")` | 컬럼명 포함 단계 가이드 |
| `bi_tool_guide("워터폴 차트", tool="looker")` | 폴백: 범용 차트 워크플로우 |
| `bi_tool_guide("KPI", tool="quicksight", columns="revenue")` | QuickSight KPI 가이드 |

**모드 2 — 계산/수식:**
| 테스트 케이스 | 예상 결과 |
|-------------|----------|
| `bi_tool_guide("고객별 최초구매일", tool="tableau", columns="customer_id, purchase_date")` | `{FIXED [customer_id] : MIN([purchase_date])}` 포함 가이드 |
| `bi_tool_guide("MoM 성장률", tool="powerbi", columns="date, revenue")` | DAX `DATEADD` 수식 포함 가이드 |
| `bi_tool_guide("알 수 없는 계산", tool="quicksight")` | 폴백: 범용 계산 필드 생성 |

**모드 3 — 기능 사용:**
| 테스트 케이스 | 예상 결과 |
|-------------|----------|
| `bi_tool_guide("매개변수 만들기", tool="tableau")` | Tableau Parameter 생성 가이드 |
| `bi_tool_guide("집합 생성", tool="tableau")` | Tableau Set 생성 가이드 |
| `bi_tool_guide("슬라이서 추가", tool="powerbi")` | Power BI Slicer 추가 가이드 |

**모드 4 — 트러블슈팅:**
| 테스트 케이스 | 예상 결과 |
|-------------|----------|
| `bi_tool_guide("연결이 안 된다", tool="powerbi", situation="연결 오류")` | 연결 오류 트러블슈팅 |
| `bi_tool_guide("함수가 오류남", tool="tableau", situation="함수 오류")` | 수식 오류 디버깅 가이드 |
| `bi_tool_guide("값이 두 배로 나와", tool="tableau")` | 중복 집계 해결 가이드 |
| `bi_tool_guide("이상한 질문", tool="powerbi", situation="알 수 없는 상황")` | 폴백: 범용 + 공식 문서 링크 |

**에러 케이스:**
| 테스트 케이스 | 예상 결과 |
|-------------|----------|
| `bi_tool_guide("", tool="tableau")` | `[ERROR] intent는 필수 파라미터` |
| `bi_tool_guide("차트", tool="unknown")` | `[ERROR] 지원하지 않는 툴` |

최소 2개/함수 (정상 + 에러) 원칙, 총 20개+ 테스트 목표.

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
