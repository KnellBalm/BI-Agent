# /backend/agents/bi_tool/pipeline_generator.py
"""
Pipeline Generator for BI-Agent

Generates multi-step analysis pipelines from high-level AnalysisIntent objects.
Each pipeline consists of 3-7 concrete steps executed by specialized agents.
"""

import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from backend.orchestrator import LLMProvider
from backend.agents.bi_tool.analysis_intent import AnalysisIntent
from backend.utils.logger_setup import setup_logger

logger = setup_logger("pipeline_generator", "pipeline_generator.log")

# LLM Prompt Template for Pipeline Generation
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
        }}
    ]
}}

JSON만 반환하고 다른 텍스트는 생략하십시오."""


@dataclass
class PipelineStep:
    """단일 파이프라인 스텝의 구조화된 표현."""
    step_id: str
    action: str  # "profile", "query", "transform", "visualize", "insight"
    description_ko: str  # Korean description
    agent: str  # "DataMaster", "Strategist", "Designer"
    input_data: List[str]
    output_data: str
    estimated_seconds: int
    dependencies: List[str] = field(default_factory=list)  # step_ids that must complete first

    def validate(self) -> bool:
        """Validate step structure and constraints."""
        # Validate action
        valid_actions = ["profile", "query", "transform", "visualize", "insight"]
        if self.action not in valid_actions:
            logger.error(f"Invalid action '{self.action}'. Must be one of {valid_actions}")
            return False

        # Validate agent
        valid_agents = ["DataMaster", "Strategist", "Designer"]
        if self.agent not in valid_agents:
            logger.error(f"Invalid agent '{self.agent}'. Must be one of {valid_agents}")
            return False

        # Validate step_id format
        if not re.match(r"^step_\d+$", self.step_id):
            logger.error(f"Invalid step_id format '{self.step_id}'. Must match 'step_N'")
            return False

        # Validate required fields
        if not self.description_ko or not self.output_data:
            logger.error("Missing required fields: description_ko or output_data")
            return False

        if self.estimated_seconds <= 0:
            logger.error("estimated_seconds must be positive")
            return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)


@dataclass
class AnalysisPipeline:
    """완전한 분석 파이프라인의 구조화된 표현."""
    pipeline_name: str
    steps: List[PipelineStep]
    estimated_total_seconds: int
    required_data: List[str]  # Required tables/data sources
    expected_outputs: List[str]  # Expected output artifacts
    created_at: datetime = field(default_factory=datetime.now)
    intent_id: Optional[str] = None

    def validate(self) -> bool:
        """Validate pipeline structure and check for circular dependencies."""
        # Validate step count
        if not (3 <= len(self.steps) <= 7):
            logger.error(f"Pipeline must have 3-7 steps, got {len(self.steps)}")
            return False

        # Validate all steps
        for step in self.steps:
            if not step.validate():
                logger.error(f"Step validation failed for {step.step_id}")
                return False

        # Check for circular dependencies
        if self._has_circular_dependencies():
            logger.error("Circular dependencies detected in pipeline")
            return False

        # Validate step IDs are unique
        step_ids = [step.step_id for step in self.steps]
        if len(step_ids) != len(set(step_ids)):
            logger.error("Duplicate step_id found in pipeline")
            return False

        # Validate dependencies reference existing steps
        all_step_ids = set(step_ids)
        for step in self.steps:
            for dep_id in step.dependencies:
                if dep_id not in all_step_ids:
                    logger.error(f"Step {step.step_id} references non-existent dependency {dep_id}")
                    return False

        return True

    def _has_circular_dependencies(self) -> bool:
        """Detect circular dependencies in step graph using DFS."""
        # Build adjacency list
        graph = {step.step_id: step.dependencies for step in self.steps}

        visited = set()
        rec_stack = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for step in self.steps:
            if step.step_id not in visited:
                if has_cycle(step.step_id):
                    return True

        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "pipeline_name": self.pipeline_name,
            "steps": [step.to_dict() for step in self.steps],
            "estimated_total_seconds": self.estimated_total_seconds,
            "required_data": self.required_data,
            "expected_outputs": self.expected_outputs,
            "created_at": self.created_at.isoformat(),
            "intent_id": self.intent_id
        }

    def save(self, filepath: Path) -> None:
        """Save pipeline to JSON file."""
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
            logger.info(f"Pipeline saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save pipeline to {filepath}: {e}")
            raise

    @classmethod
    def load(cls, filepath: Path) -> 'AnalysisPipeline':
        """Load pipeline from JSON file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Parse steps
            steps = [PipelineStep(**step_data) for step_data in data["steps"]]

            # Parse datetime
            created_at = datetime.fromisoformat(data["created_at"])

            return cls(
                pipeline_name=data["pipeline_name"],
                steps=steps,
                estimated_total_seconds=data["estimated_total_seconds"],
                required_data=data["required_data"],
                expected_outputs=data["expected_outputs"],
                created_at=created_at,
                intent_id=data.get("intent_id")
            )
        except Exception as e:
            logger.error(f"Failed to load pipeline from {filepath}: {e}")
            raise


