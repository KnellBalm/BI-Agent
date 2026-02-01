#!/usr/bin/env python3
"""
Example usage of PipelineGenerator

This script demonstrates how to use the PipelineGenerator to create
analysis pipelines from high-level intents.
"""

import asyncio
import json
from pathlib import Path

from backend.agents.bi_tool.pipeline_generator import PipelineGenerator
from backend.agents.bi_tool.analysis_intent import AnalysisIntent
from backend.orchestrator.llm_provider import GeminiProvider


async def main():
    """Demonstrate pipeline generation workflow."""

    # 1. Set up mock schema
    schema = {
        "tables": {
            "sales": {
                "columns": [
                    {"name": "sale_id", "type": "INTEGER"},
                    {"name": "product_name", "type": "VARCHAR"},
                    {"name": "amount", "type": "DECIMAL"},
                    {"name": "quantity", "type": "INTEGER"},
                    {"name": "sale_date", "type": "DATE"},
                    {"name": "region", "type": "VARCHAR"}
                ]
            },
            "customers": {
                "columns": [
                    {"name": "customer_id", "type": "INTEGER"},
                    {"name": "name", "type": "VARCHAR"},
                    {"name": "region", "type": "VARCHAR"},
                    {"name": "signup_date", "type": "DATE"}
                ]
            }
        }
    }

    # 2. Create AnalysisIntent
    intent = AnalysisIntent(
        purpose="trend",
        target_metrics=["월별 매출액", "거래 건수"],
        datasource="sales",
        hypothesis="최근 3개월간 매출이 증가 추세를 보인다",
        constraints=["2024년 데이터만 사용", "서울 지역 한정"],
        kpis=["총 매출액", "평균 거래 금액"]
    )

    print("=" * 70)
    print("BI-Agent Pipeline Generator - Example Usage")
    print("=" * 70)
    print(f"\nAnalysis Intent:")
    print(f"  Purpose: {intent.purpose}")
    print(f"  Target Metrics: {intent.target_metrics}")
    print(f"  Hypothesis: {intent.hypothesis}")
    print(f"  Constraints: {intent.constraints}")

    # 3. Initialize LLM provider
    print("\n" + "=" * 70)
    print("Initializing LLM Provider...")
    print("=" * 70)

    try:
        llm = GeminiProvider()
        print("✓ LLM Provider initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize LLM: {e}")
        print("\nNote: This example requires a valid GEMINI_API_KEY in .env")
        print("For testing purposes, you can use the mock LLM from tests.")
        return

    # 4. Create PipelineGenerator
    generator = PipelineGenerator(llm=llm, schema=schema)
    print(f"✓ PipelineGenerator initialized")
    print(f"  Pipelines directory: {generator.pipelines_dir}")

    # 5. Generate pipeline
    print("\n" + "=" * 70)
    print("Generating Analysis Pipeline...")
    print("=" * 70)

    try:
        pipeline = await generator.generate_pipeline(
            intent=intent,
            selected_tables=["sales"]
        )

        print(f"\n✓ Pipeline generated successfully!")
        print(f"\nPipeline Details:")
        print(f"  Name: {pipeline.pipeline_name}")
        print(f"  Total Steps: {len(pipeline.steps)}")
        print(f"  Estimated Duration: {pipeline.estimated_total_seconds}s")
        print(f"  Required Data: {pipeline.required_data}")
        print(f"  Expected Outputs: {pipeline.expected_outputs}")

        # 6. Display pipeline steps
        print("\n" + "=" * 70)
        print("Pipeline Steps:")
        print("=" * 70)

        for i, step in enumerate(pipeline.steps, 1):
            print(f"\nStep {i}: {step.step_id}")
            print(f"  Action: {step.action}")
            print(f"  Agent: {step.agent}")
            print(f"  Description: {step.description_ko}")
            print(f"  Input: {step.input_data}")
            print(f"  Output: {step.output_data}")
            print(f"  Duration: {step.estimated_seconds}s")
            if step.dependencies:
                print(f"  Depends on: {step.dependencies}")

        # 7. Validate pipeline
        print("\n" + "=" * 70)
        print("Validating Pipeline...")
        print("=" * 70)

        is_valid, errors = generator.validate_pipeline(pipeline)
        if is_valid:
            print("✓ Pipeline validation passed")
        else:
            print("✗ Pipeline validation failed:")
            for error in errors:
                print(f"  - {error}")

        # 8. Save pipeline
        print("\n" + "=" * 70)
        print("Saving Pipeline...")
        print("=" * 70)

        pipeline_path = generator.pipelines_dir / "example_pipeline.json"
        pipeline.save(pipeline_path)
        print(f"✓ Pipeline saved to: {pipeline_path}")

        # 9. List saved pipelines
        print("\n" + "=" * 70)
        print("Saved Pipelines:")
        print("=" * 70)

        saved_pipelines = generator.list_saved_pipelines()
        for name in saved_pipelines:
            print(f"  - {name}")

        # 10. Load and verify
        print("\n" + "=" * 70)
        print("Loading Pipeline...")
        print("=" * 70)

        loaded_pipeline = generator.load_pipeline("example_pipeline")
        print(f"✓ Pipeline loaded: {loaded_pipeline.pipeline_name}")
        print(f"  Steps: {len(loaded_pipeline.steps)}")

        print("\n" + "=" * 70)
        print("Example completed successfully!")
        print("=" * 70)

    except Exception as e:
        print(f"\n✗ Error during pipeline generation: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
