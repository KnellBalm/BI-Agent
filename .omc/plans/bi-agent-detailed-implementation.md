# BI-Agent Detailed Implementation Plan

**Plan ID:** `bi-agent-detailed-implementation`
**Created:** 2026-01-30
**Refined:** 2026-01-30 (Iteration 2 - Critic feedback addressed)
**Based on:** docs/PLAN.md (Roadmap 2.1)

---

## Executive Summary

This plan provides granular implementation tasks for BI-Agent's 15-step roadmap. The project aims to build an **Intelligent Analysis Workspace** where analysts can obtain BI reports through a transparent, controllable agent system within a TUI (Terminal User Interface).

**Iteration 2 Changes:**
- Added Section 0: Foundational Refactoring (BaseIntent architecture)
- Added Section 9: New Dependencies
- Added LLM prompt templates for Tasks 5.1.2, 10.2.2
- Added Textual screen integration patterns
- Removed Tableau .twb export (deferred to future phase)
- Fixed acceptance criteria with measurable thresholds

---

## 0. Foundational Refactoring (PRE-REQUISITE)

This section MUST be completed before Phase 2 tasks begin. It establishes the shared intent architecture.

### 0.1 Create BaseIntent Abstract Base Class
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/base_intent.py` (NEW)

**Rationale:** Both `ChartIntent` and `AnalysisIntent` share common fields (filters, datasource). A shared base class ensures consistency and enables polymorphic handling.

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 0.1.1 | Create `BaseIntent` abstract base class | ABC with `@abstractmethod validate()` |
| 0.1.2 | Define common fields | `datasource`, `filters`, `title` as base fields |
| 0.1.3 | Add `to_dict()` method | Returns dataclass fields as dictionary |
| 0.1.4 | Add type discriminator | `intent_type` property returns "chart" or "analysis" |

**Code:**
```python
# /backend/agents/bi_tool/base_intent.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

@dataclass
class BaseIntent(ABC):
    """Abstract base class for all intent types in BI-Agent.

    Shared fields:
    - datasource: Target table/dataset name
    - filters: List of filter conditions [{field, operator, value}]
    - title: Optional descriptive title
    """
    datasource: str
    filters: List[Dict[str, Any]]
    title: Optional[str] = None

    @property
    @abstractmethod
    def intent_type(self) -> str:
        """Return 'chart' or 'analysis' to identify intent subtype."""
        pass

    @abstractmethod
    def validate(self) -> bool:
        """Validate the intent structure. Returns True if valid."""
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)
```

### 0.2 Refactor ChartIntent to Extend BaseIntent
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/nl_intent_parser.py`

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 0.2.1 | Import `BaseIntent` from `base_intent.py` | Import statement added |
| 0.2.2 | Change `ChartIntent` to extend `BaseIntent` | `class ChartIntent(BaseIntent):` |
| 0.2.3 | Move common fields to super().__init__() | `datasource`, `filters`, `title` |
| 0.2.4 | Implement `intent_type` property | Returns `"chart"` |
| 0.2.5 | Update unit tests | Existing tests pass with refactored class |

**Refactored ChartIntent:**
```python
# Updated in nl_intent_parser.py
from backend.agents.bi_tool.base_intent import BaseIntent

@dataclass
class ChartIntent(BaseIntent):
    """Structured representation of a chart creation/modification intent."""
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

### 0.3 Create AnalysisIntent Class
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/analysis_intent.py` (NEW)

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 0.3.1 | Create `AnalysisIntent` extending `BaseIntent` | Implements `validate()` and `intent_type` |
| 0.3.2 | Add analysis-specific fields | `purpose`, `target_metrics`, `hypothesis`, `expected_output` |
| 0.3.3 | Add `produces_charts()` method | Returns `List[ChartIntent]` generated from analysis |
| 0.3.4 | Unit tests for AnalysisIntent | 5+ test cases covering validation |

**Code:**
```python
# /backend/agents/bi_tool/analysis_intent.py
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from backend.agents.bi_tool.base_intent import BaseIntent

@dataclass
class AnalysisIntent(BaseIntent):
    """Structured representation of a complex analysis intent.

    An AnalysisIntent represents a high-level analytical goal that may
    produce multiple ChartIntents during execution.

    Relationship: AnalysisIntent -> produces -> ChartIntent[]
    """
    purpose: str  # "performance" | "trend" | "anomaly" | "comparison" | "forecast"
    target_metrics: List[str] = field(default_factory=list)
    time_range: Optional[Dict[str, str]] = None  # {"start": "2024-01-01", "end": "2024-12-31"}
    hypothesis: Optional[str] = None
    expected_output: str = "dashboard"  # "dashboard" | "report" | "insight"
    scope: Optional[str] = None  # "전체", "서울지역", etc.
    constraints: List[str] = field(default_factory=list)  # Additional constraints
    kpis: List[str] = field(default_factory=list)  # Key Performance Indicators

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
        """Generate ChartIntents from this AnalysisIntent.

        The actual chart generation is handled by the pipeline generator,
        but this method provides a preview of likely chart types.
        """
        from backend.agents.bi_tool.nl_intent_parser import ChartIntent

        charts = []
        # Map purpose to likely chart types
        purpose_chart_map = {
            "trend": "line",
            "comparison": "bar",
            "performance": "bar",
            "anomaly": "scatter",
            "forecast": "line",
            "correlation": "scatter"
        }

        default_type = purpose_chart_map.get(self.purpose, "bar")

        for metric in self.target_metrics[:3]:  # Max 3 charts
            charts.append(ChartIntent(
                action="create",
                visual_type=default_type,
                datasource=self.datasource,
                dimensions=[],  # To be filled by pipeline
                measures=[metric],
                filters=self.filters.copy(),
                title=f"{metric} {self.purpose} analysis"
            ))

        return charts
```

### 0.4 Verification Checkpoint
Before proceeding to Phase 2:

| Checkpoint | Verification Command |
|------------|---------------------|
| BaseIntent exists | `python -c "from backend.agents.bi_tool.base_intent import BaseIntent"` |
| ChartIntent extends BaseIntent | `python -c "from backend.agents.bi_tool.nl_intent_parser import ChartIntent; assert ChartIntent.__bases__[0].__name__ == 'BaseIntent'"` |
| AnalysisIntent exists | `python -c "from backend.agents.bi_tool.analysis_intent import AnalysisIntent"` |
| Tests pass | `pytest tests/test_intents.py -v` (create test file) |

---

## 1. Current State Assessment

### 1.1 Completed (Phase 1: Steps 1-3)

| Step | Feature | Status | Implementation Files |
|------|---------|--------|---------------------|
| Step 1 | Launch | **COMPLETE** | `backend/orchestrator/bi_agent_console.py` (ASCII banner, env check) |
| Step 2 | Smart Auth | **COMPLETE** | `backend/orchestrator/auth_manager.py`, `AuthScreen` in console |
| Step 3 | Connection | **COMPLETE** | `backend/agents/data_source/connection_manager.py`, `ConnectionScreen` |

### 1.2 Partially Implemented (Foundation)

