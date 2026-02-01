# BI-Agent 상세 구현 계획 (DETAILED_SPEC.md)

> [ 🗺️ 전략/로드맵 ](./PLAN.md) · **[ 🛠️ 상세 설계 ]** · [ 📋 현재 실행 (TODO)](./TODO.md) · [ 📜 변경 이력 (CHANGELOG)](./CHANGELOG.md)

---

**플랜 ID:** `bi-agent-detailed-implementation`
**생성일:** 2026-01-30
**최종 수정:** 2026-02-01 (유기적 문서 체계 적용)
**기반 문서:** [docs/core/PLAN.md](./PLAN.md)

---

## 요약 (Executive Summary)

이 계획은 BI-Agent의 15단계 로드맵에 대한 세부적인 구현 태스크를 제공합니다. 이 프로젝트의 목표는 분석가가 TUI(Terminal User Interface) 내에서 투명하고 제어 가능한 에이전트 시스템을 통해 BI 리포트를 얻을 수 있는 **지능형 분석 워크스페이스**를 구축하는 것입니다.

**Iteration 2 변경 사항:**
- 섹션 0 추가: 기반 리팩토링 (BaseIntent 아키텍처)
- 섹션 9 추가: 신규 의존성 패키지
- 태스크 5.1.2, 10.2.2용 LLM 프롬프트 템플릿 추가
- Textual 화면 통합 패턴 추가
- Tableau .twb 내보내기 제거 (향후 단계로 연기)
- 측정 가능한 임계치를 포함한 수용 기준(Acceptance Criteria) 수정

---

## 0. 기반 리팩토링 (사전 필수 조건)

이 섹션은 Phase 2 태스크가 시작되기 전에 반드시 완료되어야 합니다. 이는 공유 의도(Shared Intent) 아키텍처를 수립합니다.

### 0.1 BaseIntent 추상 베이스 클래스 생성
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/base_intent.py` (신규)

**근거:** `ChartIntent`와 `AnalysisIntent`는 공통 필드(필터, 데이터 소스)를 공유합니다. 공유 베이스 클래스를 통해 일관성을 보장하고 다형적 처리를 가능하게 합니다.

**구현 태스크:**

| ID | 태스크 | 수용 기준 (Acceptance Criteria) |
|----|------|---------------------|
| 0.1.1 | `BaseIntent` 추상 베이스 클래스 생성 | `@abstractmethod validate()`를 포함한 ABC |
| 0.1.2 | 공통 필드 정의 | `datasource`, `filters`, `title`을 기본 필드로 정의 |
| 0.1.3 | `to_dict()` 메서드 추가 | 데이터클래스 필드를 딕셔너리로 반환 |
| 0.1.4 | 타입 구분자 추가 | `intent_type` 속성이 "chart" 또는 "analysis" 반환 |

**코드:**
```python
# /backend/agents/bi_tool/base_intent.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

