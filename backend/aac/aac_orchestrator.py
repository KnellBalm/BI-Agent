"""
AaC Orchestrator — plan.md 분석 의도 기반 순차 파이프라인 실행기
AgenticOrchestrator를 step_executor 모드로 래핑하여 무한 재계획 루프를 방지합니다.
"""
from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Any

from backend.aac.plan_parser import AnalysisIntent


class PipelineStep(Enum):
    PROFILE = "profile"
    QUERY = "query"
    TRANSFORM = "transform"
    VISUALIZE = "visualize"
    INSIGHT = "insight"


@dataclass
class PipelineResult:
    step: PipelineStep
    output: str = ""
    success: bool = True
    error: str = ""


class AaCOrchestrator:
    """분석 의도(AnalysisIntent) 기반 순차 파이프라인 실행기.

    PROFILE → QUERY → TRANSFORM → VISUALIZE → INSIGHT 순서로 실행하며,
    각 스텝은 AgenticOrchestrator를 단일 반복(max 3회)으로 호출합니다.
    이를 통해 무한 재계획 루프를 방지합니다.
    """

    def __init__(self, intent: AnalysisIntent, agentic_orchestrator=None):
        self.intent = intent
        self._orchestrator = agentic_orchestrator  # None이면 lazy init
        self._step_max_iter = 3  # 스텝당 최대 반복 (무한루프 방지)
        self._results: List[PipelineResult] = []

    async def run(self) -> List[PipelineResult]:
        """파이프라인 순차 실행: PROFILE → QUERY → TRANSFORM → VISUALIZE → INSIGHT"""
        self._results = []
        for step in [
            PipelineStep.PROFILE,
            PipelineStep.QUERY,
            PipelineStep.TRANSFORM,
            PipelineStep.VISUALIZE,
            PipelineStep.INSIGHT,
        ]:
            result = await self._run_step(step)
            self._results.append(result)
            if not result.success:
                # 스텝 실패 시 이후 스텝은 건너뜀
                break
        return self._results

    def _get_orchestrator(self):
        """Lazy init AgenticOrchestrator"""
        if self._orchestrator is None:
            from backend.orchestrator.orchestrators.agentic_orchestrator import AgenticOrchestrator
            self._orchestrator = AgenticOrchestrator(use_checkpointer=False)
        return self._orchestrator

    def _build_step_prompt(self, step: PipelineStep, prev_results: List[PipelineResult]) -> str:
        """각 스텝별 LLM 프롬프트 생성. 이전 스텝 결과를 컨텍스트로 포함."""
        intent = self.intent

        # 이전 결과 요약
        prev_output = ""
        if prev_results:
            last = prev_results[-1]
            prev_output = last.output if last.success else f"(이전 스텝 실패: {last.error})"

        if step == PipelineStep.PROFILE:
            data_sources_str = ", ".join(intent.data_sources) if intent.data_sources else "지정 없음"
            return (
                f"데이터소스 {data_sources_str} 프로파일링. "
                f"스키마와 샘플 데이터를 파악하세요."
            )

        elif step == PipelineStep.QUERY:
            metrics_str = ", ".join(intent.metrics) if intent.metrics else "지정 없음"
            return (
                f"목표 '{intent.goal}', 지표 {metrics_str}. "
                f"필요한 데이터를 조회하세요."
            )

        elif step == PipelineStep.TRANSFORM:
            return (
                f"조회 결과를 분석에 맞게 가공하세요. "
                f"이전 결과: {prev_output}"
            )

        elif step == PipelineStep.VISUALIZE:
            return (
                f"분석 결과를 시각화하세요. "
                f"최적 차트 추천 및 생성."
            )

        elif step == PipelineStep.INSIGHT:
            all_outputs = "\n".join(
                f"[{r.step.value}] {r.output}" for r in prev_results if r.success
            )
            return (
                f"전체 분석 결과를 종합하여 인사이트와 권고사항을 도출하세요.\n"
                f"분석 요약:\n{all_outputs}"
            )

        return f"{step.value} 스텝을 실행하세요."

    async def _run_step(self, step: PipelineStep) -> PipelineResult:
        """단일 스텝 실행"""
        try:
            prompt = self._build_step_prompt(step, self._results)
            orch = self._get_orchestrator()

            # MAX_ITERATIONS를 낮게 설정하여 재계획 루프 방지
            original_max = getattr(orch, '_max_iterations', None)
            if original_max is not None:
                orch._max_iterations = self._step_max_iter

            result = await orch.run(prompt)

            # 원래 max_iterations 복원
            if original_max is not None:
                orch._max_iterations = original_max

            output = result.get("final_response") or result.get("final_answer", "")
            return PipelineResult(step=step, output=output, success=True)

        except Exception as e:
            return PipelineResult(step=step, success=False, error=str(e))