| Component | Status | Location |
|-----------|--------|----------|
| LLM Provider System | Working | `backend/orchestrator/llm_provider.py` (Gemini, Claude, OpenAI, Ollama failover) |
| Metadata Scanner | Working | `backend/agents/data_source/metadata_scanner.py` |
| Data Profiler | Working | `backend/agents/data_source/profiler.py` |
| NL Intent Parser | Exists, needs integration | `backend/agents/bi_tool/nl_intent_parser.py` |
| Interaction Logic | Basic | `backend/agents/bi_tool/interaction_logic.py` |
| InHouse Generator | Working | `backend/agents/bi_tool/inhouse_generator.py` |
| Theme Engine | Working | `backend/agents/bi_tool/theme_engine.py` |
| Collaborative Orchestrator | Partial | `backend/orchestrator/collaborative_orchestrator.py` |
| TUI Message Components | Working | `backend/orchestrator/message_components.py` |

### 1.3 Not Started (Steps 4-15)

All Phase 2-5 steps require implementation from scratch or significant enhancement.

---

## 2. Technical Dependencies Graph

```
Section 0 (BaseIntent) ────────────────────────────────────────────────┐
                                                                       v
Step 4 (Intent) ──────┐
                      ├──> Step 7 (Planning) ──> Step 10 (Querying)
Step 5 (Targeting) ───┤                              │
                      │                              v
Step 6 (Scanning) ────┘                    Step 11 (Designing) ──> Step 13 (Preview)
                                                    │                      │
                                                    v                      v
                                           Step 12 (Interactive) ──> Step 14 (Refine)
                                                                           │
Step 8 (Thinking CoT) ─────────────────────────────────────────────────────┤
Step 9 (Alignment) ────────────────────────────────────────────────────────┤
                                                                           v
                                                                    Step 15 (Export)
```

---

## 3. Phase 2: Intent & Context Scanning (Steps 4-6)

### Step 4: Analysis Intent Declaration (분석 의도 선언)

**Objective:** Enable users to declare complex analysis intents via `/intent` command and have LLM generate an execution plan.

#### Task 4.1: Enhance `/intent` Command Handler
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/orchestrator/bi_agent_console.py`

**Current State:** Basic `/intent` command exists (lines 883-895), but only passes to `handle_intent()` without full pipeline.

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 4.1.1 | Parse intent with argument extraction | `/intent 매출 하락 원인 분석` extracts `intent_text = "매출 하락 원인 분석"` |
| 4.1.2 | Display thinking panel during plan generation | `ThinkingPanel` widget shows "의도 분석 중...", "플랜 생성 중..." |
| 4.1.3 | Store intent in session context | `self.orchestrator.current_intent` holds structured intent object |
| 4.1.4 | Render generated plan as selectable steps | Each step appears as a numbered list with checkboxes |

**Code Changes:**
```python
# In bi_agent_console.py, enhance handle_command() for "/intent"
# Add: IntentSession dataclass to store parsed intent
# Add: PlanDisplayWidget for rendering step-by-step plans
```

#### Task 4.2: LLM-based Intent Classification
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/nl_intent_parser.py`

**Current State:** `NLIntentParser` exists but focused on chart intents only.

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 4.2.1 | Add import for `AnalysisIntent` | `from backend.agents.bi_tool.analysis_intent import AnalysisIntent` |
| 4.2.2 | Create `parse_analysis_intent()` method | Returns `AnalysisIntent` from Korean/English NL input |
| 4.2.3 | Implement purpose auto-extraction | "성능" -> performance, "추이" -> trend, "이상치" -> anomaly |
| 4.2.4 | Unit tests for intent parsing | 10+ test cases covering Korean and English inputs |

**LLM Prompt Template for Task 4.2.2:**
```python
ANALYSIS_INTENT_PROMPT = """You are a BI analysis intent parser. Parse the following natural language request into a structured analysis intent.

The user's request is in Korean or English. Extract the following information:

1. **purpose**: Analysis purpose - "performance", "trend", "anomaly", "comparison", "forecast", "correlation"
2. **target_metrics**: List of metrics/KPIs to analyze (e.g., ["매출", "주문수", "고객수"])
3. **datasource**: The target data source or table (infer if not explicit)
4. **time_range**: Time period as {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"} or null
5. **hypothesis**: The hypothesis to test (if mentioned, else null)
6. **expected_output**: Output format - "dashboard", "report", or "insight"
7. **filters**: List of filter conditions as objects with "field", "operator", "value"
8. **scope**: Analysis scope description (e.g., "전체", "서울지역", "온라인채널")
9. **constraints**: Additional constraints or limitations as list of strings
10. **kpis**: Key Performance Indicators to track

**Korean to English purpose mapping:**
- 추이/트렌드/동향 = trend
- 성능/성과/실적 = performance
- 이상치/이상/비정상 = anomaly
- 비교/대조 = comparison
- 예측/전망/예상 = forecast
- 상관/관계 = correlation

**Korean to English field mapping:**
- 매출/판매액 = sales
- 주문/주문수 = orders
- 고객/고객수 = customers
- 월/월별 = month
- 지역 = region
- 카테고리 = category
- 제품/상품 = product

User Request: "{user_input}"

Response MUST be valid JSON in this exact format:
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

Return ONLY the JSON, no additional text or explanation."""
```

#### Task 4.3: Command History & Tab Completion
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/orchestrator/bi_agent_console.py`

**Current State:** Basic tab completion exists for commands (lines 748-773), no history.

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 4.3.1 | Add CommandHistory class | Stores last 100 commands in `~/.bi-agent/history.json` |
| 4.3.2 | Up/Down arrow navigation | Pressing Up shows previous command, Down shows next |
| 4.3.3 | Tab completion for intent phrases | Common phrases like "매출", "분석", "추이" autocomplete |
| 4.3.4 | Persist history across sessions | History loads on startup, saves on `/intent` execution |

---

### Step 5: Target Data Selection (타겟 데이터 선정)

**Objective:** LLM recommends relevant tables for user queries; interactive table selection UI.

#### Task 5.1: Table Recommendation Algorithm
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/data_source/table_recommender.py` (NEW)

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 5.1.1 | Create `TableRecommender` class | Takes `AnalysisIntent` + schema metadata, returns ranked table list |
| 5.1.2 | LLM-based relevance scoring | Each table gets 0-100 relevance score with explanation |
| 5.1.3 | Column semantic matching | Matches intent keywords to column names/descriptions |
| 5.1.4 | Multi-table relationship detection | Identifies potential JOIN relationships |

**LLM Prompt Template for Task 5.1.2:**
```python
TABLE_RECOMMENDATION_PROMPT = """You are a database expert helping select relevant tables for analysis.

**Analysis Intent:**
- Purpose: {purpose}
- Target Metrics: {target_metrics}
- Hypothesis: {hypothesis}
- Filters: {filters}

**Available Database Schema:**
{schema_json}

**Task:**
For each table in the schema, provide:
1. A relevance score (0-100) indicating how useful this table is for the analysis
2. A brief explanation in Korean why this score was assigned
3. Which columns in this table are relevant to the analysis
4. Potential JOIN relationships with other tables

**Scoring Guidelines:**
- 90-100: Table directly contains the target metrics and dimensions
- 70-89: Table contains related data that supports the analysis
- 50-69: Table might be useful for context or filtering
- 0-49: Table is not relevant to this analysis

Return JSON array:
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

Return ONLY the JSON array, no additional text."""
```

**Class Skeleton:**
```python
class TableRecommender:
    def __init__(self, llm: LLMProvider, schema: Dict[str, Any]):
        self.llm = llm
        self.schema = schema

    async def recommend_tables(self, intent: AnalysisIntent) -> List[TableRecommendation]:
        """Returns ranked list of TableRecommendation objects"""
        pass

    async def infer_relationships(self, tables: List[str]) -> List[ERDRelationship]:
        """Detects FK/PK relationships and suggests JOINs"""
        pass
```

