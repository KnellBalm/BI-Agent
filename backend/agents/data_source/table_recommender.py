"""
Table Recommender Module
LLM-based table recommendation for BI analysis queries.
Ranks tables by relevance and detects JOIN relationships.
"""

import json
import re
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from backend.agents.bi_tool.analysis_intent import AnalysisIntent
from backend.orchestrator.providers.llm_provider import LLMProvider
from backend.utils.logger_setup import setup_logger

logger = setup_logger("table_recommender", "table_recommender.log")


@dataclass
class TableRecommendation:
    """
    Recommendation for a database table with relevance scoring

    Attributes:
        table_name: Name of the recommended table
        relevance_score: Relevance score from 0-100
        explanation_ko: Korean explanation for why this table is relevant
        relevant_columns: List of column names relevant to the analysis
        join_suggestions: List of potential JOIN relationships
    """
    table_name: str
    relevance_score: int
    explanation_ko: str
    relevant_columns: List[str]
    join_suggestions: List[Dict[str, str]]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return asdict(self)

    def validate(self) -> bool:
        """Validate recommendation structure"""
        if not self.table_name or not isinstance(self.table_name, str):
            return False
        if not (0 <= self.relevance_score <= 100):
            return False
        if not self.explanation_ko or not isinstance(self.explanation_ko, str):
            return False
        if not isinstance(self.relevant_columns, list):
            return False
        if not isinstance(self.join_suggestions, list):
            return False
        return True


@dataclass
class ERDRelationship:
    """
    Entity-Relationship Diagram relationship representation

    Attributes:
        from_table: Source table name
        to_table: Target table name
        from_column: Source column name (FK)
        to_column: Target column name (PK)
        relationship_type: Type of relationship - "one-to-many", "many-to-one", "many-to-many"
    """
    from_table: str
    to_table: str
    from_column: str
    to_column: str
    relationship_type: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return asdict(self)

    def validate(self) -> bool:
        """Validate relationship structure"""
        valid_types = ["one-to-many", "many-to-one", "many-to-many"]
        if self.relationship_type not in valid_types:
            return False
        if not all([self.from_table, self.to_table, self.from_column, self.to_column]):
            return False
        return True


