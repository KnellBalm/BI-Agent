"""
Natural Language Intent Parser for BI Chart Generation
Converts Korean/English natural language requests into structured chart intents.
"""

import json
import asyncio
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from backend.orchestrator.llm_provider import GeminiProvider, OllamaProvider, FailoverLLMProvider


@dataclass
class ChartIntent:
    """
    Structured representation of a chart creation/modification intent

    Attributes:
        action: Type of action - "create", "modify", "delete"
        visual_type: Chart type - "bar", "line", "pie", "table", "scatter", "area"
        datasource: Data source identifier (table name, dataset name, etc.)
        dimensions: List of dimension fields (categories, x-axis, grouping)
        measures: List of measure fields (metrics, y-axis, aggregations)
        filters: List of filter conditions as dicts with keys: field, operator, value
        title: Optional chart title
        aggregation: Optional aggregation type - "sum", "avg", "count", "min", "max"
        time_period: Optional time period specification - "daily", "weekly", "monthly", "yearly"
    """
    action: str
    visual_type: str
    datasource: str
    dimensions: List[str]
    measures: List[str]
    filters: List[Dict[str, Any]]
    title: Optional[str] = None
    aggregation: Optional[str] = None
    time_period: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return asdict(self)

    def validate(self) -> bool:
        """Validate the intent structure"""
        if self.action not in ["create", "modify", "delete"]:
            return False
        if self.visual_type not in ["bar", "line", "pie", "table", "scatter", "area"]:
            return False
        if not self.datasource:
            return False
        if self.action in ["create", "modify"] and not (self.dimensions or self.measures):
            return False
        return True


class NLIntentParser:
    """
    Parses natural language input into structured ChartIntent objects
    using LLM with Gemini/Ollama failover
    """

    PROMPT_TEMPLATE = """You are a BI chart intent parser. Parse the following natural language request into a structured JSON format.

The user's request is in Korean or English. Extract the following information:

1. **action**: What action to perform - "create", "modify", or "delete"
2. **visual_type**: Type of visualization - "bar", "line", "pie", "table", "scatter", or "area"
3. **datasource**: The data source or table name (infer if not explicit, use "sales", "orders", "customers" as defaults)
4. **dimensions**: List of dimension fields (categories, grouping fields, x-axis)
5. **measures**: List of measure fields (metrics, values, y-axis)
6. **filters**: List of filter conditions as objects with "field", "operator", "value"
7. **title**: Chart title (extract or generate based on request)
8. **aggregation**: Aggregation type - "sum", "avg", "count", "min", "max" (if mentioned)
9. **time_period**: Time period - "daily", "weekly", "monthly", "yearly" (if mentioned)

**Korean to English field mapping:**
- 매출/판매액 = sales
- 주문 = orders
- 고객 = customer
- 월/월별 = month
- 일/일별 = day
- 년/년도/연도 = year
- 분기 = quarter
- 지역 = region
- 카테고리/범주 = category
- 제품/상품 = product
- 수량 = quantity
- 금액 = amount

**Visual type mapping:**
- 바 차트/막대 차트/바차트 = bar
- 라인 차트/선 차트/추이 = line
- 파이 차트/원 차트 = pie
- 테이블/표 = table
- 스캐터/산점도 = scatter
- 영역 차트/면적 차트 = area

User Request: "{user_input}"

Response MUST be valid JSON in this exact format:
{{
    "action": "create|modify|delete",
    "visual_type": "bar|line|pie|table|scatter|area",
    "datasource": "table_name",
    "dimensions": ["field1", "field2"],
    "measures": ["field3", "field4"],
    "filters": [{{"field": "region", "operator": "=", "value": "Seoul"}}],
    "title": "Chart Title",
    "aggregation": "sum|avg|count|min|max",
    "time_period": "daily|weekly|monthly|yearly"
}}

Return ONLY the JSON, no additional text or explanation."""

    def __init__(self, llm_provider: Optional[FailoverLLMProvider] = None):
        """
        Initialize the intent parser with LLM provider

        Args:
            llm_provider: Optional LLM provider, defaults to Gemini with Ollama failover
        """
        if llm_provider is None:
            # Setup default failover: Gemini with QuotaManager -> Ollama
            from backend.orchestrator.quota_manager import QuotaManager
            qm = QuotaManager()
            primary = GeminiProvider(quota_manager=qm)
            secondary = OllamaProvider()
            self.llm = FailoverLLMProvider(primary, secondary)
        else:
            self.llm = llm_provider

    async def parse_intent(self, user_input: str) -> ChartIntent:
        """
        Parse natural language input into structured ChartIntent

        Args:
            user_input: Natural language request in Korean or English

        Returns:
            ChartIntent object with parsed structure

        Raises:
            ValueError: If parsing fails or LLM returns invalid format
            RuntimeError: If LLM service is unavailable
        """
        if not user_input or not user_input.strip():
            raise ValueError("Empty input provided")

        # Generate prompt
        prompt = self.PROMPT_TEMPLATE.format(user_input=user_input.strip())

        try:
            # Call LLM
            response = await self.llm.generate(prompt)

            # Clean response (remove markdown code blocks if present)
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            # Parse JSON
            parsed_data = json.loads(cleaned)

            # Create ChartIntent object with defaults
            intent = ChartIntent(
                action=parsed_data.get("action", "create"),
                visual_type=parsed_data.get("visual_type", "bar"),
                datasource=parsed_data.get("datasource", "unknown"),
                dimensions=parsed_data.get("dimensions", []),
                measures=parsed_data.get("measures", []),
                filters=parsed_data.get("filters", []),
                title=parsed_data.get("title"),
                aggregation=parsed_data.get("aggregation"),
                time_period=parsed_data.get("time_period")
            )

            # Validate
            if not intent.validate():
                raise ValueError(f"Invalid intent structure: {intent}")

            return intent

        except json.JSONDecodeError as e:
            raise ValueError(f"LLM returned invalid JSON: {response}") from e
        except Exception as e:
            if "failed" in str(e).lower():
                raise RuntimeError(f"LLM service unavailable: {e}") from e
            raise ValueError(f"Failed to parse intent: {e}") from e

    def parse_intent_sync(self, user_input: str) -> ChartIntent:
        """
        Synchronous wrapper for parse_intent

        Args:
            user_input: Natural language request

        Returns:
            ChartIntent object
        """
        return asyncio.run(self.parse_intent(user_input))


# Convenience function for quick usage
async def parse_chart_intent(user_input: str) -> ChartIntent:
    """
    Quick parse function with default LLM setup

    Args:
        user_input: Natural language chart request

    Returns:
        Parsed ChartIntent object

    Example:
        >>> intent = await parse_chart_intent("월별 매출 추이를 보여주는 라인 차트를 만들어줘")
        >>> print(intent.visual_type)  # "line"
        >>> print(intent.dimensions)   # ["month"]
        >>> print(intent.measures)     # ["sales"]
    """
    parser = NLIntentParser()
    return await parser.parse_intent(user_input)