#### Task 5.2: Interactive Table Selection UI
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/orchestrator/bi_agent_console.py`

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 5.2.1 | Create `TableSelectionScreen` modal | Displays recommended tables with relevance scores |
| 5.2.2 | Add OptionList for table selection | Tables shown with icons, descriptions, row counts |
| 5.2.3 | Multi-select capability | User can select 1-5 tables for multi-table analysis |
| 5.2.4 | Show JOIN suggestions | If multiple tables selected, display suggested JOINs |

**UI Layout:**
```
+------------------------------------------+
| Select Target Tables                      |
| Intent: "월별 매출 추이 분석"              |
+------------------------------------------+
| [x] sales (95% match) - 15,000 rows       |
|     "매출", "금액" columns detected        |
| [ ] customers (60% match) - 2,000 rows    |
|     Possible JOIN: sales.customer_id      |
| [ ] products (45% match) - 500 rows       |
+------------------------------------------+
| [Enter] Confirm  [Space] Toggle  [Esc] Cancel
+------------------------------------------+
```

#### Task 5.3: ERD Relationship Auto-inference
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/data_source/erd_analyzer.py` (NEW)

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 5.3.1 | Detect FK by naming convention | `*_id` columns matched to corresponding tables |
| 5.3.2 | LLM-assisted relationship inference | Prompt LLM with column names to infer relationships |
| 5.3.3 | Generate JOIN clause suggestions | Output: `"LEFT JOIN customers ON sales.customer_id = customers.id"` |
| 5.3.4 | Visualize ERD in TUI (ASCII) | Simple text-based ERD diagram |

---

### Step 6: Deep Scanning (딥 스캐닝)

**Objective:** Real-time statistical profiling, sample data display, and data type auto-correction.

#### Task 6.1: Enhanced Column Statistics
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/data_source/profiler.py`

**Current State:** Basic profiling exists with mean, std, min, max, top_values.

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 6.1.1 | Add missing value percentage per column | `missing_pct` field in column details |
| 6.1.2 | Add mode (most frequent value) | `mode` field for all column types |
| 6.1.3 | Add quantiles (25%, 50%, 75%) | `q25`, `q50`, `q75` for numerical columns |
| 6.1.4 | Add value distribution histogram data | `distribution` field with bin counts |
| 6.1.5 | Add data quality score | 0-100 score based on completeness, consistency |

**Enhanced Output:**
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

#### Task 6.2: Sample Data Grid Component
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/orchestrator/components/data_grid.py` (NEW)

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 6.2.1 | Create `SampleDataGrid` Textual widget | Displays 5-10 rows in scrollable DataTable |
| 6.2.2 | Column type indicators | Icons: 📊 numerical, 📝 text, 📅 datetime, 🏷️ categorical |
| 6.2.3 | Truncate long values | Values > 50 chars show "..." with hover for full value |
| 6.2.4 | Export sample to clipboard | Ctrl+C copies selected rows as CSV (requires `pyperclip`) |

#### Task 6.3: Data Type Auto-correction
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/data_source/type_corrector.py` (NEW)

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 6.3.1 | Detect date strings mistyped as text | `"2024-01-15"` detected as datetime, not text |
| 6.3.2 | Detect numeric strings | `"1,234.56"` or `"1234"` detected as numerical |
| 6.3.3 | Suggest type corrections | Returns list of `{column, current_type, suggested_type, confidence}` |
| 6.3.4 | Apply corrections on user approval | User approves/rejects each suggestion |

---

## 4. Phase 3: Strategy & Hypothesis (Steps 7-9)

### Step 7: Analysis Execution Plan (분석 실행 플랜 수립)

**Objective:** Generate detailed analysis pipeline from `/intent`, with industry templates and ROI simulation.

#### Task 7.1: Pipeline Generation Engine
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/pipeline_generator.py` (NEW)

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 7.1.1 | Create `AnalysisPipeline` dataclass | Fields: `steps[]`, `estimated_duration`, `required_data`, `expected_outputs` |
| 7.1.2 | LLM generates 3-7 step pipeline | Each step has: action, description, agent_type, dependencies |
| 7.1.3 | Validate pipeline feasibility | Check if required columns/tables exist |
| 7.1.4 | Pipeline serialization | Save/load pipelines to `.bi-agent/pipelines/{name}.json` |

**LLM Prompt Template for Task 7.1.2:**
```python
PIPELINE_GENERATION_PROMPT = """You are a BI analysis planner. Generate an execution pipeline for the following analysis intent.

**Analysis Intent:**
- Purpose: {purpose}
- Target Metrics: {target_metrics}
- Hypothesis: {hypothesis}
- Selected Tables: {selected_tables}
- Constraints: {constraints}

**Available Schema:**
{schema_json}

**Task:**
Generate a 3-7 step analysis pipeline. Each step should be:
1. Actionable and specific
2. Assigned to an agent type
3. Have clear input/output data

**Agent Types:**
- DataMaster: Data profiling, quality checks, transformations
- Strategist: Hypothesis generation, insight extraction, recommendations
- Designer: Chart creation, layout design, visualization

Return JSON:
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

Return ONLY the JSON, no additional text."""
```

**Pipeline Step Structure:**
```python
@dataclass
class PipelineStep:
    step_id: str
    action: str  # "profile", "query", "transform", "visualize", "insight"
    description: str  # Korean description
    agent: str  # "DataMaster", "Strategist", "Designer"
    input_data: List[str]
    output_data: str
    estimated_seconds: int
    dependencies: List[str]  # step_ids that must complete first
```

#### Task 7.2: Hypothesis Template Engine
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/hypothesis_templates.py` (NEW)

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 7.2.1 | Create industry template registry | Templates for retail, finance, manufacturing, healthcare |
| 7.2.2 | Template format with placeholders | `"{{metric}} 성장은 {{dimension}}에 비례한다"` |
| 7.2.3 | Context-aware template selection | Based on detected columns, suggest relevant templates |
| 7.2.4 | User can customize templates | Edit placeholders before applying |

**Template Examples:**
```python
RETAIL_TEMPLATES = [
    "{{매출}} 증가는 {{요일}} 트래픽과 비례한다",
    "{{카테고리}}별 {{반품률}}은 계절에 따라 변동한다",
    "{{신규고객}} 유입은 {{마케팅채널}} 효과에 의존한다"
]
```

#### Task 7.3: ROI Simulation Preview
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/roi_simulator.py` (NEW)

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 7.3.1 | Estimate analysis value qualitatively | Output: "이 분석은 매출 향상에 기여할 가능성이 높습니다" with confidence >= 0.7 for high-value analyses |
| 7.3.2 | LLM generates business value statement | Based on intent and industry context |
| 7.3.3 | Display confidence level | High (>=0.7)/Medium (0.4-0.69)/Low (<0.4) confidence with rationale |
| 7.3.4 | Historical comparison (if available) | "과거 유사 분석 결과 평균 ROI: +8%" |

---

### Step 8: Thinking Process Visualization (사고 과정 시각화)

**Objective:** Real-time display of agent internal messages and LLM "thinking" stages.