class PipelineGenerator:
    """LLM을 사용하여 AnalysisIntent로부터 실행 가능한 파이프라인을 생성합니다."""

    def __init__(self, llm: LLMProvider, schema: Dict[str, Any]):
        """
        Initialize PipelineGenerator.

        Args:
            llm: LLM provider instance for generating pipelines
            schema: Database schema dictionary for validation
        """
        self.llm = llm
        self.schema = schema
        self.pipelines_dir = Path.home() / ".bi-agent" / "pipelines"
        self.pipelines_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"PipelineGenerator initialized with pipelines_dir: {self.pipelines_dir}")

    async def generate_pipeline(
        self,
        intent: AnalysisIntent,
        selected_tables: List[str]
    ) -> AnalysisPipeline:
        """
        Generate an analysis pipeline from intent using LLM.

        Args:
            intent: AnalysisIntent object describing the analysis goal
            selected_tables: List of table names to analyze

        Returns:
            AnalysisPipeline object with validated steps

        Raises:
            ValueError: If pipeline generation or validation fails
        """
        logger.info(f"Generating pipeline for intent: {intent.purpose}")

        # Build prompt
        prompt = PIPELINE_GENERATION_PROMPT.format(
            purpose=intent.purpose,
            target_metrics=", ".join(intent.target_metrics) if intent.target_metrics else "없음",
            hypothesis=intent.hypothesis or "없음",
            selected_tables=", ".join(selected_tables),
            constraints=", ".join(intent.constraints) if intent.constraints else "없음",
            schema_json=json.dumps(self.schema, ensure_ascii=False, indent=2)
        )

        try:
            # Call LLM
            logger.debug(f"Calling LLM with prompt length: {len(prompt)}")
            response = await self.llm.generate(prompt)
            logger.debug(f"LLM response received: {response[:200]}...")

            # Extract JSON from response
            pipeline_data = self._extract_json(response)

            # Validate required fields
            if "pipeline_name" not in pipeline_data or "steps" not in pipeline_data:
                raise ValueError("Missing required fields in LLM response: pipeline_name or steps")

            # Parse steps
            steps = []
            for step_data in pipeline_data["steps"]:
                step = PipelineStep(
                    step_id=step_data["step_id"],
                    action=step_data["action"],
                    description_ko=step_data["description_ko"],
                    agent=step_data["agent"],
                    input_data=step_data["input_data"],
                    output_data=step_data["output_data"],
                    estimated_seconds=step_data["estimated_seconds"],
                    dependencies=step_data.get("dependencies", [])
                )
                steps.append(step)

            # Extract expected outputs from steps
            expected_outputs = [step.output_data for step in steps]

            # Create pipeline object
            pipeline = AnalysisPipeline(
                pipeline_name=pipeline_data["pipeline_name"],
                steps=steps,
                estimated_total_seconds=pipeline_data.get("estimated_total_seconds",
                                                          sum(s.estimated_seconds for s in steps)),
                required_data=selected_tables,
                expected_outputs=expected_outputs,
                intent_id=intent.purpose  # Use purpose as intent ID for now
            )

            # Validate pipeline
            is_valid, errors = self.validate_pipeline(pipeline)
            if not is_valid:
                error_msg = f"Pipeline validation failed: {'; '.join(errors)}"
                logger.error(error_msg)
                raise ValueError(error_msg)

            logger.info(f"Pipeline generated successfully: {pipeline.pipeline_name}")
            return pipeline

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")
        except KeyError as e:
            logger.error(f"Missing required field in pipeline data: {e}")
            raise ValueError(f"Missing required field: {e}")
        except Exception as e:
            logger.error(f"Pipeline generation failed: {e}")
            raise

    def _extract_json(self, response: str) -> Dict[str, Any]:
        """Extract JSON object from LLM response text."""
        # Remove markdown code blocks if present
        response = re.sub(r'```json\s*', '', response)
        response = re.sub(r'```\s*', '', response)

        # Try to find JSON object
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            json_str = match.group(0)
            return json.loads(json_str)
        else:
            # Try parsing the entire response
            return json.loads(response)

    def validate_pipeline(self, pipeline: AnalysisPipeline) -> Tuple[bool, List[str]]:
        """
        Validate pipeline against schema and structural constraints.

        Args:
            pipeline: AnalysisPipeline to validate

        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        errors = []

        # Basic pipeline validation
        if not pipeline.validate():
            errors.append("Pipeline structural validation failed")

        # Check if required tables exist in schema
        if isinstance(self.schema, dict) and "tables" in self.schema:
            available_tables = set(self.schema["tables"].keys())
            for table in pipeline.required_data:
                if table not in available_tables:
                    errors.append(f"Required table '{table}' not found in schema")

        # Validate input_data references in each step
        for step in pipeline.steps:
            for input_ref in step.input_data:
                # Check if input is a table or output from previous step
                is_valid_input = (
                    input_ref in pipeline.required_data or  # It's a table
                    any(s.output_data == input_ref for s in pipeline.steps)  # It's a step output
                )
                if not is_valid_input:
                    errors.append(
                        f"Step {step.step_id} references unknown input '{input_ref}'"
                    )

        # Check for circular dependencies
        if pipeline._has_circular_dependencies():
            errors.append("Circular dependencies detected in pipeline")

        is_valid = len(errors) == 0
        if is_valid:
            logger.info(f"Pipeline '{pipeline.pipeline_name}' validated successfully")
        else:
            logger.warning(f"Pipeline validation errors: {errors}")

        return is_valid, errors

    def _check_circular_dependencies(self, steps: List[PipelineStep]) -> bool:
        """
        Detect circular dependencies in step graph.

        Args:
            steps: List of PipelineStep objects

        Returns:
            True if circular dependency exists, False otherwise
        """
        # Build adjacency list
        graph = {step.step_id: step.dependencies for step in steps}

        visited = set()
        rec_stack = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for step in steps:
            if step.step_id not in visited:
                if has_cycle(step.step_id):
                    logger.warning(f"Circular dependency detected involving {step.step_id}")
                    return True

        return False

    def list_saved_pipelines(self) -> List[str]:
        """
        List all saved pipeline files.

        Returns:
            List of pipeline filenames (without .json extension)
        """
        try:
            pipeline_files = list(self.pipelines_dir.glob("*.json"))
            names = [f.stem for f in pipeline_files]
            logger.info(f"Found {len(names)} saved pipelines")
            return sorted(names)
        except Exception as e:
            logger.error(f"Failed to list pipelines: {e}")
            return []

    def load_pipeline(self, name: str) -> AnalysisPipeline:
        """
        Load pipeline by name from storage.

        Args:
            name: Pipeline name (without .json extension)

        Returns:
            AnalysisPipeline object

        Raises:
            FileNotFoundError: If pipeline file doesn't exist
        """
        filepath = self.pipelines_dir / f"{name}.json"
        if not filepath.exists():
            raise FileNotFoundError(f"Pipeline '{name}' not found at {filepath}")

        logger.info(f"Loading pipeline from {filepath}")
        return AnalysisPipeline.load(filepath)
