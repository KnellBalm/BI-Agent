# Phase 4-5 시스템 아키텍처 설계

**문서 ID:** `bi-agent-phase4-5-architecture`
**작성일:** 2026-02-11
**작성자:** Architect Agent
**대상:** Phase 4-5 구현팀 (Builder-1, Builder-2, QA-Tester)

---

## 목차

1. [Executive Summary](#executive-summary)
2. [현재 시스템 분석](#현재-시스템-분석)
3. [Phase 4-5 컴포넌트 아키텍처](#phase-4-5-컴포넌트-아키텍처)
4. [시스템 통합 패턴](#시스템-통합-패턴)
5. [인터페이스 설계](#인터페이스-설계)
6. [데이터 흐름](#데이터-흐름)
7. [기술 스택 검증](#기술-스택-검증)
8. [구현 가이드라인](#구현-가이드라인)
9. [보안 및 성능 고려사항](#보안-및-성능-고려사항)

---

## Executive Summary

Phase 4-5 구현은 BI-Agent의 **리포트 조립 및 출력** 단계로, 다음 컴포넌트들을 신규 개발합니다:

- **ChartRecommender**: 데이터 특성 기반 차트 타입 자동 추천
- **LayoutCalculator**: 그리드 기반 레이아웃 자동 계산
- **SummaryGenerator**: LLM 기반 분석 요약 및 인사이트 생성
- **PreviewServer**: Flask 기반 로컬 웹 서버
- **기존 컴포넌트 강화**: ThemeEngine, InhouseGenerator, InteractionLogic

### 아키텍처 원칙

1. **느슨한 결합 (Loose Coupling)**: 컴포넌트 간 의존성 최소화
2. **비동기 통신 (Async Messaging)**: AgentMessageBus를 통한 이벤트 기반 통신
3. **확장성 (Extensibility)**: 새로운 차트 타입/테마 추가 용이
4. **타입 안정성 (Type Safety)**: 모든 공개 API에 타입 힌팅 적용
5. **테스트 가능성 (Testability)**: 모든 컴포넌트 단위 테스트 가능

---

## 현재 시스템 분석

### 1. 기존 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────┐
│                    bi_agent_console.py                       │
│                  (Textual TUI Main App)                      │
└────────────┬────────────────────────────────────────────────┘
             │
    ┌────────┴────────┐
    │                 │
    ▼                 ▼
┌─────────┐      ┌──────────────┐
│ Screens │      │  Components  │
│ (UI)    │      │  (Widgets)   │
└─────────┘      └──────────────┘
    │                 │
    └────────┬────────┘
             ▼
    ┌────────────────┐
    │   Handlers     │
    │ (Command/Input)│
    └────────┬───────┘
             │
    ┌────────┴───────────────┬──────────────┐
    ▼                        ▼              ▼
┌─────────┐          ┌──────────────┐  ┌─────────┐
│Managers │          │ Orchestrators│  │Services │
└─────────┘          └──────────────┘  └─────────┘
    │                        │              │
    └────────────────────────┴──────────────┘
                      ▼
            ┌──────────────────────┐
            │   Agent Layer        │
            │ ┌──────────────────┐ │
            │ │ DataSourceAgent  │ │
            │ └──────────────────┘ │
            │ ┌──────────────────┐ │
            │ │   BIToolAgent    │ │
            │ └──────────────────┘ │
            └──────────────────────┘
                      ▼
            ┌──────────────────────┐
            │  AgentMessageBus     │
            │  (asyncio.Queue)     │
            └──────────────────────┘
```

### 2. 기존 컴포넌트 상태

#### 2.1 완료된 컴포넌트 (Phase 0-3)

| 컴포넌트 | 위치 | 상태 | 용도 |
|---------|------|------|------|
| `BaseIntent` | `bi_tool/base_intent.py` | ✅ 완료 | 의도 객체 추상 클래스 |
| `ChartIntent` | `bi_tool/nl_intent_parser.py` | ✅ 완료 | 차트 생성 의도 |
| `AnalysisIntent` | `bi_tool/analysis_intent.py` | ✅ 완료 | 복합 분석 의도 |
| `TableRecommender` | `data_source/table_recommender.py` | ✅ 완료 | 테이블 추천 |
| `PipelineGenerator` | `bi_tool/pipeline_generator.py` | ✅ 완료 | 분석 파이프라인 생성 |
| `QueryHealer` | `data_source/query_healer.py` | ✅ 완료 | SQL 자동 수정 |
| `AgentMessageBus` | `orchestrator/messaging/agent_message_bus.py` | ✅ 완료 | 메시지 버스 |
| `ThemeEngine` | `bi_tool/theme_engine.py` | ⚠️ 기본 구현 | 테마 관리 (확장 필요) |
| `InhouseGenerator` | `bi_tool/inhouse_generator.py` | ⚠️ 기본 구현 | JSON 생성 (확장 필요) |
| `InteractionLogic` | `bi_tool/interaction_logic.py` | ⚠️ 기본 구현 | 인터랙션 로직 (확장 필요) |

#### 2.2 통신 패턴

현재 시스템은 두 가지 통신 패턴을 사용합니다:

1. **동기 호출 (Synchronous)**
   - TUI → Handler → Manager/Service → Agent
   - 단순한 데이터 조회/설정

2. **비동기 메시징 (Asynchronous)**
   - Agent → AgentMessageBus → TUI
   - 장시간 실행 작업의 진행 상황 알림
   - 에이전트 간 데이터 교환

---

## Phase 4-5 컴포넌트 아키텍처

### 1. 전체 시스템 다이어그램 (Phase 4-5 포함)

```
                    ┌─────────────────────────┐
                    │   bi_agent_console.py   │
                    │      (Textual TUI)      │
                    └───────────┬─────────────┘
                                │
                    ┌───────────┴────────────┐
                    │                        │
         ┌──────────▼──────────┐  ┌─────────▼──────────┐
         │  CommandHandler     │  │  QuestionFlowEngine│
         │  (명령어 라우팅)     │  │  (대화형 플로우)    │
         └─────────┬───────────┘  └─────────┬──────────┘
                   │                        │
         ┌─────────▼────────────────────────▼──────────┐
         │                                              │
    ┌────▼────────┐                         ┌──────────▼────┐
    │ Step 11     │                         │ Step 13       │
    │ Layout      │                         │ Briefing      │
    │ Design      │                         │ & Preview     │
    └─────┬───────┘                         └───────┬───────┘
          │                                         │
    ┌─────▼──────────────────────────────────┬─────▼───────┐
    │                                        │             │
┌───▼────────────┐  ┌──────────────────┐  ┌─▼───────────────┐
│ChartRecommender│  │LayoutCalculator  │  │SummaryGenerator │
│(NEW)           │  │(NEW)             │  │(NEW)            │
└───┬────────────┘  └──────┬───────────┘  └─┬───────────────┘
    │                      │                 │
    │    ┌─────────────────▼─────────────────┤
    │    │                                   │
┌───▼────▼────────┐  ┌──────────────────┐  ┌▼────────────────┐
│ ThemeEngine     │  │InteractionLogic  │  │PreviewServer    │
│(ENHANCED)       │  │(ENHANCED)        │  │(NEW)            │
└───┬─────────────┘  └────┬─────────────┘  └─┬───────────────┘
    │                     │                   │
    └─────────┬───────────┴───────────────────┘
              │
    ┌─────────▼──────────┐
    │ InhouseGenerator   │
    │ (ENHANCED)         │
    │ Final JSON Builder │
    └─────────┬──────────┘
              │
    ┌─────────▼──────────┐
    │   Output Files     │
    │ • suwon_pop.json   │
    │ • HTML Dashboard   │
    │ • Excel/PDF (opt)  │
    └────────────────────┘
```

### 2. 신규 컴포넌트 상세 설계

#### 2.1 ChartRecommender

**목적**: 데이터 특성(시계열, 분포, 상관관계 등)을 분석하여 최적의 차트 타입을 추천

**위치**: `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/chart_recommender.py`

**클래스 설계**:

```python
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum
import pandas as pd

class DataCharacteristic(Enum):
    """데이터 특성 분류"""
    TIMESERIES = "timeseries"
    DISTRIBUTION = "distribution"
    COMPARISON = "comparison"
    CORRELATION = "correlation"
    COMPOSITION = "composition"
    GEOGRAPHIC = "geographic"

class ChartType(Enum):
    """지원 차트 타입"""
    LINE = "line"
    BAR = "bar"
    COLUMN = "column"
    PIE = "pie"
    SCATTER = "scatter"
    HEATMAP = "heatmap"
    AREA = "area"
    TABLE = "table"

@dataclass
class ChartRecommendation:
    """차트 추천 결과"""
    chart_type: ChartType
    score: float  # 0-1 범위
    reasoning: str  # 한국어 근거
    dimensions: List[str]
    measures: List[str]
    alternative_charts: List['ChartRecommendation']

class ChartRecommender:
    """데이터 특성 기반 차트 추천 엔진"""

    def __init__(self, llm_provider=None):
        self.llm = llm_provider
        self._rules = self._initialize_rules()

    def _initialize_rules(self) -> Dict[DataCharacteristic, List[ChartType]]:
        """규칙 기반 매핑 초기화"""
        return {
            DataCharacteristic.TIMESERIES: [
                ChartType.LINE, ChartType.AREA, ChartType.COLUMN
            ],
            DataCharacteristic.DISTRIBUTION: [
                ChartType.COLUMN, ChartType.BAR, ChartType.PIE
            ],
            DataCharacteristic.COMPARISON: [
                ChartType.BAR, ChartType.COLUMN, ChartType.TABLE
            ],
            DataCharacteristic.CORRELATION: [
                ChartType.SCATTER, ChartType.HEATMAP
            ],
            DataCharacteristic.COMPOSITION: [
                ChartType.PIE, ChartType.AREA
            ]
        }

    def detect_characteristics(
        self,
        df: pd.DataFrame,
        dimensions: List[str],
        measures: List[str]
    ) -> List[DataCharacteristic]:
        """데이터 특성 자동 감지"""
        characteristics = []

        # 시계열 감지
        for dim in dimensions:
            if self._is_datetime(df[dim]):
                characteristics.append(DataCharacteristic.TIMESERIES)
                break

        # 분포 감지 (단일 범주형 차원)
        if len(dimensions) == 1 and len(measures) >= 1:
            if df[dimensions[0]].dtype == 'object':
                characteristics.append(DataCharacteristic.DISTRIBUTION)

        # 비교 감지 (여러 범주)
        if len(dimensions) >= 1 and len(measures) >= 1:
            characteristics.append(DataCharacteristic.COMPARISON)

        # 상관관계 감지 (2개 이상 수치형 지표)
        if len(measures) >= 2:
            characteristics.append(DataCharacteristic.CORRELATION)

        return characteristics

    def recommend(
        self,
        df: pd.DataFrame,
        dimensions: List[str],
        measures: List[str],
        intent: Optional[Any] = None
    ) -> List[ChartRecommendation]:
        """
        차트 타입 추천 (규칙 + LLM 기반)

        Returns:
            상위 3개 추천 차트, 점수 순으로 정렬
        """
        characteristics = self.detect_characteristics(df, dimensions, measures)
        recommendations = []

        # 규칙 기반 추천
        for char in characteristics:
            for chart_type in self._rules.get(char, []):
                score = self._calculate_score(
                    chart_type, char, df, dimensions, measures
                )
                recommendations.append(ChartRecommendation(
                    chart_type=chart_type,
                    score=score,
                    reasoning=self._generate_reasoning(chart_type, char),
                    dimensions=dimensions,
                    measures=measures,
                    alternative_charts=[]
                ))

        # LLM 기반 추천 (선택적)
        if self.llm and intent:
            llm_rec = self._llm_recommend(df, dimensions, measures, intent)
            recommendations.extend(llm_rec)

        # 중복 제거 및 점수순 정렬
        recommendations = self._deduplicate_and_sort(recommendations)

        # 대안 차트 설정
        for i, rec in enumerate(recommendations[:3]):
            rec.alternative_charts = recommendations[i+1:i+3]

        return recommendations[:3]

    def _is_datetime(self, series: pd.Series) -> bool:
        """시계열 컬럼 감지"""
        return pd.api.types.is_datetime64_any_dtype(series)

    def _calculate_score(
        self,
        chart_type: ChartType,
        characteristic: DataCharacteristic,
        df: pd.DataFrame,
        dimensions: List[str],
        measures: List[str]
    ) -> float:
        """규칙 기반 점수 계산"""
        base_score = 0.7

        # 데이터 크기 고려
        row_count = len(df)
        if chart_type == ChartType.PIE and row_count > 10:
            base_score -= 0.2  # 파이 차트는 카테고리가 많으면 부적합

        # 차원/지표 수 고려
        if chart_type == ChartType.SCATTER and len(measures) >= 2:
            base_score += 0.2

        if chart_type == ChartType.LINE and characteristic == DataCharacteristic.TIMESERIES:
            base_score += 0.3

        return min(1.0, base_score)

    def _generate_reasoning(
        self,
        chart_type: ChartType,
        characteristic: DataCharacteristic
    ) -> str:
        """추천 근거 생성 (한국어)"""
        reasons = {
            (ChartType.LINE, DataCharacteristic.TIMESERIES):
                "시계열 데이터의 추이를 명확하게 표현하기에 적합합니다.",
            (ChartType.BAR, DataCharacteristic.COMPARISON):
                "여러 항목 간 비교를 직관적으로 보여줍니다.",
            (ChartType.SCATTER, DataCharacteristic.CORRELATION):
                "두 변수 간 상관관계를 시각적으로 확인할 수 있습니다.",
        }
        return reasons.get((chart_type, characteristic),
                          f"{chart_type.value} 차트가 적합합니다.")

    def _llm_recommend(
        self,
        df: pd.DataFrame,
        dimensions: List[str],
        measures: List[str],
        intent: Any
    ) -> List[ChartRecommendation]:
        """LLM 기반 추천 (향후 구현)"""
        # TODO: LLM 프롬프트를 통한 고급 추천
        return []

    def _deduplicate_and_sort(
        self,
        recommendations: List[ChartRecommendation]
    ) -> List[ChartRecommendation]:
        """중복 제거 및 점수순 정렬"""
        seen = {}
        for rec in recommendations:
            if rec.chart_type not in seen or seen[rec.chart_type].score < rec.score:
                seen[rec.chart_type] = rec
        return sorted(seen.values(), key=lambda x: x.score, reverse=True)
```

**의존성**:
- `pandas`: 데이터 분석
- `LLMProvider`: 선택적, 고급 추천에 사용

---

#### 2.2 LayoutCalculator

**목적**: 차트/컴포넌트를 12컬럼 그리드에 최적 배치

**위치**: `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/layout_calculator.py`

**클래스 설계**:

```python
from dataclasses import dataclass
from typing import List, Dict, Any
from enum import Enum

class ComponentPriority(Enum):
    """컴포넌트 우선순위"""
    CRITICAL = 3  # KPI, 핵심 지표
    HIGH = 2      # 메인 차트
    MEDIUM = 1    # 보조 차트
    LOW = 0       # 부가 정보

@dataclass
class LayoutComponent:
    """레이아웃 컴포넌트"""
    id: str
    type: str  # "chart", "kpi", "filter", "label"
    priority: ComponentPriority
    min_width: int = 2  # 최소 컬럼 수
    preferred_width: int = 6  # 선호 컬럼 수
    height: int = 4  # 높이 (단위)

@dataclass
class GridPosition:
    """그리드 상의 위치"""
    x: int  # 컬럼 시작 위치 (0-11)
    y: int  # 행 위치
    width: int  # 컬럼 수
    height: int  # 높이

class LayoutCalculator:
    """그리드 기반 레이아웃 자동 계산기"""

    GRID_COLUMNS = 12

    def __init__(self):
        self.grid: List[List[bool]] = []  # 사용 여부 추적

    def calculate_layout(
        self,
        components: List[LayoutComponent]
    ) -> Dict[str, GridPosition]:
        """
        컴포넌트들의 최적 레이아웃 계산

        알고리즘:
        1. 우선순위 순으로 정렬
        2. 각 컴포넌트를 사용 가능한 첫 위치에 배치
        3. 선호 너비를 최대한 보장
        """
        # 우선순위 정렬
        sorted_components = sorted(
            components,
            key=lambda c: c.priority.value,
            reverse=True
        )

        # 그리드 초기화
        max_height = sum(c.height for c in components)
        self.grid = [[False] * self.GRID_COLUMNS for _ in range(max_height)]

        layout = {}

        for comp in sorted_components:
            position = self._find_best_position(comp)
            layout[comp.id] = position
            self._mark_occupied(position)

        return layout

    def _find_best_position(self, comp: LayoutComponent) -> GridPosition:
        """컴포넌트를 배치할 최적 위치 찾기"""
        for y in range(len(self.grid)):
            for x in range(self.GRID_COLUMNS):
                # 선호 너비로 시도
                if self._can_place(x, y, comp.preferred_width, comp.height):
                    return GridPosition(x, y, comp.preferred_width, comp.height)

                # 최소 너비로 시도
                if self._can_place(x, y, comp.min_width, comp.height):
                    return GridPosition(x, y, comp.min_width, comp.height)

        # 공간이 없으면 새 행 추가
        new_y = len(self.grid)
        self.grid.extend([[False] * self.GRID_COLUMNS for _ in range(comp.height)])
        return GridPosition(0, new_y, comp.preferred_width, comp.height)

    def _can_place(self, x: int, y: int, width: int, height: int) -> bool:
        """지정 위치에 배치 가능한지 확인"""
        if x + width > self.GRID_COLUMNS:
            return False
        if y + height > len(self.grid):
            return False

        for dy in range(height):
            for dx in range(width):
                if self.grid[y + dy][x + dx]:
                    return False
        return True

    def _mark_occupied(self, position: GridPosition):
        """그리드 영역을 사용 중으로 표시"""
        for dy in range(position.height):
            for dx in range(position.width):
                self.grid[position.y + dy][position.x + dx] = True

    def to_css_grid(self, layout: Dict[str, GridPosition]) -> Dict[str, str]:
        """CSS Grid 스타일 생성"""
        styles = {}
        for comp_id, pos in layout.items():
            styles[comp_id] = (
                f"grid-column: {pos.x + 1} / span {pos.width}; "
                f"grid-row: {pos.y + 1} / span {pos.height};"
            )
        return styles

    def to_inhouse_layout(
        self,
        layout: Dict[str, GridPosition]
    ) -> List[Dict[str, Any]]:
        """InHouse JSON 레이아웃 형식으로 변환"""
        result = []
        for comp_id, pos in layout.items():
            result.append({
                "componentId": comp_id,
                "x": pos.x,
                "y": pos.y,
                "width": pos.width,
                "height": pos.height
            })
        return result
```

**의존성**: 없음 (순수 Python)

---

#### 2.3 SummaryGenerator

**목적**: LLM을 활용하여 분석 결과 요약 및 인사이트 추출

**위치**: `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/summary_generator.py`

**클래스 설계**:

```python
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import pandas as pd

@dataclass
class AnalysisSummary:
    """분석 요약 결과"""
    title: str
    overview: str  # 3-5 문단 요약
    key_insights: List[str]  # 3-5개 핵심 인사이트
    recommendations: List[str]  # 권고사항
    confidence_level: str  # "HIGH", "MEDIUM", "LOW"

class SummaryGenerator:
    """LLM 기반 분석 요약 생성기"""

    SUMMARY_PROMPT_TEMPLATE = """
당신은 데이터 분석 전문가입니다. 다음 분석 결과를 바탕으로 경영진이 이해하기 쉬운 요약 보고서를 작성하세요.

**분석 의도:**
{intent_summary}

**데이터 요약:**
{data_summary}

**생성된 차트:**
{chart_list}

**통계 정보:**
{statistics}

**요구사항:**
1. **개요 (Overview)**: 3-5 문단으로 분석 목적, 방법, 주요 발견사항을 요약
2. **핵심 인사이트 (Key Insights)**: 3-5개의 중요한 발견사항을 불렛 포인트로 제시
3. **권고사항 (Recommendations)**: 인사이트를 바탕으로 한 구체적 액션 아이템 3개

**응답 형식 (JSON):**
{{
    "title": "분석 제목",
    "overview": "개요 문단...",
    "key_insights": ["인사이트 1", "인사이트 2", ...],
    "recommendations": ["권고사항 1", "권고사항 2", ...],
    "confidence_level": "HIGH|MEDIUM|LOW"
}}

JSON만 반환하세요.
"""

    def __init__(self, llm_provider):
        self.llm = llm_provider

    async def generate_summary(
        self,
        intent: Any,
        dataframes: Dict[str, pd.DataFrame],
        charts: List[Dict[str, Any]],
        statistics: Dict[str, Any]
    ) -> AnalysisSummary:
        """
        분석 결과 요약 생성

        Args:
            intent: AnalysisIntent 객체
            dataframes: 분석에 사용된 데이터프레임들
            charts: 생성된 차트 정보
            statistics: 통계 정보

        Returns:
            AnalysisSummary 객체
        """
        # 프롬프트 준비
        prompt = self._prepare_prompt(intent, dataframes, charts, statistics)

        # LLM 호출
        response = await self.llm.generate(prompt)

        # 응답 파싱
        summary = self._parse_response(response)

        return summary

    def _prepare_prompt(
        self,
        intent: Any,
        dataframes: Dict[str, pd.DataFrame],
        charts: List[Dict[str, Any]],
        statistics: Dict[str, Any]
    ) -> str:
        """프롬프트 준비"""
        intent_summary = f"목적: {intent.purpose}, 지표: {intent.target_metrics}"

        data_summary = self._summarize_dataframes(dataframes)
        chart_list = self._format_chart_list(charts)
        stats_text = self._format_statistics(statistics)

        return self.SUMMARY_PROMPT_TEMPLATE.format(
            intent_summary=intent_summary,
            data_summary=data_summary,
            chart_list=chart_list,
            statistics=stats_text
        )

    def _summarize_dataframes(
        self,
        dataframes: Dict[str, pd.DataFrame]
    ) -> str:
        """데이터프레임 요약"""
        summaries = []
        for name, df in dataframes.items():
            summaries.append(
                f"- {name}: {len(df)} 행, {len(df.columns)} 컬럼"
            )
        return "\n".join(summaries)

    def _format_chart_list(self, charts: List[Dict[str, Any]]) -> str:
        """차트 목록 포맷"""
        chart_texts = []
        for i, chart in enumerate(charts, 1):
            chart_texts.append(
                f"{i}. {chart.get('type', 'Unknown')} - "
                f"{chart.get('title', 'Untitled')}"
            )
        return "\n".join(chart_texts)

    def _format_statistics(self, statistics: Dict[str, Any]) -> str:
        """통계 정보 포맷"""
        stats_text = []
        for key, value in statistics.items():
            stats_text.append(f"- {key}: {value}")
        return "\n".join(stats_text)

    def _parse_response(self, response: str) -> AnalysisSummary:
        """LLM 응답 파싱"""
        import json

        try:
            # JSON 추출
            clean_response = response.strip()
            if "{" in clean_response:
                start = clean_response.find("{")
                end = clean_response.rfind("}") + 1
                clean_response = clean_response[start:end]

            data = json.loads(clean_response)

            return AnalysisSummary(
                title=data.get("title", "분석 요약"),
                overview=data.get("overview", ""),
                key_insights=data.get("key_insights", []),
                recommendations=data.get("recommendations", []),
                confidence_level=data.get("confidence_level", "MEDIUM")
            )
        except json.JSONDecodeError as e:
            # 파싱 실패 시 기본 요약 반환
            return AnalysisSummary(
                title="분석 요약",
                overview="요약 생성 중 오류가 발생했습니다.",
                key_insights=[],
                recommendations=[],
                confidence_level="LOW"
            )
```

**의존성**:
- `LLMProvider`: LLM 호출
- `pandas`: 데이터 요약

---

#### 2.4 PreviewServer

**목적**: 로컬 웹 서버를 통한 대시보드 미리보기

**위치**: `/Users/zokr/python_workspace/BI-Agent/backend/utils/preview_server.py`

**클래스 설계**:

```python
from flask import Flask, render_template_string, jsonify, send_from_directory
from pathlib import Path
from typing import Dict, Any, Optional
import threading
import logging

logger = logging.getLogger(__name__)

class PreviewServer:
    """로컬 Flask 기반 대시보드 미리보기 서버"""

    DEFAULT_PORT = 5555
    TEMPLATE_DIR = Path(__file__).parent / "templates"

    def __init__(self, port: int = DEFAULT_PORT):
        self.port = port
        self.app = Flask(__name__)
        self.server_thread: Optional[threading.Thread] = None
        self.dashboard_cache: Dict[str, Dict[str, Any]] = {}

        self._setup_routes()

    def _setup_routes(self):
        """라우트 설정"""

        @self.app.route("/")
        def index():
            """서버 상태 확인"""
            return jsonify({
                "status": "running",
                "available_dashboards": list(self.dashboard_cache.keys())
            })

        @self.app.route("/preview/<dashboard_id>")
        def preview(dashboard_id: str):
            """대시보드 미리보기"""
            if dashboard_id not in self.dashboard_cache:
                return jsonify({"error": "Dashboard not found"}), 404

            dashboard_data = self.dashboard_cache[dashboard_id]
            return render_template_string(
                self._generate_html_template(dashboard_data)
            )

        @self.app.route("/api/dashboard/<dashboard_id>")
        def get_dashboard_data(dashboard_id: str):
            """대시보드 데이터 API"""
            if dashboard_id not in self.dashboard_cache:
                return jsonify({"error": "Dashboard not found"}), 404
            return jsonify(self.dashboard_cache[dashboard_id])

    def register_dashboard(
        self,
        dashboard_id: str,
        dashboard_data: Dict[str, Any]
    ):
        """대시보드 등록"""
        self.dashboard_cache[dashboard_id] = dashboard_data
        logger.info(f"Dashboard registered: {dashboard_id}")

    def start(self, background: bool = True):
        """서버 시작"""
        if background:
            self.server_thread = threading.Thread(
                target=self._run_server,
                daemon=True
            )
            self.server_thread.start()
            logger.info(f"Preview server started at http://localhost:{self.port}")
        else:
            self._run_server()

    def _run_server(self):
        """Flask 서버 실행"""
        self.app.run(
            host="127.0.0.1",
            port=self.port,
            debug=False,
            use_reloader=False
        )

    def stop(self):
        """서버 중지"""
        # Flask 서버는 백그라운드 스레드로 실행되므로
        # 프로세스 종료 시 자동으로 정리됨
        logger.info("Preview server stopped")

    def get_preview_url(self, dashboard_id: str) -> str:
        """미리보기 URL 반환"""
        return f"http://localhost:{self.port}/preview/{dashboard_id}"

    def _generate_html_template(self, dashboard_data: Dict[str, Any]) -> str:
        """HTML 템플릿 생성"""
        return """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ dashboard_data.get('title', 'BI Dashboard') }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', 'Roboto', sans-serif;
            background: #0F172A;
            color: #F8FAFC;
            padding: 20px;
        }
        .dashboard-header {
            margin-bottom: 30px;
            text-align: center;
        }
        .dashboard-title {
            font-size: 32px;
            font-weight: bold;
            color: #38BDF8;
        }
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(12, 1fr);
            gap: 20px;
            max-width: 1400px;
            margin: 0 auto;
        }
        .dashboard-component {
            background: #1E293B;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }
        .component-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 15px;
            color: #38BDF8;
        }
        .chart-placeholder {
            background: #0F172A;
            border: 2px dashed #475569;
            border-radius: 4px;
            padding: 40px;
            text-align: center;
            color: #94A3B8;
        }
    </style>
</head>
<body>
    <div class="dashboard-header">
        <h1 class="dashboard-title">{{ dashboard_data.get('title', 'BI Dashboard') }}</h1>
        <p style="color: #94A3B8; margin-top: 10px;">
            Generated by BI-Agent | Preview Mode
        </p>
    </div>

    <div class="dashboard-grid">
        {% for component in dashboard_data.get('components', []) %}
        <div class="dashboard-component" style="
            grid-column: {{ component.x + 1 }} / span {{ component.width }};
            grid-row: {{ component.y + 1 }} / span {{ component.height }};
        ">
            <div class="component-title">{{ component.title }}</div>
            <div class="chart-placeholder">
                {{ component.type }} Chart
                <br><small>{{ component.description }}</small>
            </div>
        </div>
        {% endfor %}
    </div>

    <script>
        // 향후 실제 차트 라이브러리 (Chart.js, ECharts 등) 연동
        console.log('Dashboard loaded:', {{ dashboard_data | tojson }});
    </script>
</body>
</html>
"""
```

**의존성**:
- `Flask`: 웹 서버

---

### 3. 기존 컴포넌트 강화

#### 3.1 ThemeEngine 확장

**현재 상태**: 2개 팔레트 (premium_dark, corporate_light)

**확장 계획**:
- 3개 추가 테마: `executive_blue`, `nature_green`, `sunset_warm`
- 폰트 메타데이터 주입
- 컴포넌트별 세밀한 스타일 제어

```python
# theme_engine.py 추가 사항

PALETTES = {
    # ... 기존 팔레트 ...
    "executive_blue": {
        "background": "#0A1929",
        "card_bg": "#132F4C",
        "primary": "#3399FF",
        "secondary": "#66B2FF",
        "accent": "#FFB400",
        "text": "#FFFFFF",
        "subtext": "#B2BAC2",
        "chart_colors": ["#3399FF", "#66B2FF", "#FFB400", "#FF6B6B", "#4ECDC4"]
    },
    "nature_green": {
        "background": "#1A2E1A",
        "card_bg": "#2D4A2D",
        "primary": "#5CBF5C",
        "secondary": "#8DD98D",
        "accent": "#FFD700",
        "text": "#F0FFF0",
        "subtext": "#A8D5A8",
        "chart_colors": ["#5CBF5C", "#8DD98D", "#FFD700", "#FF8C42", "#6A994E"]
    },
    "sunset_warm": {
        "background": "#2A1810",
        "card_bg": "#3D2718",
        "primary": "#FF6B35",
        "secondary": "#F7931E",
        "accent": "#FDC830",
        "text": "#FFF8F0",
        "subtext": "#D4A574",
        "chart_colors": ["#FF6B35", "#F7931E", "#FDC830", "#C1666B", "#E07A5F"]
    }
}

FONT_METADATA = {
    "title": {
        "family": "Inter, sans-serif",
        "size": 24,
        "weight": 700
    },
    "subtitle": {
        "family": "Inter, sans-serif",
        "size": 18,
        "weight": 600
    },
    "body": {
        "family": "Roboto, sans-serif",
        "size": 14,
        "weight": 400
    },
    "caption": {
        "family": "Roboto, sans-serif",
        "size": 12,
        "weight": 300
    }
}
```

#### 3.2 InteractionLogic 강화

**현재 상태**: 기본 인터랙션 로직

**확장 계획**:
- `varList` 자동 생성
- `eventList` 크로스 필터링 로직
- 파라미터 바인딩

```python
# interaction_logic.py 메서드 추가

def generate_var_list(
    self,
    filters: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """전역 필터 변수 생성"""
    var_list = []

    for i, filter_def in enumerate(filters):
        var_list.append({
            "id": f"var_{filter_def['field']}",
            "name": filter_def['field'],
            "type": "parameter",
            "value": filter_def.get('default', ''),
            "dataType": self._infer_data_type(filter_def)
        })

    return var_list

def generate_event_list(
    self,
    components: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """크로스 필터링 이벤트 생성"""
    event_list = []

    # 모든 차트 간 크로스 필터링 설정
    chart_components = [c for c in components if c['type'] in ['bar', 'line', 'pie']]

    for i, source in enumerate(chart_components):
        for target in chart_components[i+1:]:
            event_list.append({
                "eventType": "commonDataReceived",
                "fromId": source['id'],
                "toId": target['id'],
                "action": "filter",
                "parameter": "selected_category"
            })

    return event_list
```

---

## 시스템 통합 패턴

### 1. 컴포넌트 간 통신

```
┌─────────────────┐
│  TUI (Console)  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│    CommandHandler               │
│  • /visualize 명령 처리         │
│  • Step 11-13 오케스트레이션    │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  VisualizationOrchestrator      │
│  (신규, orchestrators/ 내)      │
│                                 │
│  async def orchestrate():       │
│    1. ChartRecommender 호출     │
│    2. LayoutCalculator 호출     │
│    3. ThemeEngine 적용          │
│    4. SummaryGenerator 호출     │
│    5. InhouseGenerator 빌드     │
│    6. PreviewServer 등록        │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│    AgentMessageBus              │
│  • 진행 상황 브로드캐스트       │
│  • TUI ThinkingPanel 업데이트   │
└─────────────────────────────────┘
```

### 2. 데이터 흐름

```
Step 10: Query Execution
         │
         ▼
    [DataFrames]
         │
         ├──────────────────┬──────────────────┐
         │                  │                  │
         ▼                  ▼                  ▼
  ChartRecommender   SummaryGenerator   LayoutCalculator
         │                  │                  │
         └──────────┬───────┴──────────────────┘
                    │
                    ▼
            [Chart Definitions]
            [Layout Positions]
            [Summary Text]
                    │
                    ▼
            ThemeEngine.apply()
                    │
                    ▼
        InhouseGenerator.build_report()
                    │
                    ▼
            [suwon_pop.json]
                    │
                    ├──────────────┬──────────────┐
                    ▼              ▼              ▼
              File System    PreviewServer   Return to TUI
```

### 3. 에러 핸들링 전략

모든 컴포넌트는 다음 에러 핸들링 패턴을 따릅니다:

```python
from typing import Union, TypeVar, Generic
from dataclasses import dataclass

T = TypeVar('T')

@dataclass
class Success(Generic[T]):
    """성공 결과"""
    value: T

@dataclass
class Failure:
    """실패 결과"""
    error: str
    error_type: str
    recovery_suggestion: str

Result = Union[Success[T], Failure]

# 사용 예시
def recommend_chart(...) -> Result[List[ChartRecommendation]]:
    try:
        recommendations = # ... 로직 ...
        return Success(recommendations)
    except Exception as e:
        return Failure(
            error=str(e),
            error_type="RECOMMENDATION_ERROR",
            recovery_suggestion="기본 Bar 차트를 사용하세요."
        )
```

---

## 인터페이스 설계

### 1. 공개 API

각 컴포넌트는 다음과 같은 공개 API를 제공합니다:

#### ChartRecommender

```python
class ChartRecommender:
    def recommend(
        self,
        df: pd.DataFrame,
        dimensions: List[str],
        measures: List[str],
        intent: Optional[AnalysisIntent] = None
    ) -> List[ChartRecommendation]:
        """차트 추천 (최대 3개 반환)"""
        pass

    def detect_characteristics(
        self,
        df: pd.DataFrame,
        dimensions: List[str],
        measures: List[str]
    ) -> List[DataCharacteristic]:
        """데이터 특성 감지"""
        pass
```

#### LayoutCalculator

```python
class LayoutCalculator:
    def calculate_layout(
        self,
        components: List[LayoutComponent]
    ) -> Dict[str, GridPosition]:
        """레이아웃 계산"""
        pass

    def to_inhouse_layout(
        self,
        layout: Dict[str, GridPosition]
    ) -> List[Dict[str, Any]]:
        """InHouse 형식으로 변환"""
        pass
```

#### SummaryGenerator

```python
class SummaryGenerator:
    async def generate_summary(
        self,
        intent: AnalysisIntent,
        dataframes: Dict[str, pd.DataFrame],
        charts: List[Dict[str, Any]],
        statistics: Dict[str, Any]
    ) -> AnalysisSummary:
        """분석 요약 생성"""
        pass
```

#### PreviewServer

```python
class PreviewServer:
    def register_dashboard(
        self,
        dashboard_id: str,
        dashboard_data: Dict[str, Any]
    ):
        """대시보드 등록"""
        pass

    def start(self, background: bool = True):
        """서버 시작"""
        pass

    def get_preview_url(self, dashboard_id: str) -> str:
        """미리보기 URL"""
        pass
```

### 2. 내부 API

컴포넌트 내부에서만 사용되는 private 메서드는 `_` prefix를 사용합니다.

---

## 데이터 흐름

### 1. Phase 4-5 전체 흐름

```
[사용자] /visualize 명령
    │
    ▼
[CommandHandler] 명령 파싱
    │
    ▼
[VisualizationOrchestrator] 시작
    │
    ├─► [AgentMessageBus] "차트 추천 중..." 전송
    │   └─► [TUI] ThinkingPanel 업데이트
    │
    ├─► [ChartRecommender.recommend()]
    │   ├─ 입력: DataFrame, dimensions, measures
    │   └─ 출력: List[ChartRecommendation]
    │
    ├─► [LayoutCalculator.calculate_layout()]
    │   ├─ 입력: List[LayoutComponent]
    │   └─ 출력: Dict[id → GridPosition]
    │
    ├─► [ThemeEngine.get_style()]
    │   ├─ 입력: component_type
    │   └─ 출력: Dict[style_properties]
    │
    ├─► [InteractionLogic.generate_var_list()]
    │   ├─ 입력: filters
    │   └─ 출력: List[var_definitions]
    │
    ├─► [SummaryGenerator.generate_summary()]
    │   ├─ 입력: intent, dataframes, charts, statistics
    │   └─ 출력: AnalysisSummary
    │
    ├─► [InhouseGenerator.build_report()]
    │   ├─ 입력: 위의 모든 결과물
    │   └─ 출력: suwon_pop.json
    │
    ├─► [PreviewServer.register_dashboard()]
    │   ├─ 입력: dashboard_id, dashboard_data
    │   └─ 출력: preview_url
    │
    └─► [TUI] 완료 메시지 + 미리보기 링크 표시
```

### 2. 상태 관리

Phase 4-5 실행 중 상태는 `VisualizationSession` 객체로 관리됩니다:

```python
@dataclass
class VisualizationSession:
    """시각화 세션 상태"""
    session_id: str
    intent: AnalysisIntent
    dataframes: Dict[str, pd.DataFrame]
    chart_recommendations: List[ChartRecommendation]
    selected_charts: List[ChartRecommendation]
    layout: Dict[str, GridPosition]
    theme: str
    summary: Optional[AnalysisSummary]
    output_path: Optional[Path]
    preview_url: Optional[str]
    status: str  # "in_progress", "completed", "failed"
    error: Optional[str]
```

---

## 기술 스택 검증

### 1. 신규 의존성

Phase 4-5 구현을 위해 다음 라이브러리가 필요합니다:

| 라이브러리 | 버전 | 용도 | 라이선스 |
|-----------|------|------|---------|
| `Flask` | ^3.0.0 | 로컬 웹 서버 | BSD-3-Clause |
| `openpyxl` | ^3.1.0 | Excel 출력 (선택) | MIT |
| `weasyprint` | ^60.0 | PDF 출력 (선택) | BSD-3-Clause |
| `Jinja2` | ^3.1.0 | 템플릿 엔진 | BSD-3-Clause |

**설치 명령**:
```bash
pip install Flask==3.0.0 openpyxl==3.1.0 Jinja2==3.1.0
# PDF 출력이 필요한 경우만:
# pip install weasyprint==60.0
```

### 2. 기존 의존성 활용

| 컴포넌트 | 기존 라이브러리 |
|---------|---------------|
| 데이터 분석 | `pandas`, `numpy` |
| LLM 통신 | `google-generativeai`, `anthropic` |
| 비동기 처리 | `asyncio` (표준 라이브러리) |
| TUI | `textual`, `rich` |

### 3. 성능 고려사항

- **메모리**: 대용량 DataFrame 처리 시 청크 단위 처리
- **CPU**: LLM 호출은 I/O 바운드이므로 비동기 처리
- **네트워크**: PreviewServer는 로컬 전용 (127.0.0.1)

---

## 구현 가이드라인

### 1. 코딩 표준

#### 1.1 타입 힌팅

모든 공개 API는 타입 힌팅을 적용합니다:

```python
from typing import List, Dict, Any, Optional
import pandas as pd

def recommend_chart(
    df: pd.DataFrame,
    dimensions: List[str],
    measures: List[str],
    intent: Optional[AnalysisIntent] = None
) -> List[ChartRecommendation]:
    """차트 추천 함수"""
    pass
```

#### 1.2 Docstring

모든 클래스와 공개 메서드는 docstring을 포함합니다:

```python
def calculate_layout(self, components: List[LayoutComponent]) -> Dict[str, GridPosition]:
    """
    컴포넌트들의 최적 레이아웃 계산

    알고리즘:
    1. 우선순위 순으로 정렬
    2. 각 컴포넌트를 사용 가능한 첫 위치에 배치
    3. 선호 너비를 최대한 보장

    Args:
        components: 배치할 컴포넌트 리스트

    Returns:
        컴포넌트 ID → GridPosition 매핑

    Example:
        >>> calculator = LayoutCalculator()
        >>> layout = calculator.calculate_layout([
        ...     LayoutComponent(id="kpi1", type="kpi", priority=ComponentPriority.CRITICAL)
        ... ])
    """
    pass
```

#### 1.3 에러 처리

명시적 예외 처리와 로깅:

```python
import logging

logger = logging.getLogger(__name__)

def recommend_chart(...):
    try:
        # 로직
        return recommendations
    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        raise
    except Exception as e:
        logger.exception("Unexpected error in chart recommendation")
        # 기본값 반환 또는 재시도
        return self._get_default_recommendations()
```

### 2. 테스트 전략

#### 2.1 단위 테스트

각 컴포넌트는 독립적으로 테스트 가능해야 합니다:

```python
# tests/test_chart_recommender.py
import pytest
import pandas as pd
from backend.agents.bi_tool.chart_recommender import ChartRecommender, ChartType

def test_timeseries_detection():
    df = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=10),
        'sales': range(10)
    })

    recommender = ChartRecommender()
    recommendations = recommender.recommend(df, ['date'], ['sales'])

    assert len(recommendations) > 0
    assert recommendations[0].chart_type == ChartType.LINE

def test_comparison_detection():
    df = pd.DataFrame({
        'category': ['A', 'B', 'C'],
        'value': [10, 20, 15]
    })

    recommender = ChartRecommender()
    recommendations = recommender.recommend(df, ['category'], ['value'])

    assert ChartType.BAR in [r.chart_type for r in recommendations]
```

#### 2.2 통합 테스트

전체 플로우를 테스트:

```python
# tests/integration/test_visualization_flow.py
@pytest.mark.asyncio
async def test_full_visualization_pipeline():
    # 준비
    orchestrator = VisualizationOrchestrator()
    intent = AnalysisIntent(...)
    df = load_test_data()

    # 실행
    result = await orchestrator.orchestrate(intent, {"main": df})

    # 검증
    assert result.status == "completed"
    assert result.output_path.exists()
    assert result.preview_url is not None
```

### 3. 성능 목표

| 작업 | 목표 시간 | 측정 방법 |
|------|---------|----------|
| 차트 추천 | < 2초 | 10,000행 데이터 기준 |
| 레이아웃 계산 | < 1초 | 20개 컴포넌트 기준 |
| 요약 생성 | < 10초 | LLM 호출 포함 |
| JSON 빌드 | < 3초 | 전체 대시보드 |
| 프리뷰 서버 시작 | < 0.5초 | 백그라운드 스레드 |

---

## 보안 및 성능 고려사항

### 1. 보안

#### 1.1 PreviewServer

- **바인딩**: `127.0.0.1`만 허용 (외부 접근 차단)
- **인증**: 로컬 전용이므로 인증 불필요
- **포트**: 동적 포트 할당 옵션 제공

#### 1.2 LLM 프롬프트

- **데이터 노출 최소화**: 샘플 데이터만 전송
- **개인정보 마스킹**: PII 자동 감지 및 마스킹 (향후)

### 2. 성능 최적화

#### 2.1 캐싱 전략

```python
from functools import lru_cache

class ChartRecommender:
    @lru_cache(maxsize=100)
    def _calculate_score(
        self,
        chart_type: ChartType,
        characteristic: DataCharacteristic,
        row_count: int,
        col_count: int
    ) -> float:
        """점수 계산 결과 캐싱"""
        pass
```

#### 2.2 비동기 처리

LLM 호출이 포함된 작업은 비동기로 처리:

```python
async def generate_all(self, ...):
    # 병렬 실행
    summary_task = asyncio.create_task(
        self.summary_generator.generate_summary(...)
    )

    # 순차 작업 먼저 수행
    charts = self.chart_recommender.recommend(...)
    layout = self.layout_calculator.calculate_layout(...)

    # 비동기 작업 대기
    summary = await summary_task

    return charts, layout, summary
```

#### 2.3 메모리 관리

대용량 DataFrame 처리:

```python
def _summarize_large_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
    """대용량 데이터 요약 (샘플링)"""
    if len(df) > 10000:
        sample_df = df.sample(n=10000, random_state=42)
    else:
        sample_df = df

    return {
        "row_count": len(df),
        "sample_statistics": sample_df.describe().to_dict()
    }
```

### 3. 에러 복구

#### 3.1 Graceful Degradation

컴포넌트 실패 시 대안 제공:

```python
def recommend_chart(...) -> List[ChartRecommendation]:
    try:
        # LLM 기반 추천 시도
        return self._llm_recommend(...)
    except Exception as e:
        logger.warning(f"LLM recommendation failed: {e}")
        # 규칙 기반 추천으로 폴백
        return self._rule_based_recommend(...)
```

#### 3.2 재시도 로직

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def _llm_generate(self, prompt: str) -> str:
    """LLM 호출 (자동 재시도)"""
    return await self.llm.generate(prompt)
```

---

## 구현 우선순위

### Phase 1: 핵심 컴포넌트 (Week 1-2)

1. **ChartRecommender** (Builder-1)
   - 규칙 기반 추천
   - 데이터 특성 감지
   - 단위 테스트

2. **LayoutCalculator** (Builder-2)
   - 그리드 배치 알고리즘
   - InHouse 형식 변환
   - 단위 테스트

3. **ThemeEngine 확장** (Builder-1)
   - 3개 테마 추가
   - 폰트 메타데이터
   - 단위 테스트

### Phase 2: 통합 및 출력 (Week 3)

4. **SummaryGenerator** (Builder-1)
   - LLM 프롬프트 설계
   - 응답 파싱
   - 단위 테스트

5. **PreviewServer** (Builder-2)
   - Flask 서버 구현
   - HTML 템플릿
   - 단위 테스트

6. **InhouseGenerator 강화** (Builder-1 & Builder-2)
   - 신규 컴포넌트 통합
   - 최종 JSON 빌드
   - 통합 테스트

### Phase 3: 품질 검증 (Week 4)

7. **통합 테스트** (QA-Tester)
8. **성능 테스트** (QA-Tester)
9. **문서화** (All)

---

## 부록

### A. 디렉토리 구조

```
backend/
├── agents/
│   ├── bi_tool/
│   │   ├── chart_recommender.py       # NEW
│   │   ├── layout_calculator.py       # NEW
│   │   ├── summary_generator.py       # NEW
│   │   ├── theme_engine.py            # ENHANCED
│   │   ├── interaction_logic.py       # ENHANCED
│   │   └── inhouse_generator.py       # ENHANCED
│   └── data_source/
│       └── ... (기존)
├── orchestrator/
│   ├── orchestrators/
│   │   └── visualization_orchestrator.py  # NEW
│   └── ... (기존)
└── utils/
    ├── preview_server.py              # NEW
    └── ... (기존)

tests/
├── test_chart_recommender.py          # NEW
├── test_layout_calculator.py          # NEW
├── test_summary_generator.py          # NEW
├── test_preview_server.py             # NEW
└── integration/
    └── test_visualization_flow.py     # NEW
```

### B. 참고 문서

- [PLAN.md](../core/PLAN.md): 전체 로드맵
- [DETAILED_SPEC.md](../core/DETAILED_SPEC.md): 상세 구현 계획
- [TODO.md](../core/TODO.md): 현재 진행 상황

---

**문서 버전**: 1.0
**최종 검토**: 2026-02-11
**다음 리뷰**: Phase 4 구현 완료 후

---

## 승인

이 설계는 다음 요구사항을 충족합니다:

- ✅ 모든 Phase 4-5 컴포넌트 정의
- ✅ 인터페이스 및 의존성 명시
- ✅ 데이터 흐름 및 통합 패턴 제시
- ✅ 구현 가이드라인 제공
- ✅ 테스트 전략 수립
- ✅ 보안 및 성능 고려

**Architect 승인**: ✅
**준비 상태**: 구현 시작 가능