#### Task 8.1: Agent Message Bus
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/orchestrator/agent_message_bus.py` (NEW)

**Architecture Decision:** Use `asyncio.Queue` with Textual Worker Pattern (NOT Redis).

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 8.1.1 | Create `AgentMessageBus` class | `asyncio.Queue`-based pub/sub system |
| 8.1.2 | Define message types | `THINKING`, `DATA_REQUEST`, `DATA_RESPONSE`, `INSIGHT`, `ERROR` |
| 8.1.3 | Subscribe TUI to message bus | Console receives all messages via Textual Worker |
| 8.1.4 | Message persistence | Save messages to `logs/agent_messages.jsonl` |

**Implementation Code:**
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
    to_agent: str  # Target agent or "broadcast"
    message_type: MessageType
    content: str  # Korean message content
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        d['message_type'] = self.message_type.value
        return d

class AgentMessageBus:
    """Async message bus for agent-to-agent and agent-to-TUI communication.

    Uses asyncio.Queue for thread-safe message passing without external dependencies.
    Integrates with Textual's Worker pattern for UI updates.
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
        """Subscribe to receive all messages. Callback is invoked for each message."""
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[AgentMessage], None]) -> None:
        """Remove a subscriber."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    async def publish(self, message: AgentMessage) -> None:
        """Publish a message to all subscribers."""
        await self._queue.put(message)

        # Persist to log file
        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(message.to_dict(), ensure_ascii=False) + "\n")

    async def start(self) -> None:
        """Start the message dispatch loop."""
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
        """Stop the message dispatch loop."""
        self._running = False

    # Convenience methods for common message types
    async def thinking(self, from_agent: str, content: str, **metadata) -> None:
        await self.publish(AgentMessage(
            timestamp=datetime.now(),
            from_agent=from_agent,
            to_agent="broadcast",
            message_type=MessageType.THINKING,
            content=content,
            metadata=metadata
        ))

    async def progress(self, from_agent: str, step: int, total: int, description: str) -> None:
        await self.publish(AgentMessage(
            timestamp=datetime.now(),
            from_agent=from_agent,
            to_agent="broadcast",
            message_type=MessageType.PROGRESS,
            content=description,
            metadata={"step": step, "total": total, "percent": round(step/total*100)}
        ))
```

#### Task 8.2: Thinking Stage Translator
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/orchestrator/thinking_translator.py` (NEW)

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 8.2.1 | Map LLM internal states to Korean labels | "스키마 해석 중...", "가설 생성 중...", "쿼리 최적화 중..." |
| 8.2.2 | Detect stage transitions | When LLM moves from schema analysis to query generation |
| 8.2.3 | Display progress indicator | "2/5 단계 완료" with progress bar |
| 8.2.4 | Estimated remaining time | "예상 남은 시간: 30초" |

#### Task 8.3: Real-time ThinkingPanel Updates
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/orchestrator/message_components.py`

**Current State:** `ThinkingPanel` exists but is static.

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 8.3.1 | Connect ThinkingPanel to AgentMessageBus | Auto-updates when new messages arrive |
| 8.3.2 | Add step checkmarks | ✓ for completed steps, ⏳ for in-progress |
| 8.3.3 | Expandable details | Click on step to see full content |
| 8.3.4 | Animation for active step | Pulsing indicator for current step |

---

### Step 9: User Alignment (사용자 정렬)

**Objective:** Interactive hypothesis selection, constraint input, and approval workflow.

#### Task 9.1: Hypothesis Selection Screen
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/orchestrator/screens/hypothesis_screen.py` (NEW)

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 9.1.1 | Create `HypothesisScreen` modal | Displays generated hypotheses as selectable options |
| 9.1.2 | Editable hypothesis text | User can modify text before approval |
| 9.1.3 | Priority ranking (drag-drop or numbers) | Order hypotheses by priority |
| 9.1.4 | Dismiss unwanted hypotheses | Remove from analysis scope |

**Textual Screen Integration Pattern:**
```python
# /backend/orchestrator/screens/hypothesis_screen.py
"""
Hypothesis Selection Screen for User Alignment (Step 9).

Integration with bi_agent_console.py:
1. Import: from backend.orchestrator.screens.hypothesis_screen import HypothesisScreen
2. Push screen: self.push_screen(HypothesisScreen(hypotheses, on_confirm_callback))
3. Handle callback: def on_confirm_callback(selected_hypotheses: List[Hypothesis]): ...
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
    Interactive hypothesis selection and editing screen.

    Usage in bi_agent_console.py handle_command():
    ```python
    elif cmd == "/hypothesis" or (awaiting_hypothesis_selection):
        hypotheses = self.orchestrator.get_generated_hypotheses()

        def on_hypothesis_confirmed(selected: List[Hypothesis]):
            self.orchestrator.set_approved_hypotheses(selected)
            msg = MessageBubble(role="system", content=f"[green]✅ {len(selected)}개 가설이 승인되었습니다.[/green]")
            chat_log.mount(msg)
            chat_log.scroll_end(animate=False)

        self.push_screen(HypothesisScreen(hypotheses, on_hypothesis_confirmed))
    ```
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
        ("y", "confirm", "Approve"),
        ("n", "cancel", "Cancel"),
        ("e", "edit", "Edit Selected"),
        ("space", "toggle", "Toggle Selection"),
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, hypotheses: List[Hypothesis], callback: Callable[[List[Hypothesis]], None]):
        super().__init__()
        self.hypotheses = hypotheses
        self.callback = callback
        self.selected_index = 0

    def compose(self) -> ComposeResult:
        with Container(id="hypothesis-modal"):
            yield Label("Generated Hypotheses (Select & Edit)", id="hypothesis-title")
            yield Label("[dim]Space: Toggle | E: Edit | Y: Approve | N: Cancel[/dim]")

            options = []
            for i, h in enumerate(self.hypotheses):
                prefix = "[x]" if h.selected else "[ ]"
                options.append(Option(f"{prefix} {i+1}. {h.text}", id=h.id))

            yield OptionList(*options, id="hypothesis-list")
            yield Input(id="edit-input", placeholder="Edit hypothesis text...")

            with Horizontal():
                yield Button("[+ Add Custom]", id="add-btn", classes="action-btn")
                yield Button("[Y] Approve", id="confirm-btn", classes="action-btn")
                yield Button("[N] Cancel", id="cancel-btn", classes="action-btn")

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
            # Update display
            prefix = "[x]" if self.hypotheses[idx].selected else "[ ]"
            # Note: OptionList doesn't support direct text update, would need to refresh

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
            # Add custom hypothesis
            new_h = Hypothesis(id=f"custom_{len(self.hypotheses)}", text="새로운 가설 입력...")
            self.hypotheses.append(new_h)
            # Refresh list
```

**UI Layout:**
```
+------------------------------------------+
| Generated Hypotheses (Select & Edit)     |
+------------------------------------------+
| [x] 1. 주말 매출이 평일 대비 30% 높다     |
|        [Edit] [Remove]                    |
| [ ] 2. 서울 지역 매출이 전체 50%를 차지   |
|        [Edit] [Remove]                    |
| [ ] 3. 특정 카테고리가 계절에 영향받음    |
|        [Edit] [Remove]                    |
+------------------------------------------+
| [+ Add Custom Hypothesis]                 |
+------------------------------------------+
| [Y] Approve  [N] Cancel  [E] Edit All     |
+------------------------------------------+
```

#### Task 9.2: Constraint Input Workflow
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/orchestrator/screens/constraint_screen.py` (NEW)

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 9.2.1 | Create `ConstraintScreen` modal | Input fields for date range, region, category filters |
| 9.2.2 | Date range picker | Start/end date inputs with validation (YYYY-MM-DD format) |
| 9.2.3 | Multi-select for categorical constraints | "지역: [서울] [부산] [대구]" toggles |
| 9.2.4 | Free-text constraint input | User can type additional constraints |

**Textual Screen Integration Pattern:**
```python
# /backend/orchestrator/screens/constraint_screen.py
"""
Constraint Input Screen for User Alignment (Step 9).