class TableRecommender:
    """
    LLM-based table recommendation engine

    Analyzes database schema and recommends relevant tables for analysis queries
    using semantic understanding and relationship detection.
    """

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

    RELATIONSHIP_INFERENCE_PROMPT = """다음 테이블들 간의 JOIN 관계를 추론하십시오.

**테이블 목록:**
{tables}

**전체 스키마:**
{schema_json}

**과업:**
컬럼명 패턴을 기반으로 테이블 간의 잠재적 관계를 식별하십시오:
- *_id, *ID 패턴으로 끝나는 컬럼은 외래 키일 가능성이 높음
- 테이블명과 매칭되는 컬럼명 (예: customers 테이블의 customer_id)
- 복합 키 관계 감지

다음 형식의 JSON 배열로 반환하십시오:
[
    {{
        "from_table": "orders",
        "to_table": "customers",
        "from_column": "customer_id",
        "to_column": "id",
        "relationship_type": "many-to-one"
    }}
]

JSON 배열만 반환하십시오."""

    def __init__(self, llm: LLMProvider, schema: Dict[str, Any]):
        """
        Initialize table recommender

        Args:
            llm: LLM provider instance
            schema: Database schema metadata
        """
        self.llm = llm
        self.schema = schema
        logger.info(f"TableRecommender initialized with {len(schema.get('tables', []))} tables")

    async def recommend_tables(self, intent: AnalysisIntent) -> List[TableRecommendation]:
        """
        Recommend tables based on analysis intent

        Args:
            intent: Structured analysis intent

        Returns:
            List of TableRecommendation objects sorted by relevance score (descending)

        Raises:
            ValueError: If intent validation fails or LLM returns invalid format
            RuntimeError: If LLM service is unavailable
        """
        if not intent.validate():
            raise ValueError(f"Invalid analysis intent: {intent}")

        logger.info(f"Recommending tables for intent: {intent.title or intent.purpose}")

        try:
            # Prepare schema JSON
            schema_json = json.dumps(self.schema, ensure_ascii=False, indent=2)

            # Format prompt
            prompt = self.TABLE_RECOMMENDATION_PROMPT.format(
                purpose=intent.purpose,
                target_metrics=", ".join(intent.target_metrics),
                hypothesis=intent.hypothesis or "없음",
                filters=json.dumps(intent.filters, ensure_ascii=False) if intent.filters else "없음",
                schema_json=schema_json
            )

            # Call LLM
            response = await self.llm.generate(prompt)
            logger.debug(f"LLM response: {response[:500]}...")

            # Parse JSON response
            cleaned_response = self._clean_json_response(response)
            recommendations_data = json.loads(cleaned_response)

            if not isinstance(recommendations_data, list):
                raise ValueError("LLM response is not a list")

            # Convert to TableRecommendation objects
            recommendations = []
            for rec_data in recommendations_data:
                rec = TableRecommendation(
                    table_name=rec_data.get("table_name", ""),
                    relevance_score=int(rec_data.get("relevance_score", 0)),
                    explanation_ko=rec_data.get("explanation_ko", ""),
                    relevant_columns=rec_data.get("relevant_columns", []),
                    join_suggestions=rec_data.get("join_suggestions", [])
                )

                if rec.validate():
                    recommendations.append(rec)
                    logger.debug(f"Added recommendation: {rec.table_name} (score: {rec.relevance_score})")
                else:
                    logger.warning(f"Invalid recommendation skipped: {rec_data}")

            # Sort by relevance score (descending)
            recommendations.sort(key=lambda x: x.relevance_score, reverse=True)

            logger.info(f"Generated {len(recommendations)} table recommendations")
            return recommendations

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            raise ValueError(f"LLM returned invalid JSON: {response}") from e
        except Exception as e:
            logger.error(f"Table recommendation failed: {e}")
            if "failed" in str(e).lower() or "unavailable" in str(e).lower():
                raise RuntimeError(f"LLM service unavailable: {e}") from e
            raise ValueError(f"Failed to recommend tables: {e}") from e

    async def infer_relationships(self, tables: List[str]) -> List[ERDRelationship]:
        """
        Infer JOIN relationships between tables

        Args:
            tables: List of table names to analyze

        Returns:
            List of ERDRelationship objects representing detected relationships

        Raises:
            ValueError: If tables list is empty or LLM returns invalid format
            RuntimeError: If LLM service is unavailable
        """
        if not tables or len(tables) == 0:
            raise ValueError("Tables list cannot be empty")

        logger.info(f"Inferring relationships for {len(tables)} tables")

        try:
            # Filter schema to only include specified tables
            filtered_schema = {
                "tables": [
                    table for table in self.schema.get("tables", [])
                    if table.get("name") in tables
                ]
            }

            schema_json = json.dumps(filtered_schema, ensure_ascii=False, indent=2)
            tables_str = ", ".join(tables)

            # Format prompt
            prompt = self.RELATIONSHIP_INFERENCE_PROMPT.format(
                tables=tables_str,
                schema_json=schema_json
            )

            # Call LLM
            response = await self.llm.generate(prompt)
            logger.debug(f"LLM relationship response: {response[:500]}...")

            # Parse JSON response
            cleaned_response = self._clean_json_response(response)
            relationships_data = json.loads(cleaned_response)

            if not isinstance(relationships_data, list):
                raise ValueError("LLM response is not a list")

            # Convert to ERDRelationship objects
            relationships = []
            for rel_data in relationships_data:
                rel = ERDRelationship(
                    from_table=rel_data.get("from_table", ""),
                    to_table=rel_data.get("to_table", ""),
                    from_column=rel_data.get("from_column", ""),
                    to_column=rel_data.get("to_column", ""),
                    relationship_type=rel_data.get("relationship_type", "")
                )

                if rel.validate():
                    relationships.append(rel)
                    logger.debug(f"Detected relationship: {rel.from_table}.{rel.from_column} -> {rel.to_table}.{rel.to_column}")
                else:
                    logger.warning(f"Invalid relationship skipped: {rel_data}")

            # Additionally detect relationships using heuristics
            heuristic_relationships = self._detect_relationships_heuristic(tables)

            # Merge LLM and heuristic results (avoid duplicates)
            existing_pairs = {
                (r.from_table, r.from_column, r.to_table, r.to_column)
                for r in relationships
            }

            for heur_rel in heuristic_relationships:
                key = (heur_rel.from_table, heur_rel.from_column, heur_rel.to_table, heur_rel.to_column)
                if key not in existing_pairs:
                    relationships.append(heur_rel)
                    logger.debug(f"Added heuristic relationship: {heur_rel.from_table}.{heur_rel.from_column} -> {heur_rel.to_table}.{heur_rel.to_column}")

            logger.info(f"Inferred {len(relationships)} relationships")
            return relationships

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            raise ValueError(f"LLM returned invalid JSON: {response}") from e
        except Exception as e:
            logger.error(f"Relationship inference failed: {e}")
            if "failed" in str(e).lower() or "unavailable" in str(e).lower():
                raise RuntimeError(f"LLM service unavailable: {e}") from e
            raise ValueError(f"Failed to infer relationships: {e}") from e

    def _detect_relationships_heuristic(self, tables: List[str]) -> List[ERDRelationship]:
        """
        Detect relationships using column naming heuristics

        Looks for patterns like:
        - customer_id, customerId, CustomerID
        - product_id, productId, ProductID
        - Matches against table names

        Args:
            tables: List of table names

        Returns:
            List of ERDRelationship objects
        """
        relationships = []

        # Get table schemas
        table_schemas = {
            table.get("name"): table.get("columns", [])
            for table in self.schema.get("tables", [])
            if table.get("name") in tables
        }

        # Foreign key patterns
        fk_patterns = [
            r"(.+)_id$",  # snake_case: customer_id
            r"(.+)Id$",   # camelCase: customerId
            r"(.+)ID$",   # PascalCase: customerID
        ]

        for from_table, columns in table_schemas.items():
            for column in columns:
                col_name = column.get("name", "")

                # Check if column matches FK pattern
                for pattern in fk_patterns:
                    match = re.match(pattern, col_name)
                    if match:
                        referenced_table = match.group(1)

                        # Check if referenced table exists (case-insensitive)
                        for to_table in tables:
                            if to_table.lower() == referenced_table.lower():
                                # Found a potential FK relationship
                                relationships.append(ERDRelationship(
                                    from_table=from_table,
                                    to_table=to_table,
                                    from_column=col_name,
                                    to_column="id",  # Assume primary key is 'id'
                                    relationship_type="many-to-one"
                                ))
                                break

                            # Also check plural forms (e.g., customers -> customer_id)
                            if to_table.lower() == referenced_table.lower() + "s":
                                relationships.append(ERDRelationship(
                                    from_table=from_table,
                                    to_table=to_table,
                                    from_column=col_name,
                                    to_column="id",
                                    relationship_type="many-to-one"
                                ))
                                break

        return relationships

    def _clean_json_response(self, response: str) -> str:
        """
        Clean LLM response to extract valid JSON

        Removes markdown code blocks and extra whitespace

        Args:
            response: Raw LLM response string

        Returns:
            Cleaned JSON string
        """
        cleaned = response.strip()

        # Remove markdown code blocks
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]

        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        cleaned = cleaned.strip()

        return cleaned