@dataclass
class BaseIntent(ABC):
    """BI-Agent의 모든 의도 타입에 대한 추상 베이스 클래스.

    공유 필드:
    - datasource: 대상 테이블/데이터셋 이름
    - filters: 필터 조건 리스트 [{field, operator, value}]
    - title: 선택적 설명 제목
    """
    datasource: str
    filters: List[Dict[str, Any]]
    title: Optional[str] = None

    @property
    @abstractmethod
    def intent_type(self) -> str:
        """의도 하위 타입을 식별하기 위해 'chart' 또는 'analysis' 반환"""
        pass

    @abstractmethod
    def validate(self) -> bool:
        """의도 구조 검증. 유효하면 True 반환"""
        pass

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 표현으로 변환"""
        return asdict(self)
```

### 0.2 ChartIntent가 BaseIntent를 확장하도록 리팩토링
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/nl_intent_parser.py`

**구현 태스크:**

| ID | 태스크 | 수용 기준 |
|----|------|---------------------|
| 0.2.1 | `base_intent.py`에서 `BaseIntent` 임포트 | 임포트 구문 추가 완료 |
| 0.2.2 | `ChartIntent`가 `BaseIntent`를 상속하도록 변경 | `class ChartIntent(BaseIntent):` |
| 0.2.3 | 공통 필드를 `super().__init__()`으로 이동 | `datasource`, `filters`, `title` |
| 0.2.4 | `intent_type` 속성 구현 | `"chart"` 반환 |
| 0.2.5 | 유닛 테스트 업데이트 | 리팩토링된 클래스로 기존 테스트 통과 |

**리팩토링된 ChartIntent:**
```python
# nl_intent_parser.py에서 업데이트됨
from backend.agents.bi_tool.base_intent import BaseIntent

@dataclass
class ChartIntent(BaseIntent):
    """차트 생성/수정 의도의 구조화된 표현"""
    action: str  # "create", "modify", "delete"
    visual_type: str  # "bar", "line", "pie", "table", "scatter", "area"
    dimensions: List[str]
    measures: List[str]
    aggregation: Optional[str] = None
    time_period: Optional[str] = None

    @property
    def intent_type(self) -> str:
        return "chart"

    def validate(self) -> bool:
        if self.action not in ["create", "modify", "delete"]:
            return False
        if self.visual_type not in ["bar", "line", "pie", "table", "scatter", "area"]:
            return False
        if not self.datasource:
            return False
        if self.action in ["create", "modify"] and not (self.dimensions or self.measures):
            return False
        return True
```

### 0.3 AnalysisIntent 클래스 생성
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/analysis_intent.py` (신규)

**구현 태스크:**

| ID | 태스크 | 수용 기준 |
|----|------|---------------------|
| 0.3.1 | `BaseIntent`를 상속한 `AnalysisIntent` 생성 | `validate()` 및 `intent_type` 구현 |
| 0.3.2 | 분석 전용 필드 추가 | `purpose`, `target_metrics`, `hypothesis`, `expected_output` |
| 0.3.3 | `produces_charts()` 메서드 추가 | 분석에서 생성된 `List[ChartIntent]` 반환 |
| 0.3.4 | AnalysisIntent용 유닛 테스트 | 검증 로직을 포함한 5개 이상의 테스트 케이스 |

**코드:**
```python
# /backend/agents/bi_tool/analysis_intent.py
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from backend.agents.bi_tool.base_intent import BaseIntent

@dataclass
class AnalysisIntent(BaseIntent):
    """복합 분석 의도의 구조화된 표현.

    AnalysisIntent는 실행 중에 여러 ChartIntent를 생성할 수 있는 
    상위 수준의 분석 목표를 나타냅니다.

    관계: AnalysisIntent -> 생성 -> ChartIntent[]
    """
    purpose: str  # "performance" | "trend" | "anomaly" | "comparison" | "forecast"
    target_metrics: List[str] = field(default_factory=list)
    time_range: Optional[Dict[str, str]] = None  # {"start": "2024-01-01", "end": "2024-12-31"}
    hypothesis: Optional[str] = None
    expected_output: str = "dashboard"  # "dashboard" | "report" | "insight"
    scope: Optional[str] = None  # "전체", "서울지역" 등
    constraints: List[str] = field(default_factory=list)  # 추가 제약 조건
    kpis: List[str] = field(default_factory=list)  # 주요 성과 지표

    @property
    def intent_type(self) -> str:
        return "analysis"

    def validate(self) -> bool:
        valid_purposes = ["performance", "trend", "anomaly", "comparison", "forecast", "correlation"]
        if self.purpose not in valid_purposes:
            return False
        if not self.datasource:
            return False
        if not self.target_metrics and not self.kpis:
            return False
        return True

    def produces_charts(self) -> List["ChartIntent"]:
        """AnalysisIntent에서 ChartIntent 생성.

        실제 차트 생성은 파이프라인 생성기에서 처리하지만, 
        이 메서드는 예상되는 차트 타입의 미리보기를 제공합니다.
        """
        from backend.agents.bi_tool.nl_intent_parser import ChartIntent

        charts = []
        # 목적을 예상 차트 타입으로 매핑
        purpose_chart_map = {
            "trend": "line",
            "comparison": "bar",
            "performance": "bar",
            "anomaly": "scatter",
            "forecast": "line",
            "correlation": "scatter"
        }

        default_type = purpose_chart_map.get(self.purpose, "bar")

        for metric in self.target_metrics[:3]:  # 최대 3개 차트
            charts.append(ChartIntent(
                action="create",
                visual_type=default_type,
                datasource=self.datasource,
                dimensions=[],  # 파이프라인에서 채워짐
                measures=[metric],
                filters=self.filters.copy(),
                title=f"{metric} {self.purpose} 분석"
            ))

        return charts
```

### 0.4 검증 체크포인트
Phase 2로 진행하기 전:

| 체크포인트 | 검증 명령어 |
|------------|---------------------|
| BaseIntent 존재 확인 | `python -c "from backend.agents.bi_tool.base_intent import BaseIntent"` |
| ChartIntent 상속 확인 | `python -c "from backend.agents.bi_tool.nl_intent_parser import ChartIntent; assert ChartIntent.__bases__[0].__name__ == 'BaseIntent'"` |
| AnalysisIntent 존재 확인 | `python -c "from backend.agents.bi_tool.analysis_intent import AnalysisIntent"` |
| 테스트 통과 | `pytest tests/test_intents.py -v` (테스트 파일 생성 필요) |

---

## BI-Agent 개발 현황 (TODO.md)

> [ 🗺️ 전략/로드맵 ](./PLAN.md) · [ 🛠️ 상세 설계 (DETAILED_SPEC)](./DETAILED_SPEC.md) · **[ 📋 현재 실행 ]** · [ 📜 변경 이력 (CHANGELOG)](./CHANGELOG.md)

---

> 마지막 업데이트: 2026-02-01 (유기적 문서 체계 적용)
> 목표: 15단계 초정밀 여정 구현을 통한 분석가 최적화 워크스페이스 구축

## 1. 현재 상태 평가

### 1.1 완료 (Phase 1: Step 1-3)

| 단계 | 기능 | 상태 | 구현 파일 |
|------|---------|--------|---------------------|
| Step 1 | 실행 | **완료** | `backend/orchestrator/bi_agent_console.py` (ASCII 배너, 환경 체크) |
| Step 2 | 스마트 인증 | **완료** | `backend/orchestrator/auth_manager.py`, 콘솔 내 `AuthScreen` |
| Step 3 | 연결 | **완료** | `backend/agents/data_source/connection_manager.py`, `ConnectionScreen` |

### 1.2 부분 구현 (기반 요소)

| 컴포넌트 | 상태 | 위치 |
|-----------|--------|----------|
| LLM 공급자 시스템 | 작동 중 | `backend/orchestrator/llm_provider.py` (Gemini, Claude, OpenAI, Ollama 장애 복구) |
| 메타데이터 스캐너 | 작동 중 | `backend/agents/data_source/metadata_scanner.py` |
| 데이터 프로파일러 | 작동 중 | `backend/agents/data_source/profiler.py` |
| 자연어 의도 파서 | 존재 (통합 필요) | `backend/agents/bi_tool/nl_intent_parser.py` |
| 인터랙션 로직 | 기본 수준 | `backend/agents/bi_tool/interaction_logic.py` |
| 인하우스 생성기 | 작동 중 | `backend/agents/bi_tool/inhouse_generator.py` |
| 테마 엔진 | 작동 중 | `backend/agents/bi_tool/theme_engine.py` |
| 협업 오케스트레이터 | 부분 완료 | `backend/orchestrator/collaborative_orchestrator.py` |
| TUI 메시지 컴포넌트 | 작동 중 | `backend/orchestrator/message_components.py` |

### 1.3 시작 전 (Step 4-15)

Phase 2-5의 모든 단계는 처음부터 구현하거나 대폭적인 강화가 필요합니다.

---

## 2. 기술적 의존성 그래프

```
섹션 0 (BaseIntent) ──────────────────────────────────────────────────┐
                                                                        v
Step 4 (의도) ──────┐
                     ├──> Step 7 (플랜 수립) ──> Step 10 (쿼리 생성)
Step 5 (타겟팅) ───┤                               │
                     │                               v
Step 6 (스캐닝) ────┘                    Step 11 (자인) ──> Step 13 (브리핑)
                                                   │                      │
                                                   v                      v
                                          Step 12 (인터랙션) ──> Step 14 (교정)
                                                                           │
Step 8 (사고 CoT) ─────────────────────────────────────────────────────────┤
Step 9 (정렬) ─────────────────────────────────────────────────────────────┤
                                                                           v
                                                                    Step 15 (내보내기)
```

---

## 3. Phase 2: 의도 파악 및 컨텍스트 스캐닝 (Step 4-6)

### Step 4: 분석 의도 선언 (Analysis Intent Declaration)

**목표:** 사용자가 `/intent` 명령어를 통해 복합적인 분석 의도를 선언하면 LLM이 실행 계획을 생성할 수 있도록 지원.

#### Task 4.1: `/intent` 명령어 핸들러 강화
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/orchestrator/bi_agent_console.py`

**현재 상태:** 기본적인 `/intent` 명령어는 존재하나(883-895라인), 전체 파이프라인 없이 `handle_intent()`로 전달만 됨.

**구현 태스크:**

| ID | 태스크 | 수용 기준 |
|----|------|---------------------|
| 4.1.1 | 인자 추출을 포함한 의도 파싱 | `/intent 매출 하락 원인 분석`에서 `intent_text = "매출 하락 원인 분석"` 추출 |
| 4.1.2 | 플랜 생성 중 사고 과정 패널 표시 | `ThinkingPanel` 위젯에 "의도 분석 중...", "플랜 생성 중..." 표시 |
| 4.1.3 | 세션 컨텍스트에 의도 저장 | `self.orchestrator.current_intent`에 구조화된 의도 객체 보유 |
| 4.1.4 | 생성된 플랜을 선택 가능한 단계로 렌더링 | 각 단계가 체크박스가 있는 번호 있는 리스트로 표시 |

**코드 변경:**
```python
# bi_agent_console.py에서 "/intent"를 처리하는 handle_command() 강화
# 추가: 파싱된 의도를 저장할 IntentSession 데이터클래스
# 추가: 단계별 플랜을 렌더링할 PlanDisplayWidget
```

#### Task 4.2: LLM 기반 의도 분류
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/nl_intent_parser.py`

**현재 상태:** `NLIntentParser`가 존재하나 차트 의도 파싱에만 집중되어 있음.

**구현 태스크:**

| ID | 태스크 | 수용 기준 |
|----|------|---------------------|
| 4.2.1 | `AnalysisIntent` 임포트 추가 | `from backend.agents.bi_tool.analysis_intent import AnalysisIntent` |
| 4.2.2 | `parse_analysis_intent()` 메서드 생성 | 한/영 자연어 입력에서 `AnalysisIntent` 반환 |
| 4.2.3 | 목적(Purpose) 자동 추출 구현 | "성능" -> performance, "추이" -> trend, "이상치" -> anomaly 등 |
| 4.2.4 | 의도 파싱 유닛 테스트 | 한/영 입력을 포괄하는 10개 이상의 테스트 케이스 |

**Task 4.2.2용 LLM 프롬프트 템플릿:**
```python
ANALYSIS_INTENT_PROMPT = """당신은 BI 분석 의도 파서입니다. 다음 자연어 요청을 구조화된 분석 의도로 파싱하십시오.