Integration with bi_agent_console.py:
1. Import: from backend.orchestrator.screens.constraint_screen import ConstraintScreen
2. Push screen: self.push_screen(ConstraintScreen(available_dimensions, on_confirm_callback))
3. Handle callback: def on_confirm_callback(constraints: ConstraintSet): ...
"""

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, Button, Input, Checkbox
from textual.containers import Container, Vertical, Horizontal
from dataclasses import dataclass, field
from typing import List, Callable, Dict, Any
import re

@dataclass
class ConstraintSet:
    date_start: str = ""
    date_end: str = ""
    selected_regions: List[str] = field(default_factory=list)
    selected_categories: List[str] = field(default_factory=list)
    custom_constraints: List[str] = field(default_factory=list)

    def to_filters(self) -> List[Dict[str, Any]]:
        """Convert constraints to filter list for AnalysisIntent."""
        filters = []
        if self.date_start:
            filters.append({"field": "date", "operator": ">=", "value": self.date_start})
        if self.date_end:
            filters.append({"field": "date", "operator": "<=", "value": self.date_end})
        if self.selected_regions:
            filters.append({"field": "region", "operator": "IN", "value": self.selected_regions})
        if self.selected_categories:
            filters.append({"field": "category", "operator": "IN", "value": self.selected_categories})
        return filters

class ConstraintScreen(ModalScreen):
    """
    Interactive constraint input screen.

    Usage in bi_agent_console.py handle_command():
    ```python
    elif cmd == "/constraints":
        dimensions = self.orchestrator.get_available_dimensions()

        def on_constraints_confirmed(constraints: ConstraintSet):
            self.orchestrator.apply_constraints(constraints)
            msg = MessageBubble(role="system", content="[green]✅ 제약조건이 적용되었습니다.[/green]")
            chat_log.mount(msg)

        self.push_screen(ConstraintScreen(dimensions, on_constraints_confirmed))
    ```
    """

    CSS = """
    ConstraintScreen {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }
    #constraint-modal {
        width: 65;
        height: auto;
        background: #1a1b1e;
        border: solid #2d2f34;
        padding: 1 2;
    }
    .section-label {
        color: #94a3b8;
        margin-top: 1;
        text-style: bold;
    }
    .date-input {
        width: 20;
        background: #111214;
        border: solid #2d2f34;
    }
    .checkbox-row {
        margin: 0 1;
    }
    """

    def __init__(self, dimensions: Dict[str, List[str]], callback: Callable[[ConstraintSet], None]):
        super().__init__()
        self.dimensions = dimensions  # {"regions": ["서울", "부산"], "categories": ["전자", "식품"]}
        self.callback = callback
        self.constraint_set = ConstraintSet()

    def compose(self) -> ComposeResult:
        with Container(id="constraint-modal"):
            yield Label("Analysis Constraints (분석 제약조건)", id="constraint-title")

            yield Label("Date Range (날짜 범위):", classes="section-label")
            with Horizontal():
                yield Input(id="date-start", placeholder="2024-01-01", classes="date-input")
                yield Label(" ~ ")
                yield Input(id="date-end", placeholder="2024-12-31", classes="date-input")

            if "regions" in self.dimensions:
                yield Label("Regions (지역):", classes="section-label")
                with Horizontal(classes="checkbox-row"):
                    for region in self.dimensions["regions"]:
                        yield Checkbox(region, id=f"region_{region}")

            if "categories" in self.dimensions:
                yield Label("Categories (카테고리):", classes="section-label")
                with Horizontal(classes="checkbox-row"):
                    for cat in self.dimensions["categories"]:
                        yield Checkbox(cat, id=f"cat_{cat}")

            yield Label("Custom Constraints (추가 조건):", classes="section-label")
            yield Input(id="custom-constraint", placeholder="예: 금액 > 10000")

            with Horizontal():
                yield Button("Apply", id="apply-btn")
                yield Button("Cancel", id="cancel-btn")

    def _validate_date(self, date_str: str) -> bool:
        """Validate YYYY-MM-DD format."""
        return bool(re.match(r'^\d{4}-\d{2}-\d{2}$', date_str))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "apply-btn":
            # Collect values
            self.constraint_set.date_start = self.query_one("#date-start", Input).value
            self.constraint_set.date_end = self.query_one("#date-end", Input).value

            # Validate dates
            if self.constraint_set.date_start and not self._validate_date(self.constraint_set.date_start):
                self.notify("Invalid start date format. Use YYYY-MM-DD.", severity="error")
                return
            if self.constraint_set.date_end and not self._validate_date(self.constraint_set.date_end):
                self.notify("Invalid end date format. Use YYYY-MM-DD.", severity="error")
                return

            # Collect checkboxes
            for region in self.dimensions.get("regions", []):
                cb = self.query_one(f"#region_{region}", Checkbox)
                if cb.value:
                    self.constraint_set.selected_regions.append(region)

            for cat in self.dimensions.get("categories", []):
                cb = self.query_one(f"#cat_{cat}", Checkbox)
                if cb.value:
                    self.constraint_set.selected_categories.append(cat)

            custom = self.query_one("#custom-constraint", Input).value
            if custom:
                self.constraint_set.custom_constraints.append(custom)

            self.callback(self.constraint_set)
            self.dismiss()
        elif event.button.id == "cancel-btn":
            self.dismiss()
```

#### Task 9.3: Approval Shortcut System
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/orchestrator/bi_agent_console.py`

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 9.3.1 | Add keyboard shortcuts for approval | `Y` = approve, `N` = reject, `E` = edit |
| 9.3.2 | Quick approval mode | Skip confirmation dialogs with Shift+Y |
| 9.3.3 | Batch approval | Select multiple items and approve all |
| 9.3.4 | Approval audit log | Save all approval decisions with timestamps |

---

## 5. Phase 4: Report Assembly (Steps 10-12)

### Step 10: Optimal Query Generation (최적 쿼리 생성)

**Objective:** Auto-generate SQL for hypothesis validation, with self-healing error correction.

#### Task 10.1: Enhanced SQL Generator
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/data_source/sql_generator.py`

**Current State:** Basic `SQLGenerator` exists with LLM-based generation.

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 10.1.1 | Add DB dialect validation | Check SQL syntax against target DB (SQLite, Postgres, MySQL) |
| 10.1.2 | Column existence validation | Verify all referenced columns exist in schema |
| 10.1.3 | Query cost estimation | Estimate row scans, warn for expensive queries (> 100,000 rows) |
| 10.1.4 | Query explanation | Generate Korean explanation of what query does |

#### Task 10.2: Self-Healing Query Loop
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/data_source/query_healer.py` (NEW)

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 10.2.1 | Capture execution errors | Parse error messages from DB |
| 10.2.2 | LLM analyzes error and suggests fix | "Column 'salse' not found -> Did you mean 'sales'?" |
| 10.2.3 | Auto-apply fix and retry | Max 3 retry attempts |
| 10.2.4 | Log all healing attempts | Save to `logs/query_healing.jsonl` |

**LLM Prompt Template for Task 10.2.2 (SQL Healing):**
```python
SQL_HEALING_PROMPT = """You are a SQL debugging expert. Analyze the following SQL error and suggest a fix.

**Original SQL:**
```sql
{original_sql}
```

**Error Message:**
{error_message}

**Database Schema:**
{schema_json}

**Database Type:** {db_type}

**Task:**
1. Identify the cause of the error
2. Check column names against the schema - suggest corrections for typos
3. Check table names against the schema
4. Verify SQL syntax for the specific database type
5. Provide a corrected SQL query

**Common Error Patterns:**
- "no such column: X" -> Check for typos, suggest closest match from schema
- "no such table: X" -> Check for typos in table name
- "syntax error" -> Check SQL syntax for {db_type}
- "ambiguous column" -> Add table alias prefix

Return JSON:
{{
    "error_type": "column_not_found|table_not_found|syntax_error|ambiguous_column|other",
    "diagnosis_ko": "오류 원인 설명 (한국어)",
    "suggested_fix_ko": "수정 제안 (한국어)",
    "corrected_sql": "SELECT ... (수정된 SQL)",
    "confidence": 0.95,
    "similar_columns": ["sales", "sale_amount"]
}}

Return ONLY the JSON, no additional text."""
```

**Flow:**
```
Execute Query -> Error? -> Parse Error -> LLM Fix -> Retry (max 3) -> Success/Fail
```

#### Task 10.3: Pandas Transformation Generator
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/data_source/pandas_generator.py` (NEW)

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 10.3.1 | Generate pandas code for complex ops | When SQL can't express the transformation |
| 10.3.2 | LLM generates python code | Safe subset: pandas, numpy, no file I/O |
| 10.3.3 | Sandboxed execution | Execute in restricted environment |
| 10.3.4 | Code review before execution | Show generated code, require user approval |

---

### Step 11: Layout Design (레이아웃 디자인)

**Objective:** Auto-recommend charts, apply premium themes, and calculate optimal layouts.

#### Task 11.1: Chart Recommendation Engine
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/chart_recommender.py` (NEW)

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 11.1.1 | Detect data characteristics | Time series, distribution, correlation, comparison |
| 11.1.2 | Map characteristics to chart types | Time series -> Line, Distribution -> Histogram |
| 11.1.3 | Rank recommendations | Top 3 chart types with scores and rationale |
| 11.1.4 | Consider hypothesis context | If testing correlation, suggest scatter plot |

**Mapping Table:**
| Data Characteristic | Primary Chart | Secondary Chart |
|---------------------|---------------|-----------------|
| Time Series (1 measure) | Line Chart | Area Chart |
| Time Series (multiple measures) | Multi-line | Stacked Area |
| Categorical Comparison | Bar Chart | Horizontal Bar |
| Distribution | Histogram | Box Plot |
| Part-to-whole | Pie Chart | Treemap |
| Correlation | Scatter Plot | Heatmap |
| Geographic | Map | Choropleth |

#### Task 11.2: Premium Theme Engine Enhancement
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/theme_engine.py`

**Current State:** Two themes exist (premium_dark, corporate_light).

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 11.2.1 | Add 3 more theme palettes | "executive_blue", "nature_green", "sunset_warm" |
| 11.2.2 | Font metadata injection | Font family, size scale, weight mappings |
| 11.2.3 | Responsive layout tokens | Breakpoints for different screen sizes |
| 11.2.4 | Accessibility compliance | WCAG 2.1 color contrast ratios (>= 4.5:1 for normal text) |

#### Task 11.3: Auto Layout Calculator
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/layout_calculator.py` (NEW)

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 11.3.1 | Calculate grid positions | Given N components, arrange in 12-col grid |
| 11.3.2 | Priority-based sizing | KPIs get 2 cols, main chart gets 8-12 cols |
| 11.3.3 | Responsive breakpoints | Different layouts for desktop/tablet/mobile |
| 11.3.4 | Collision detection | No overlapping components |

---

### Step 12: Interaction Injection (인터랙션 주입)

**Objective:** Generate varList/eventList JSON for filters, drill-down, and cross-filtering.

#### Task 12.1: VarList/EventList Generator
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/interaction_logic.py`

**Current State:** Basic `suggest_configuration()` exists.

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 12.1.1 | Generate global filter variables | Date range, category selects linked to all charts |
| 12.1.2 | Generate cross-filter events | Click on bar chart filters other charts |
| 12.1.3 | Parameter binding syntax | `{{v_date_start}}` placeholders in queries |
| 12.1.4 | Export as standalone JSON | `varList.json`, `eventList.json` files |

#### Task 12.2: Drill-Down Logic Mapping
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/drilldown_mapper.py` (NEW)

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 12.2.1 | Define drill-down hierarchies | Year -> Quarter -> Month -> Day |
| 12.2.2 | Auto-detect hierarchies from data | Columns like `year`, `month` form hierarchy |
| 12.2.3 | Generate drill-down events | Click on "2024" shows Q1-Q4 breakdown |
| 12.2.4 | Breadcrumb navigation | "All > 2024 > Q1" with back navigation |

#### Task 12.3: Custom Variable Widgets
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/orchestrator/components/filter_widgets.py` (NEW)

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 12.3.1 | Slider widget for numeric ranges | Min/max values, step size |
| 12.3.2 | Multi-select dropdown | Select multiple categories |
| 12.3.3 | Date picker with presets | "Last 7 days", "This month", "Custom range" |
| 12.3.4 | Search-enabled dropdown | Type to filter long option lists |

---

## 6. Phase 5: Review & Export (Steps 13-15)

### Step 13: Draft Briefing (초안 브리핑)

**Objective:** LLM generates Korean summary, local web preview, and ASCII KPI cards.

#### Task 13.1: Analysis Summary Generator
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/summary_generator.py` (NEW)

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 13.1.1 | LLM generates Korean executive summary | 3-5 paragraphs summarizing findings |
| 13.1.2 | Key insight extraction | Bullet points of top 3-5 insights |
| 13.1.3 | Hypothesis validation results | "가설 1: 확인됨 (95% 신뢰도)" |
| 13.1.4 | Action recommendations | "권고사항: 주말 프로모션 강화 필요" |

#### Task 13.2: Local Web Preview Server
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/utils/preview_server.py` (NEW)

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 13.2.1 | Start local HTTP server | Flask on `localhost:5000` (requires `flask`) |
| 13.2.2 | Serve generated HTML dashboard | `/preview/{report_id}` endpoint |
| 13.2.3 | Auto-open in browser | `webbrowser.open()` on preview generation |
| 13.2.4 | Hot reload on changes | Re-serve updated dashboard without restart |

#### Task 13.3: ASCII KPI Cards in TUI
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/orchestrator/components/ascii_kpi.py` (NEW)

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 13.3.1 | Create `ASCIIKPICard` widget | Displays metric value with label |
| 13.3.2 | Trend indicator | ▲ +5% or ▼ -3% with color coding |
| 13.3.3 | Sparkline visualization | Mini ASCII chart: `▁▂▃▄▅▆▇█` |
| 13.3.4 | Grid layout for multiple KPIs | 4 KPIs in a row |

**Example Output:**
```
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   Total Sales   │ │  Avg Order Val  │ │   New Customers │
│   ₩2,340,000    │ │     ₩45,000     │ │      1,234      │
│   ▲ +12.5%      │ │   ▼ -2.3%       │ │   ▲ +8.7%       │
│ ▁▂▃▄▅▆▇█▇▆     │ │ ▅▅▄▄▃▃▂▂▁▁     │ │ ▁▂▂▃▄▅▆▇▇█     │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

### Step 14: Iterative Refinement (반복적 교정)

**Objective:** Real-time modification commands, auto-linting, and proactive question generation.

#### Task 14.1: Refinement Command Loop
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/orchestrator/refinement_handler.py` (NEW)

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 14.1.1 | Parse modification commands | "차트 바꿔줘" -> chart type change |
| 14.1.2 | Apply changes in-memory | Update dashboard JSON without regenerating |
| 14.1.3 | Undo/Redo support | Ctrl+Z / Ctrl+Y to revert changes |
| 14.1.4 | Change history log | Track all modifications with timestamps |

**Command Examples:**
| User Command | Action |
|--------------|--------|
| "차트를 파이 차트로 바꿔줘" | Change chart type to pie |
| "필터 추가해줘: 서울만" | Add filter condition |
| "색상을 파란색으로" | Change color scheme |
| "제목을 '월별 매출 추이'로" | Update chart title |

#### Task 14.2: Report Linting
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/report_linter.py` (NEW)

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 14.2.1 | Check visual clarity | Font size >= 12px, contrast ratio >= 4.5:1 |
| 14.2.2 | Check data accuracy | All referenced columns exist, no null aggregations |
| 14.2.3 | Check consistency | All charts use same date range, consistent labels |
| 14.2.4 | Generate lint report | List of warnings with fix suggestions |

#### Task 14.3: Proactive Question Generator
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/proactive_questions.py` (NEW)

**Current State:** Basic implementation in `collaborative_orchestrator.py` (`_generate_proactive_questions`).

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 14.3.1 | Move to dedicated module | Clean separation of concerns |
| 14.3.2 | Context-aware questions | Based on analysis results, not just schema |
| 14.3.3 | Actionable format | Each question includes expected value |
| 14.3.4 | Priority ranking | High (score >= 0.8) / Medium (0.5-0.79) / Low (< 0.5) impact questions with numeric scores |

---

### Step 15: Final Export (최종 출력 및 배포)

**Objective:** Build final JSON with validation and package to output folder.

**NOTE:** Tableau .twb export is DEFERRED to a future phase. This MVP focuses on InHouse JSON format.

#### Task 15.1: Final JSON Build & Validation
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/agents/bi_tool/json_validator.py` (NEW)

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 15.1.1 | JSON Schema validation | Validate against InHouse schema (see below) |
| 15.1.2 | Reference integrity check | All datamodel IDs referenced in report exist |
| 15.1.3 | Parameter completeness check | All `{{param}}` have corresponding varList entries |
| 15.1.4 | Generate validation report | Pass/Fail with detailed error messages |

**InHouse JSON Schema (from `suwon_pop.json` pattern):**
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "InHouse BI Dashboard Schema",
  "type": "object",
  "required": ["connector", "datamodel", "report"],
  "properties": {
    "connector": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "type", "config"],
        "properties": {
          "id": {"type": "string"},
          "type": {"type": "string", "enum": ["postgres", "mysql", "sqlite", "duckdb"]},
          "config": {
            "type": "object",
            "properties": {
              "host": {"type": "string"},
              "port": {"type": "string"},
              "database": {"type": "string"}
            }
          }
        }
      }
    },
    "datamodel": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "name", "connector_id", "dataset"],
        "properties": {
          "id": {"type": "string", "pattern": "^dm-"},
          "name": {"type": "string"},
          "connector_id": {"type": "string"},
          "dataset": {
            "type": "object",
            "required": ["query"],
            "properties": {
              "query": {"type": "string"},
              "rendered_query": {"type": "string"},
              "parameters": {"type": "object"}
            }
          }
        }
      }
    },
    "report": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "name", "visual"],
        "properties": {
          "id": {"type": "string", "pattern": "^report-"},
          "name": {"type": "string"},
          "visual": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["id", "type"],
              "properties": {
                "id": {"type": "string"},
                "type": {"type": "string", "enum": ["bar", "line", "pie", "table", "scatter", "area", "kpi"]},
                "datamodel_id": {"type": "string"},
                "style": {"type": "object"}
              }
            }
          },
          "varList": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["id", "name", "type"],
              "properties": {
                "id": {"type": "string", "pattern": "^var-"},
                "name": {"type": "string"},
                "type": {"type": "string"},
                "value": {"type": "string"}
              }
            }
          },
          "eventList": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["eventType", "fromId", "toId"],
              "properties": {
                "eventType": {"type": "string"},
                "fromId": {"type": "string"},
                "toId": {"type": "string"}
              }
            }
          }
        }
      }
    }
  }
}
```

#### Task 15.2: Output Packager Enhancement
**File:** `/Users/zokr/python_workspace/BI-Agent/backend/utils/output_packager.py`

**Current State:** Basic packaging with HTML, JSON, README.

**Implementation Tasks:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| 15.2.1 | Add Excel export | Export data tables as .xlsx (requires `openpyxl`) |
| 15.2.2 | Add PDF report | Generate PDF from HTML using weasyprint (requires `weasyprint`) |
| 15.2.3 | Zip package option | Create .zip archive with all files |
| 15.2.4 | TUI file browser | Navigate output folder, open files |

**Final Package Structure:**
```
output/
├── {project_name}/
│   ├── packages/
│   │   └── {analysis_name}/
│   │       ├── INSIGHTS.md
│   │       ├── dashboard.html
│   │       ├── data.json
│   │       ├── data_export.xlsx
│   │       └── report.pdf
│   └── dashboards/
│       └── report_{table}.html
```

---

## 7. Cross-Cutting Concerns

### 7.1 Error Handling & Logging

| Task | File | Acceptance Criteria |
|------|------|---------------------|
| Structured logging | `backend/utils/logger_setup.py` | All logs include `timestamp`, `level`, `agent`, `action` |
| Error recovery | All orchestrators | Graceful degradation with user notification |
| Debug mode | `bi_agent_console.py` | `/debug` command toggles verbose logging |

### 7.2 Testing Requirements

| Phase | Test Type | Coverage Target | Measurement |
|-------|-----------|-----------------|-------------|
| Phase 2 | Unit tests for parsers | 90% for `nl_intent_parser.py`, `table_recommender.py` | `pytest --cov=backend/agents --cov-report=term-missing` |
| Phase 3 | Integration tests | Pipeline generation end-to-end | Measured via `pytest-cov` |
| Phase 4 | UI tests | Textual widget interactions | Textual's test framework |
| Phase 5 | E2E tests | Full flow from `/intent` to export | Manual + integration tests |

**Coverage Measurement:**
```bash
# Install pytest-cov
pip install pytest-cov

# Run with coverage
pytest --cov=backend --cov-report=html --cov-fail-under=90 tests/

# View report
open htmlcov/index.html
```

### 7.3 Performance Targets

| Operation | Max Duration | Mitigation |
|-----------|--------------|------------|
| Intent parsing | 3 seconds | Async LLM calls with timeout |
| Schema scanning | 10 seconds | Cache results, background refresh |
| Query execution | 30 seconds | Progress indicator, cancel option |
| Dashboard generation | 5 seconds | Template caching |

### 7.4 Korean/English Mixed Input Handling

**Guideline for UI Components:**

| Component | Handling |
|-----------|----------|
| Intent parsing | LLM prompt includes Korean-English mapping (see Task 4.2.2 prompt) |
| Field labels | Display Korean with English in parentheses: "매출 (sales)" |
| Error messages | Korean primary, English technical details |
| Tab completion | Support both Korean and romanized input: "mae-chul" -> "매출" |

---

## 8. Commit Strategy

| Phase | Branch | Commits |
|-------|--------|---------|
| Section 0 (Foundation) | `feature/base-intent-refactor` | 1 commit: BaseIntent + ChartIntent refactor + AnalysisIntent |
| Phase 2 (Steps 4-6) | `feature/phase2-intent-scanning` | 1 commit per task (4.1-4.3, 5.1-5.3, 6.1-6.3) |
| Phase 3 (Steps 7-9) | `feature/phase3-planning-alignment` | 1 commit per step |
| Phase 4 (Steps 10-12) | `feature/phase4-report-assembly` | 1 commit per step |
| Phase 5 (Steps 13-15) | `feature/phase5-preview-export` | 1 commit per step |

---

## 9. New Dependencies

The following packages must be added to `pyproject.toml`:

| Package | Version | Purpose | Required By |
|---------|---------|---------|-------------|
| `flask` | `>=2.3.0` | Local preview server | Task 13.2 |
| `openpyxl` | `>=3.1.0` | Excel export | Task 15.2.1 |
| `weasyprint` | `>=60.0` | PDF generation | Task 15.2.2 |
| `pyperclip` | `>=1.8.0` | Clipboard support | Task 6.2.4 |
| `pytest-cov` | `>=4.1.0` | Test coverage measurement | Section 7.2 |
| `jsonschema` | `>=4.20.0` | JSON validation | Task 15.1.1 |

**Updated pyproject.toml dependencies section:**
```toml
dependencies = [
    "textual>=0.47.1",
    "google-generativeai",
    "pandas",
    "duckdb",
    "plotly",
    "httpx",
    "rich",
    "python-dotenv",
    "google-auth",
    "google-auth-oauthlib",
    "anthropic",
    "openai",
    "mcp",
    # New dependencies for Phase 2-5
    "flask>=2.3.0",
    "openpyxl>=3.1.0",
    "weasyprint>=60.0",
    "pyperclip>=1.8.0",
    "jsonschema>=4.20.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.1.0",
    "pytest-asyncio>=0.21.0",
]
```

**Installation:**
```bash
pip install -e ".[dev]"
```

---

## 10. Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| LLM rate limiting | High | Medium | Implement aggressive caching, local fallback |
| Schema mismatch | Medium | High | Validation at each stage, user confirmation |
| TUI responsiveness | Medium | Medium | Async workers, progress indicators |
| weasyprint installation issues | Medium | Low | PDF export is optional, graceful degradation |
| Korean encoding issues | Low | Medium | Ensure UTF-8 everywhere, test with Korean data |

**Tableau Export Deferral Note:**
Tableau .twb export has been deferred to a future phase due to:
1. Complex XML structure requiring extensive testing
2. Tableau Desktop required for validation
3. Not blocking for MVP use cases

Alternative for Tableau users: Export data as CSV with a Tableau connection guide.

---

## 11. Success Criteria

### Section 0 Complete When:
- [ ] `BaseIntent` abstract class exists in `base_intent.py`
- [ ] `ChartIntent` extends `BaseIntent` and all existing tests pass
- [ ] `AnalysisIntent` exists with `produces_charts()` method
- [ ] Unit tests achieve >= 90% coverage for intent classes

### Phase 2 Complete When:
- [ ] `/intent "매출 분석"` returns structured `AnalysisIntent`
- [ ] Table recommendation shows top 3 tables with scores (0-100)
- [ ] Profile includes all statistical fields (missing_pct, quantiles, etc.)

### Phase 3 Complete When:
- [ ] Pipeline generator creates 5-step analysis plan
- [ ] ThinkingPanel shows real-time agent messages via AgentMessageBus
- [ ] HypothesisScreen allows selection and editing

### Phase 4 Complete When:
- [ ] SQL generator validates against schema
- [ ] Query healer successfully fixes typo errors in >= 80% of cases
- [ ] Chart recommender suggests correct chart for time series data
- [ ] VarList/EventList JSON generates working cross-filters

### Phase 5 Complete When:
- [ ] Korean executive summary is coherent and actionable
- [ ] Output package contains HTML, JSON, Excel, and PDF
- [ ] JSON validates against InHouse schema
- [ ] All files accessible via TUI file browser

---

## Appendix A: File Creation Summary

### New Files to Create:

| Path | Purpose |
|------|---------|
| `backend/agents/bi_tool/base_intent.py` | Abstract base class for intents |
| `backend/agents/bi_tool/analysis_intent.py` | AnalysisIntent implementation |
| `backend/agents/data_source/table_recommender.py` | LLM-based table recommendation |
| `backend/agents/data_source/erd_analyzer.py` | ERD relationship inference |
| `backend/agents/data_source/type_corrector.py` | Data type auto-correction |
| `backend/agents/data_source/query_healer.py` | Self-healing query loop |
| `backend/agents/data_source/pandas_generator.py` | Pandas code generation |
| `backend/agents/bi_tool/pipeline_generator.py` | Analysis pipeline generation |
| `backend/agents/bi_tool/hypothesis_templates.py` | Industry hypothesis templates |
| `backend/agents/bi_tool/roi_simulator.py` | ROI simulation preview |
| `backend/agents/bi_tool/chart_recommender.py` | Data-to-chart mapping |
| `backend/agents/bi_tool/layout_calculator.py` | Auto layout grid calculation |
| `backend/agents/bi_tool/drilldown_mapper.py` | Drill-down hierarchy mapping |
| `backend/agents/bi_tool/summary_generator.py` | Korean summary generation |
| `backend/agents/bi_tool/report_linter.py` | Report quality linting |
| `backend/agents/bi_tool/proactive_questions.py` | Proactive question generation |
| `backend/agents/bi_tool/json_validator.py` | JSON schema validation |
| `backend/orchestrator/agent_message_bus.py` | Agent pub/sub messaging (asyncio.Queue) |
| `backend/orchestrator/thinking_translator.py` | LLM thinking stage translator |
| `backend/orchestrator/refinement_handler.py` | Refinement command handler |
| `backend/orchestrator/screens/hypothesis_screen.py` | Hypothesis selection UI |
| `backend/orchestrator/screens/constraint_screen.py` | Constraint input UI |
| `backend/orchestrator/components/data_grid.py` | Sample data grid widget |
| `backend/orchestrator/components/filter_widgets.py` | Custom filter widgets |
| `backend/orchestrator/components/ascii_kpi.py` | ASCII KPI cards |
| `backend/utils/preview_server.py` | Local web preview server |
| `tests/test_intents.py` | Unit tests for intent classes |

### Files to Modify:

| Path | Changes |
|------|---------|
| `backend/orchestrator/bi_agent_console.py` | Command enhancements, new screen integrations |
| `backend/orchestrator/message_components.py` | ThinkingPanel real-time updates |
| `backend/orchestrator/collaborative_orchestrator.py` | Integration with new modules |
| `backend/agents/data_source/profiler.py` | Enhanced statistics |
| `backend/agents/data_source/sql_generator.py` | Validation and explanation |
| `backend/agents/bi_tool/nl_intent_parser.py` | Refactor ChartIntent, add AnalysisIntent parsing |
| `backend/agents/bi_tool/interaction_logic.py` | VarList/EventList generation |
| `backend/agents/bi_tool/theme_engine.py` | New themes, font metadata |
| `backend/utils/output_packager.py` | Enhanced packaging options |
| `pyproject.toml` | Add new dependencies |

---

**PLAN_READY: .omc/plans/bi-agent-detailed-implementation.md**