사용자의 요청은 한국어 또는 영어입니다. 다음 정보를 추출하십시오:

1. **purpose**: 분석 목적 - "performance", "trend", "anomaly", "comparison", "forecast", "correlation"
2. **target_metrics**: 분석할 지표/KPI 리스트 (예: ["매출", "주문수", "고객수"])
3. **datasource**: 대상 데이터 소스 또는 테이블 (추론 가능하면 포함)
4. **time_range**: {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"} 형태의 기간 또는 null
5. **hypothesis**: 검증할 가설 (언급된 경우, 아니면 null)
6. **expected_output**: 출력 형식 - "dashboard", "report" 또는 "insight"
7. **filters**: "field", "operator", "value"를 가진 필터 조건 리스트
8. **scope**: 분석 범위 설명 (예: "전체", "서울지역", "온라인채널")
9. **constraints**: 리스트 형태의 추가 제약 조건
10. **kpis**: 추적할 주요 성과 지표

**한국어-영어 목적 매핑:**
- 추이/트렌드/동향 = trend
- 성능/성과/실적 = performance
- 이상치/이상/비정상 = anomaly
- 비교/대조 = comparison
- 예측/전망/예상 = forecast
- 상관/관계 = correlation

**한국어-영어 필드 매핑:**
- 매출/판매액 = sales
- 주문/주문수 = orders
- 고객/고객수 = customers
- 월/월별 = month
- 지역 = region
- 카테고리 = category
- 제품/상품 = product

사용자 요청: "{user_input}"

응답은 반드시 다음 형식을 정확히 따르는 유효한 JSON이어야 합니다:
{{
    "purpose": "trend|performance|anomaly|comparison|forecast|correlation",
    "target_metrics": ["metric1", "metric2"],
    "datasource": "table_name",
    "time_range": {{"start": "2024-01-01", "end": "2024-12-31"}} or null,
    "hypothesis": "가설 문장" or null,
    "expected_output": "dashboard|report|insight",
    "filters": [{{"field": "region", "operator": "=", "value": "Seoul"}}],
    "scope": "분석 범위",
    "constraints": ["제약조건1", "제약조건2"],
    "kpis": ["KPI1", "KPI2"],
    "title": "분석 제목"
}}

JSON만 반환하고 추가적인 텍스트나 설명은 생략하십시오."""
```

#### Task 4.3: 명령어 히스토리 및 탭 완성
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/orchestrator/bi_agent_console.py`

**현재 상태:** 기본적인 명령어 탭 완성 기능은 있으나(748-773라인), 히스토리가 없음.

**구현 태스크:**

| ID | 태스크 | 수용 기준 |
|----|------|---------------------|
| 4.3.1 | `CommandHistory` 클래스 추가 | 마지막 100개 명령어를 `~/.bi-agent/history.json`에 저장 |
| 4.3.2 | 위/아래 방향키 네비게이션 | 위를 누르면 이전 명령, 아래를 누르면 다음 명령 표시 |
| 4.3.3 | 의도 문구 탭 완성 | "매출", "분석", "추이" 등 공통 문구 자동 완성 |
| 4.3.4 | 세션 간 히스토리 유지 | 시작 시 히스토리 로드, `/intent` 실행 시 저장 |

---

### Step 5: 타겟 데이터 선정 (Target Data Selection)

**목표:** 사용자의 쿼리에 대해 LLM 결과가 관련 테이블을 추천하고, 인터랙티브한 테이블 선택 UI 제공.

#### Task 5.1: 테이블 추천 알고리즘
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/data_source/table_recommender.py` (신규)

**구현 태스크:**

| ID | 태스크 | 수용 기준 |
|----|------|---------------------|
| 5.1.1 | `TableRecommender` 클래스 생성 | `AnalysisIntent` + 스키마 메타데이터 기반 랭킹된 테이블 리스트 반환 |
| 5.1.2 | LLM 기반 관련성 점수 산정 | 각 테이블에 대해 0-100 점수 및 근거 부여 |
| 5.1.3 | 컬럼 의미론적 매칭 | 의도 키워드와 컬럼명/설명 매칭 |
| 5.1.4 | 다중 테이블 관계 감지 | 잠재적인 JOIN 관계 식별 |

**Task 5.1.2용 LLM 프롬프트 템플릿:**
```python
TABLE_RECOMMENDATION_PROMPT = """당신은 분석에 적합한 테이블을 선정하는 데이터베이스 전문가입니다.

**분석 의도:**
- 목적: {purpose}
- 타겟 지표: {target_metrics}
- 가설: {hypothesis}
- 필터: {filters}

**사용 가능한 데이터베이스 스키마:**
{schema_json}

**과업:**
스키마의 각 테이블에 대해 다음을 제공하십시오:
1. 해당 분석에 얼마나 유용한지 나타내는 관련성 점수 (0-100)
2. 해당 점수가 부여된 이유에 대한 간략한 한국어 설명
3. 해당 테이블에서 분석과 관련된 컬럼들
4. 다른 테이블과의 잠재적인 JOIN 관계

**점수 가이드라인:**
- 90-100: 테이블이 타겟 지표와 차원을 직접 포함함
- 70-89: 테이블이 분석을 지원하는 관련 데이터를 포함함
- 50-69: 테이블이 컨텍스트나 필터링에 유용할 수 있음
- 0-49: 테이블이 이 분석과 관련 없음

다음 형식의 JSON 배열로 반환하십시오:
[
    {{
        "table_name": "sales",
        "relevance_score": 95,
        "explanation_ko": "매출 분석에 필요한 금액, 날짜, 고객ID 컬럼을 포함합니다.",
        "relevant_columns": ["amount", "date", "customer_id"],
        "join_suggestions": [
            {{"target_table": "customers", "join_column": "customer_id", "target_column": "id"}}
        ]
    }}
]

JSON 배열만 반환하고 추가 텍스트는 생략하십시오."""
```

**클래스 골격:**
```python
class TableRecommender:
    def __init__(self, llm: LLMProvider, schema: Dict[str, Any]):
        self.llm = llm
        self.schema = schema

    async def recommend_tables(self, intent: AnalysisIntent) -> List[TableRecommendation]:
        """랭킹된 TableRecommendation 객체 리스트 반환"""
        pass

    async def infer_relationships(self, tables: List[str]) -> List[ERDRelationship]:
        """FK/PK 관계 감지 및 JOIN 제안"""
        pass
```

---

### Step 6: Deep Scanning (데이터 딥 스캐닝)

**목표:** 실시간 통계 프로파일링, 샘플 데이터 표시 및 데이터 타입 자동 교정.

#### Task 6.1: 향상된 컬럼 통계
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/data_source/profiler.py`

**현재 상태:** mean, std, min, max, top_values를 포함한 기초 프로파일링 존재.

**구현 태스크:**

| ID | 태스크 | 수용 기준 |
|----|------|---------------------|
| 6.1.1 | 컬럼별 결측치 비율 추가 | 컬럼 상세에 `missing_pct` 필드 추가 |
| 6.1.2 | 최빈값(Mode) 추가 | 모든 컬럼 타입에 대해 `mode` 필드 추가 |
| 6.1.3 | 사분위수(25%, 50%, 75%) 추가 | 수치형 컬럼에 대해 `q25`, `q50`, `q75` 추가 |
| 6.1.4 | 값 분포 히스토그램 데이터 추가 | 빈(bin) 카운트가 포함된 `distribution` 필드 추가 |
| 6.1.5 | 데이터 품질 점수 추가 | 완전성, 일관성에 기반한 0-100 점수 산출 |

**향상된 출력 예시:**
```python
{
    "name": "sales_amount",
    "type": "numerical",
    "missing_pct": 2.5,
    "unique": 1432,
    "mean": 1500.50,
    "std": 350.25,
    "min": 10.0,
    "max": 9999.99,
    "q25": 800.0,
    "q50": 1400.0,
    "q75": 2100.0,
    "mode": 1000.0,
    "distribution": {"bins": [...], "counts": [...]},
    "quality_score": 95
}
```

#### Task 6.2: 샘플 데이터 그리드 컴포넌트
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/orchestrator/components/data_grid.py` (신규)

**구현 태스크:**

| ID | 태스크 | 수용 기준 |
|----|------|---------------------|
| 6.2.1 | `SampleDataGrid` Textual 위젯 생성 | 스크롤 가능한 DataTable에 5-10개 행 표시 |
| 6.2.2 | 컬럼 타입 인디케이터 | 아이콘: 📊 수치형, 📝 텍스트, 📅 날짜시간, 🏷️ 범주형 |
| 6.2.3 | 긴 값 잘라내기 | 50자 초과 값은 "..." 표시 및 호버 시 전체 값 노출 |
| 6.2.4 | 샘플 데이터를 클립보드로 내보내기 | Ctrl+C 입력 시 선택된 행을 CSV로 복사 (`pyperclip` 필요) |

#### Task 6.3: 데이터 타입 자동 교정
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/data_source/type_corrector.py` (신규)

**구현 태스크:**

| ID | 태스크 | 수용 기준 |
|----|------|---------------------|
| 6.3.1 | 텍스트로 오인된 날짜 문자열 감지 | `"2024-01-15"`를 텍스트가 아닌 datetime으로 감지 |
| 6.3.2 | 숫자형 문자열 감지 | `"1,234.56"` 또는 `"1234"`를 수치형으로 감지 |
| 6.3.3 | 타입 교정 제안 | `{column, current_type, suggested_type, confidence}` 리스트 반환 |
| 6.3.4 | 사용자 승인 시 교정 적용 | 사용자가 각 제안에 대해 승인/거부 선택 |

---

## 4. Phase 3: Strategy & Hypothesis (Steps 7-9)

### Step 7: Analysis Execution Plan (분석 실행 플랜 수립)

**목표:** `/intent`로부터 상세 분석 파이프라인 생성, 산업별 템플릿 및 ROI 시뮬레이션 활용.

#### Task 7.1: 파이프라인 생성 엔진
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/pipeline_generator.py` (신규)

**구현 태스크:**

| ID | 태스크 | 수용 기준 |
|----|------|---------------------|
| 7.1.1 | `AnalysisPipeline` 데이터클래스 생성 | 필드: `steps[]`, `estimated_duration`, `required_data`, `expected_outputs` |
| 7.1.2 | LLM이 3-7단계 파이프라인 생성 | 각 단계: action, description, agent_type, dependencies 포함 |
| 7.1.3 | 파이프라인 실행 가능성 검증 | 필요한 컬럼/테이블이 스키마에 존재하는지 확인 |
| 7.1.4 | 파이프라인 직렬화 | 파이프라인을 `.bi-agent/pipelines/{name}.json`에 저장/로드 |

**Task 7.1.2를 위한 LLM 프롬프트 템플릿:**
```python
PIPELINE_GENERATION_PROMPT = """당신은 BI 분석 설계자입니다. 다음 분석 의도에 대한 실행 파이프라인을 생성하십시오.

**분석 의도:**
- 목적: {purpose}
- 타겟 지표: {target_metrics}
- 가설: {hypothesis}
- 선택된 테이블: {selected_tables}
- 제약 조건: {constraints}

**사용 가능한 스키마:**
{schema_json}

**과업:**
3-7단계의 분석 파이프라인을 생성하십시오. 각 단계는 다음과 같아야 합니다:
1. 실행 가능하고 구체적일 것
2. 에이전트 타입이 할당될 것
3. 명확한 입력/출력 데이터가 있을 것

**에이전트 타입:**
- DataMaster: 데이터 프로파일링, 품질 검사, 변환
- Strategist: 가설 생성, 인사이트 추출, 권고안
- Designer: 차트 생성, 레이아웃 설계, 시각화

반환 형식 (JSON):
{{
    "pipeline_name": "분석 파이프라인 이름",
    "estimated_total_seconds": 120,
    "steps": [
        {{
            "step_id": "step_1",
            "action": "profile",
            "description_ko": "sales 테이블의 데이터 품질을 검증합니다",
            "agent": "DataMaster",
            "input_data": ["sales"],
            "output_data": "profile_result",
            "estimated_seconds": 15,
            "dependencies": []
        }},
        {{
            "step_id": "step_2",
            "action": "query",
            "description_ko": "월별 매출 데이터를 집계합니다",
            "agent": "DataMaster",
            "input_data": ["sales", "profile_result"],
            "output_data": "monthly_sales",
            "estimated_seconds": 30,
            "dependencies": ["step_1"]
        }}
    ]
}}

JSON만 반환하고 다른 텍스트는 생략하십시오."""
```

**파이프라인 단계 구조:**
```python
@dataclass
class PipelineStep:
    step_id: str
    action: str  # "profile", "query", "transform", "visualize", "insight"
    description: str  # 한국어 설명
    agent: str  # "DataMaster", "Strategist", "Designer"
    input_data: List[str]
    output_data: str
    estimated_seconds: int
    dependencies: List[str]  # 먼저 완료되어야 하는 step_id 리스트
```

#### Task 7.2: 가설 템플릿 엔진
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/hypothesis_templates.py` (신규)

**구현 태스크:**

| ID | 태스크 | 수용 기준 |
|----|------|---------------------|
| 7.2.1 | 산업별 템플릿 레지스트리 생성 | 소매, 금융, 제조, 의료용 템플릿 |
| 7.2.2 | 플레이스홀더를 포함한 템플릿 형식 | `"{{metric}} 성장은 {{dimension}}에 비례한다"` |
| 7.2.3 | 문맥 인식형 템플릿 선택 | 감지된 컬럼에 기반하여 관련 템플릿 제안 |
| 7.2.4 | 사용자 정의 템플릿 기능 | 적용 전 플레이스홀더 편집 가능 |

**템플릿 예시:**
```python
RETAIL_TEMPLATES = [
    "{{매출}} 증가는 {{요일}} 트래픽과 비례한다",
    "{{카테고리}}별 {{반품률}}은 계절에 따라 변동한다",
    "{{신규고객}} 유입은 {{마케팅채널}} 효과에 의존한다"
]
```

#### Task 7.3: ROI 시뮬레이션 미리보기
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/roi_simulator.py` (신규)

**구현 태스크:**

| ID | 태스크 | 수용 기준 |
|----|------|---------------------|
| 7.3.1 | 분석 가치를 정성적으로 추정 | 출력: "이 분석은 매출 향상에 기여할 가능성이 높습니다" |
| 7.3.2 | LLM이 비즈니스 가치 진술 생성 | 의도 및 산업 문맥에 기반 |
| 7.3.3 | 신뢰 수준 표시 | High(>=0.7)/Medium(0.4-0.69)/Low(<0.4) 신뢰도와 근거 제시 |
| 7.3.4 | 과거 유사 사례 비교 (가능한 경우) | "과거 유사 분석 결과 평균 ROI: +8%" |

---

### Step 8: Thinking Process Visualization (사고 과정 시각화)

**목표:** 에이전트 내부 메시지 및 LLM "사고" 단계를 실시간으로 표시.

#### Task 8.1: 에이전트 메시지 버스
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/orchestrator/agent_message_bus.py` (신규)

**아키텍처 결정:** Redis가 아닌 Textual 워커 패턴을 활용한 `asyncio.Queue` 사용.

**구현 태스크:**

| ID | 태스크 | 수용 기준 |
|----|------|---------------------|
| 8.1.1 | `AgentMessageBus` 클래스 생성 | `asyncio.Queue` 기반 pub/sub 시스템 |
| 8.1.2 | 메시지 타입 정의 | `THINKING`, `DATA_REQUEST`, `DATA_RESPONSE`, `INSIGHT`, `ERROR` |
| 8.1.3 | TUI를 메시지 버스에 구독 시키기 | 콘솔이 Textual 워커를 통해 모든 메시지 수신 |
| 8.1.4 | 메시지 지속성 관리 | 메시지를 `logs/agent_messages.jsonl`에 저장 |

**구현 코드:**
```python
# /backend/orchestrator/agent_message_bus.py
import asyncio
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any, Callable, List, Optional
from enum import Enum
import json
from pathlib import Path

class MessageType(Enum):
    THINKING = "thinking"
    DATA_REQUEST = "data_request"
    DATA_RESPONSE = "data_response"
    INSIGHT = "insight"
    ERROR = "error"
    PROGRESS = "progress"
    COMPLETE = "complete"

@dataclass
class AgentMessage:
    timestamp: datetime
    from_agent: str  # "DataMaster", "Strategist", "Designer"
    to_agent: str  # 대상 에이전트 또는 "broadcast"
    message_type: MessageType
    content: str  # 한국어 메시지 내용
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        d['message_type'] = self.message_type.value
        return d

class AgentMessageBus:
    """에이전트-에이전트 및 에이전트-TUI 통신을 위한 비동기 메시지 버스.

    외부 의존성 없이 스레드 안전한 메시지 전달을 위해 asyncio.Queue를 사용합니다.
    UI 업데이트를 위해 Textual의 워커 패턴과 통합됩니다.
    """

    _instance: Optional['AgentMessageBus'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._queue: asyncio.Queue[AgentMessage] = asyncio.Queue()
        self._subscribers: List[Callable[[AgentMessage], None]] = []
        self._running = False
        self._log_path = Path("logs/agent_messages.jsonl")
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialized = True

    def subscribe(self, callback: Callable[[AgentMessage], None]) -> None:
        """모든 메시지를 수신하기 위해 구독합니다."""
        self._subscribers.append(callback)

    async def publish(self, message: AgentMessage) -> None:
        """모든 구독자에게 메시지를 발행합니다."""
        await self._queue.put(message)
        # 로그 파일에 저장
        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(message.to_dict(), ensure_ascii=False) + "\n")

    async def start(self) -> None:
        """메시지 디스패치 루프를 시작합니다."""
        self._running = True
        while self._running:
            try:
                message = await asyncio.wait_for(self._queue.get(), timeout=0.1)
                for subscriber in self._subscribers:
                    try:
                        subscriber(message)
                    except Exception as e:
                        print(f"Subscriber error: {e}")
            except asyncio.TimeoutError:
                continue

    def stop(self) -> None:
        """메시지 디스패치 루프를 중단합니다."""
        self._running = False
```

#### Task 8.2: 사고 단계 번역기
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/orchestrator/thinking_translator.py` (신규)

**구현 태스크:**

| ID | 태스크 | 수용 기준 |
|----|------|---------------------|
| 8.2.1 | LLM 내부 상태를 한국어 라벨로 매핑 | "스키마 해석 중...", "가설 생성 중...", "쿼리 최적화 중..." |
| 8.2.2 | 단계 전환 감지 | LLM이 스키마 분석에서 쿼리 생성으로 전환되는 시점 포착 |
| 8.2.3 | 진행 표시기 출력 | 프로그레스 바와 함께 "2/5 단계 완료" 표시 |
| 8.2.4 | 예상 남은 시간 표시 | "예상 남은 시간: 30초" |

#### Task 8.3: 실시간 ThinkingPanel 업데이트
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/orchestrator/message_components.py`

**현재 상태:** `ThinkingPanel`이 존재하지만 정적임.

**구현 태스크:**

| ID | 태스크 | 수용 기준 |
|----|------|---------------------|
| 8.3.1 | ThinkingPanel을 AgentMessageBus에 연결 | 새로운 메시지 도착 시 자동 업데이트 |
| 8.3.2 | 단계별 체크마크 추가 | 완료된 단계는 ✓, 진행 중인 단계는 ⏳ 표시 |
| 8.3.3 | 상세 내용 확장 기능 | 단계 클릭 시 상세 내용 노출 |
| 8.3.4 | 활성 단계 애니메이션 | 현재 진행 중인 단계에 펄싱(pulsing) 인디케이터 적용 |

---

### Step 9: User Alignment (사용자 정렬)

**목표:** 대화형 가설 선택, 제약 조건 입력 및 승인 워크플로우 구축.

#### Task 9.1: 가설 선택 화면
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/orchestrator/screens/hypothesis_screen.py` (신규)

**구현 태스크:**

| ID | 태스크 | 수용 기준 |
|----|------|---------------------|
| 9.1.1 | `HypothesisScreen` 모달 생성 | 생성된 가설을 선택 가능한 옵션으로 표시 |
| 9.1.2 | 가설 텍스트 편집 기능 | 승인 전 사용자가 텍스트 수정 가능 |
| 9.1.3 | 우선순위 지정 | 가설의 우선순위 설정 가능 |
| 9.1.4 | 원치 않는 가설 제외 | 분석 범위에서 특정 가설을 제거 |

**Textual 화면 통합 패턴:**
```python
# /backend/orchestrator/screens/hypothesis_screen.py
"""
사용자 정렬(Step 9)을 위한 가설 선택 화면.

bi_agent_console.py와의 통합:
1. 임포트: from backend.orchestrator.screens.hypothesis_screen import HypothesisScreen
2. 화면 푸시: self.push_screen(HypothesisScreen(hypotheses, on_confirm_callback))
3. 콜백 처리: def on_confirm_callback(selected_hypotheses: List[Hypothesis]): ...
"""

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, Button, OptionList, Input
from textual.containers import Container, Vertical, Horizontal
from textual.widgets.option_list import Option
from dataclasses import dataclass
from typing import List, Callable, Optional

@dataclass
class Hypothesis:
    id: str
    text: str
    priority: int = 0
    selected: bool = True
    edited: bool = False

class HypothesisScreen(ModalScreen):
    """
    대화형 가설 선택 및 편집 화면.
    """

    CSS = """
    HypothesisScreen {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }
    #hypothesis-modal {
        width: 70;
        height: auto;
        max-height: 80%;
        background: #1a1b1e;
        border: solid #2d2f34;
        padding: 1 2;
    }
    #hypothesis-title {
        text-align: center;
        color: #f8fafc;
        text-style: bold;
        margin-bottom: 2;
    }
    #hypothesis-list {
        height: auto;
        max-height: 15;
        margin-bottom: 1;
        background: #111214;
        border: solid #2d2f34;
    }
    .hypothesis-item {
        padding: 1;
    }
    .hypothesis-item.selected {
        background: #1e3a5f;
    }
    #edit-input {
        margin: 1 0;
        background: #111214;
        border: solid #7c3aed;
    }
    .action-btn {
        margin: 0 1;
    }
    #confirm-btn {
        background: #22c55e;
    }
    #cancel-btn {
        background: #ef4444;
    }
    """

    BINDINGS = [
        ("y", "confirm", "승인"),
        ("n", "cancel", "취소"),
        ("e", "edit", "선택된 항목 편집"),
        ("space", "toggle", "선택 토글"),
        ("escape", "cancel", "취소"),
    ]

    def __init__(self, hypotheses: List[Hypothesis], callback: Callable[[List[Hypothesis]], None]):
        super().__init__()
        self.hypotheses = hypotheses
        self.callback = callback
        self.selected_index = 0

    def compose(self) -> ComposeResult:
        with Container(id="hypothesis-modal"):
            yield Label("생성된 가설 (선택 및 편집)", id="hypothesis-title")
            yield Label("[dim]Space: 토글 | E: 편집 | Y: 승인 | N: 취소[/dim]")

            options = []
            for i, h in enumerate(self.hypotheses):
                prefix = "[x]" if h.selected else "[ ]"
                options.append(Option(f"{prefix} {i+1}. {h.text}", id=h.id))

            yield OptionList(*options, id="hypothesis-list")
            yield Input(id="edit-input", placeholder="가설 내용을 수정하세요...")

            with Horizontal():
                yield Button("[+ 커스텀 추가]", id="add-btn", classes="action-btn")
                yield Button("[Y] 승인", id="confirm-btn", classes="action-btn")
                yield Button("[N] 취소", id="cancel-btn", classes="action-btn")

    def on_mount(self) -> None:
        self.query_one("#hypothesis-list").focus()
        self.query_one("#edit-input").display = False

    def action_confirm(self) -> None:
        selected = [h for h in self.hypotheses if h.selected]
        self.callback(selected)
        self.dismiss()

    def action_cancel(self) -> None:
        self.dismiss()

    def action_toggle(self) -> None:
        option_list = self.query_one("#hypothesis-list", OptionList)
        if option_list.highlighted is not None:
            idx = option_list.highlighted
            self.hypotheses[idx].selected = not self.hypotheses[idx].selected
            # UI 갱신 로직 필요 (OptionList는 항목 텍스트의 직접 수정을 지원하지 않으므로 항목 교체 필요)

    def action_edit(self) -> None:
        edit_input = self.query_one("#edit-input", Input)
        edit_input.display = True
        option_list = self.query_one("#hypothesis-list", OptionList)
        if option_list.highlighted is not None:
            idx = option_list.highlighted
            edit_input.value = self.hypotheses[idx].text
            edit_input.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-btn":
            self.action_confirm()
        elif event.button.id == "cancel-btn":
            self.action_cancel()
        elif event.button.id == "add-btn":
            new_h = Hypothesis(id=f"custom_{len(self.hypotheses)}", text="새로운 가설 입력...")
            self.hypotheses.append(new_h)
            # 리스트 갱신 로직 필요
```

#### Task 9.2: 제약 조건 입력 워크플로우
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/orchestrator/screens/constraint_screen.py` (신규)

**구현 태스크:**

| ID | 태스크 | 수용 기준 |
|----|------|---------------------|
| 9.2.1 | `ConstraintScreen` 모달 생성 | 날짜 범위, 지역, 카테고리 필터 입력 필드 제공 |
| 9.2.2 | 날짜 범위 피커 | YYYY-MM-DD 형식의 시작/종료일 입력 및 검증 |
| 9.2.3 | 다중 선택 범주형 제약 | 지역, 카테고리 등을 체크박스로 선택 |
| 9.2.4 | 자유 텍스트 제약 조건 | 사용자가 직접 추가적인 제약 조건을 입력 |

#### Task 9.3: 승인 단축키 시스템
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/orchestrator/bi_agent_console.py`

**구현 태스크:**

| ID | 태스크 | 수용 기준 |
|----|------|---------------------|
| 9.3.1 | 승인용 키보드 단축키 추가 | `Y` = 승인, `N` = 거절, `E` = 편집 |
| 9.3.2 | 빠른 승인 모드 | Shift+Y 입력 시 확인 대화 상자 건너뛰기 |
| 9.3.3 | 일괄 승인 기능 | 여러 항목을 선택하고 한 번에 승인 |
| 9.3.4 | 승인 감사 로그 | 모든 승인 결정을 타임스탬프와 함께 저장 |

---

## 5. Phase 4: Report Assembly (Steps 10-12)

### Step 10: Optimal Query Generation (최적 쿼리 생성)

**목표:** 가설 검증을 위한 SQL 자동 생성 및 자가 치유(Self-healing) 오류 수정.

#### Task 10.1: 향상된 SQL 생성기
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/data_source/sql_generator.py`

**구현 태스크:**

| ID | 태스크 | 수용 기준 |
|----|------|---------------------|
| 10.1.1 | DB Dialect 검증 추가 | 대상 DB(SQLite, Postgres, MySQL)에 맞는 문법 확인 |
| 10.1.2 | 컬럼 존재 여부 검증 | 스키마를 확인하여 참조된 모든 컬럼이 존재하는지 확인 |
| 10.1.3 | 쿼리 비용 추정 | 대량 데이터 스캔(예: 10만 행 이상) 시 경고 발생 |
| 10.1.4 | 쿼리 설명 생성 | 쿼리가 수행하는 작업을 사용자에게 안내하는 한국어 설명 생성 |

#### Task 10.2: 자가 치유 쿼리 루프
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/data_source/query_healer.py` (신규)

**구현 태스크:**

| ID | 태스크 | 수용 기준 |
|----|------|---------------------|
| 10.2.1 | 실행 오류 캡처 | DB에서 반환된 에러 메시지 파싱 |
| 10.2.2 | LLM 기반 에러 분석 및 수정 | "salse 컬럼 없음 -> sales를 의도하셨나요?" 등의 수정 제안 |
| 10.2.3 | 자동 수정 및 재시도 | 최대 3회까지 재시도 수행 |
| 10.2.4 | 모든 치유 시도 로그 저장 | `logs/query_healing.jsonl`에 저장 |

**SQL 치유를 위한 LLM 프롬프트 템플릿:**
```python
SQL_HEALING_PROMPT = """당신은 SQL 디버깅 전문가입니다. 다음 SQL 에러를 분석하고 수정안을 제시하십시오.

**원본 SQL:**
```sql
{original_sql}
```

**에러 메시지:**
{error_message}

**데이터베이스 스키마:**
{schema_json}

**데이터베이스 타입:** {db_type}

**과업:**
1. 에러 원인 식별
2. 스키마와 컬럼명 대조 (오타인 경우 가장 유사한 컬럼 제안)
3. 해당 DB 타입의 문법에 맞는지 확인
4. 수정된 SQL 쿼리 제공

반환 형식 (JSON):
{{
    "error_type": "column_not_found|table_not_found|syntax_error|ambiguous_column|other",
    "diagnosis_ko": "에러 원인 설명 (한국어)",
    "suggested_fix_ko": "수정 제안 (한국어)",
    "corrected_sql": "SELECT ... (수정된 SQL)",
    "confidence": 0.95
}}

JSON만 반환하십시오."""
```

#### Task 10.3: Pandas 변환 생성기
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/data_source/pandas_generator.py` (신규)

| ID | 태스크 | 수용 기준 |
|----|------|---------------------|
| 10.3.1 | 복잡한 연산을 위한 Pandas 코드 생성 | SQL로 표현하기 힘든 변환 작업 시 활용 |
| 10.3.2 | LLM 기반 파이썬 코드 생성 | pandas, numpy만 포함하는 안전한 서브셋 코드 생성 |
| 10.3.3 | 샌드박스 실행 | 제한된 환경에서 파이썬 코드 실행 |

---

### Step 11: Layout Design (레이아웃 디자인)

**목표:** 차트 자동 추천, 프리미엄 테마 적용 및 최적 레이아웃 계산.

#### Task 11.1: 차트 추천 엔진
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/chart_recommender.py` (신규)

| ID | 태스크 | 수용 기준 |
|----|------|---------------------|
| 11.1.1 | 데이터 특성 감지 | 시계열, 분포, 상관관계, 비교 데이터 식별 |
| 11.1.2 | 특성별 차트 타입 매핑 | 시계열 -> Line, 분포 -> Histogram 등 |
| 11.1.3 | 추천 순위 지정 | 근거와 함께 상위 3개 차트 타입 제안 |

#### Task 11.2: 프리미엄 테마 엔진 강화
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/theme_engine.py`

| ID | 태스크 | 수용 기준 |
|----|------|---------------------|
| 11.2.1 | 3개 이상의 테마 팔레트 추가 | "executive_blue", "nature_green", "sunset_warm" |
| 11.2.2 | 폰트 메타데이터 주입 | 폰트 패밀리, 크기 스케일, 굵기 매핑 |

#### Task 11.3: 자동 레이아웃 계산기
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/layout_calculator.py` (신규)

| ID | 태스크 | 수용 기준 |
|----|------|---------------------|
| 11.3.1 | 그리드 위치 계산 | N개의 컴포넌트를 12컬럼 그리드에 배치 |
| 11.3.2 | 우선순위 기반 크기 조정 | KPI는 2컬럼, 메인 차트는 8-12컬럼 할당 |

---

### Step 12: Interaction Injection (인터랙션 주입)

**목표:** 필터, 드릴다운, 크로스 필터링을 위한 varList/eventList JSON 생성.

#### Task 12.1: VarList/EventList 생성기
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/interaction_logic.py`

| ID | 태스크 | 수용 기준 |
|----|------|---------------------|
| 12.1.1 | 전역 필터 변수 생성 | 날짜 범위, 카테고리 선택 등이 모든 차트와 연결됨 |
| 12.1.2 | 크로스 필터 이벤트 생성 | 한 차트의 항목 클릭 시 다른 차트들이 필터링됨 |
| 12.1.3 | 파라미터 바인딩 문법 | 쿼리 내 `{{v_date_start}}` 플레이스홀더 주입 |

#### Task 12.2: 드릴다운 로직 매핑
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/drilldown_mapper.py` (신규)

| ID | 태스크 | 수용 기준 |
|----|------|---------------------|
| 12.2.1 | 드릴다운 계층 정의 | 연도 -> 분기 -> 월 -> 일 등 |
| 12.2.2 | 데이터로부터 계층 자동 감지 | `year`, `month` 등의 컬럼을 계층으로 묶음 |

---

## 6. Phase 5: Review & Export (Steps 13-15)

### Step 13: Draft Briefing (초안 브리핑)

**목표:** 한국어 요약 생성, 로컬 웹 미리보기 및 ASCII KPI 카드 제공.

#### Task 13.1: 분석 요약 생성기
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/summary_generator.py` (신규)

| ID | 태스크 | 수용 기준 |
|----|------|---------------------|
| 13.1.1 | LLM 기반 한국어 요약문 생성 | 발견 사항을 요약한 3~5개 문단 |
| 13.1.2 | 주요 인사이트 추출 | 3~5개의 핵심 불렛 포인트 인사이트 |

#### Task 13.2: 로컬 웹 미리보기 서버
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/utils/preview_server.py` (신규)

| ID | 태스크 | 수용 기준 |
|----|------|---------------------|
| 13.2.1 | 로컬 HTTP 서버 기동 | Flask 활용 `localhost:5000` 가동 |
| 13.2.2 | 생성된 HTML 대시보드 서빙 | `/preview/{report_id}` 엔드포인트 |

#### Task 13.3: TUI 내 ASCII KPI 카드
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/orchestrator/components/ascii_kpi.py` (신규)

| ID | 태스크 | 수용 기준 |
|----|------|---------------------|
| 13.3.1 | `ASCIIKPICard` 위젯 생성 | 지표 값과 라벨을 ASCII 박스로 표시 |
| 13.3.3 | 스파크라인 시각화 | 미니 ASCII 차트(`▁▂▃▄▅▆▇█`) 표시 |

---

### Step 14: Iterative Refinement (반복적 교정)

**목표:** 실시간 수정 명령 처리 및 보고서 품질 검사.

#### Task 14.1: 교정 명령 루프
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/orchestrator/refinement_handler.py` (신규)

| ID | 태스크 | 수용 기준 |
|----|------|---------------------|
| 14.1.1 | 수정 명령 파싱 | "차트 바꿔줘" -> 차트 타입 변경 동작 수행 |

#### Task 14.2: 보고서 린팅(Linting)
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/report_linter.py` (신규)

| ID | 태스크 | 수용 기준 |
|----|------|---------------------|
| 14.2.1 | 시각적 명료성 검사 | 폰트 크기, 대비 등 가독성 확인 |
| 14.2.2 | 데이터 정확성 검사 | 참조 컬럼 존재 여부, 집계 오류 확인 |

---

### Step 15: Final Export (최종 출력 및 배포)

**목표:** 최종 JSON 구축, 검증 및 패키징.

#### Task 15.1: 최종 JSON 빌드 및 검증
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/json_validator.py` (신규)

| ID | 태스크 | 수용 기준 |
|----|------|---------------------|
| 15.1.1 | JSON 스키마 검증 | InHouse 표준 스키마 준수 여부 확인 |
| 15.1.2 | 참조 무결성 확인 | 리포트가 참조하는 모든 datamodel ID가 존재하는지 확인 |

#### Task 15.2: 출력 패키저 강화
**파일:** `/Users/zokr/python_workspace/BI-Agent/backend/utils/output_packager.py`

| ID | 태스크 | 수용 기준 |
|----|------|---------------------|
| 15.2.1 | Excel 내보내기 추가 | 데이터 테이블을 .xlsx로 저장 (`openpyxl` 사용) |
| 15.2.2 | PDF 리포트 추가 | HTML을 PDF로 변환 (`weasyprint` 사용) |

---

## 7. 공통 고려 사항 (Cross-Cutting Concerns)

- **에러 핸들링:** 구조화된 로깅 및 예외 처리 강화.
- **테스팅:** 유닛 테스트 커버리지 90% 목표.
- **성능:** 주요 동작별 응답 시간 최적화.
- **언어:** 한국어 중심의 UI/UX 및 결과물 생성.

---

## 8. 부록 (Appendix)

### 신규 파일 생성 요약:
`base_intent.py`, `analysis_intent.py`, `table_recommender.py`, `pipeline_generator.py`, `agent_message_bus.py`, `hypothesis_screen.py`, `query_healer.py` 등 총 20여 개의 신규 모듈 및 컴포넌트 추가 예정.

---

**PLAN_READY: .omc/plans/bi-agent-detailed-implementation.md**
