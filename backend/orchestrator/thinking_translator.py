"""
Thinking Translator for BI-Agent

Translates LLM agent states to Korean labels and broadcasts via AgentMessageBus.
Provides progress tracking with time estimation and step completion.
"""

import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from backend.orchestrator.agent_message_bus import (
    AgentMessageBus,
    AgentMessage,
    MessageType,
)

logger = logging.getLogger(__name__)


class AgentState(Enum):
    """Agent processing states for BI analysis pipeline."""

    SCHEMA_ANALYSIS = "schema_analysis"
    HYPOTHESIS_GENERATION = "hypothesis_generation"
    QUERY_OPTIMIZATION = "query_optimization"
    DATA_PROFILING = "data_profiling"
    VISUALIZATION = "visualization"
    INSIGHT_EXTRACTION = "insight_extraction"


# Korean labels for each agent state
STATE_LABELS_KO: Dict[AgentState, str] = {
    AgentState.SCHEMA_ANALYSIS: "스키마 해석 중...",
    AgentState.HYPOTHESIS_GENERATION: "가설 생성 중...",
    AgentState.QUERY_OPTIMIZATION: "쿼리 최적화 중...",
    AgentState.DATA_PROFILING: "데이터 프로파일링 중...",
    AgentState.VISUALIZATION: "시각화 생성 중...",
    AgentState.INSIGHT_EXTRACTION: "인사이트 추출 중...",
}


class ThinkingTranslator:
    """
    Translates agent states to Korean labels and manages progress tracking.

    Integrates with AgentMessageBus to broadcast thinking status, progress updates,
    and completion notifications to the TUI.

    Example:
        translator = ThinkingTranslator(message_bus)
        translator.set_pipeline(total_steps=5)

        await translator.transition_to(AgentState.SCHEMA_ANALYSIS, agent="DataMaster")
        # ... do work ...
        await translator.complete_step("step1", "스키마 분석 완료")

        await translator.transition_to(AgentState.QUERY_OPTIMIZATION, agent="Strategist")
        # ... do work ...
        await translator.complete_step("step2", "쿼리 생성 완료")
    """

    def __init__(self, message_bus: AgentMessageBus):
        """
        Initialize thinking translator.

        Args:
            message_bus: AgentMessageBus instance for broadcasting messages
        """
        self.message_bus = message_bus
        self.current_state: Optional[AgentState] = None
        self.step_count: int = 0
        self.total_steps: int = 0
        self.start_time: Optional[datetime] = None
        logger.info("ThinkingTranslator initialized")

    def set_pipeline(self, total_steps: int) -> None:
        """
        Set total steps for progress tracking.

        Call this at the start of a pipeline to enable progress percentage
        and time estimation.

        Args:
            total_steps: Total number of steps in the pipeline

        Raises:
            ValueError: If total_steps is less than 1
        """
        if total_steps < 1:
            raise ValueError(f"total_steps must be >= 1, got {total_steps}")

        self.total_steps = total_steps
        self.step_count = 0
        self.start_time = datetime.now()
        logger.info(f"Pipeline set with {total_steps} total steps")

    async def transition_to(self, state: AgentState, agent: str = "System") -> None:
        """
        Transition to new state and broadcast thinking message.

        Args:
            state: New agent state to transition to
            agent: Name of the agent making the transition (default: "System")

        Raises:
            ValueError: If state is not a valid AgentState
        """
        if not isinstance(state, AgentState):
            raise ValueError(f"Invalid state: {state}. Must be an AgentState enum.")

        self.current_state = state
        label = STATE_LABELS_KO.get(state, "처리 중...")

        message = AgentMessage(
            timestamp=datetime.now(),
            from_agent=agent,
            to_agent="broadcast",
            message_type=MessageType.THINKING,
            content=label,
            metadata={"state": state.value},
        )

        try:
            await self.message_bus.publish(message)
            logger.info(f"Transitioned to state: {state.value} (agent: {agent})")
        except Exception as e:
            logger.error(f"Failed to publish state transition: {e}", exc_info=True)
            raise

    async def complete_step(self, step_id: str, description: str) -> None:
        """
        Mark step as complete and update progress.

        Increments step counter and broadcasts progress message with
        time estimation.

        Args:
            step_id: Unique identifier for the completed step
            description: Korean description of what was completed

        Raises:
            ValueError: If step_id is empty or description is empty
        """
        if not step_id or not step_id.strip():
            raise ValueError("step_id cannot be empty")
        if not description or not description.strip():
            raise ValueError("description cannot be empty")

        self.step_count += 1

        progress_text = f"{self.step_count}/{self.total_steps} 단계 완료: {description}"
        remaining_time = self._estimate_remaining_time()

        if remaining_time:
            progress_text += f" (예상 남은 시간: {remaining_time}초)"

        message = AgentMessage(
            timestamp=datetime.now(),
            from_agent="System",
            to_agent="broadcast",
            message_type=MessageType.PROGRESS,
            content=progress_text,
            metadata={
                "step": self.step_count,
                "total": self.total_steps,
                "step_id": step_id,
                "description": description,
                "remaining_time": remaining_time,
            },
        )

        try:
            await self.message_bus.publish(message)
            logger.info(
                f"Step {self.step_count}/{self.total_steps} completed: {step_id}"
            )
        except Exception as e:
            logger.error(f"Failed to publish step completion: {e}", exc_info=True)
            raise

    def _estimate_remaining_time(self) -> Optional[int]:
        """
        Estimate remaining time based on elapsed time and progress.

        Uses average time per completed step to estimate how long
        remaining steps will take.

        Returns:
            Estimated remaining time in seconds, or None if estimation
            is not possible (no steps completed yet or no start time)
        """
        if not self.start_time or self.step_count == 0:
            return None

        elapsed = (datetime.now() - self.start_time).total_seconds()
        avg_time_per_step = elapsed / self.step_count
        remaining_steps = self.total_steps - self.step_count

        if remaining_steps <= 0:
            return 0

        return int(avg_time_per_step * remaining_steps)

    async def send_thinking(self, agent: str, content: str) -> None:
        """
        Send generic thinking message.

        Use this for ad-hoc thinking messages that don't correspond
        to a specific state transition.

        Args:
            agent: Name of the agent sending the message
            content: Korean thinking message content

        Raises:
            ValueError: If agent or content is empty
        """
        if not agent or not agent.strip():
            raise ValueError("agent cannot be empty")
        if not content or not content.strip():
            raise ValueError("content cannot be empty")

        message = AgentMessage(
            timestamp=datetime.now(),
            from_agent=agent,
            to_agent="broadcast",
            message_type=MessageType.THINKING,
            content=content,
            metadata={},
        )

        try:
            await self.message_bus.publish(message)
            logger.debug(f"Thinking message sent from {agent}: {content}")
        except Exception as e:
            logger.error(f"Failed to send thinking message: {e}", exc_info=True)
            raise

    def reset(self) -> None:
        """
        Reset translator state.

        Clears current state, step count, and start time.
        Useful for reusing the same translator instance for multiple pipelines.
        """
        self.current_state = None
        self.step_count = 0
        self.total_steps = 0
        self.start_time = None
        logger.info("ThinkingTranslator reset")

    @property
    def progress_percentage(self) -> float:
        """
        Get current progress as percentage.

        Returns:
            Progress percentage (0.0 to 100.0), or 0.0 if total_steps is 0
        """
        if self.total_steps == 0:
            return 0.0
        return (self.step_count / self.total_steps) * 100.0

    @property
    def is_complete(self) -> bool:
        """
        Check if all steps are complete.

        Returns:
            True if step_count >= total_steps and total_steps > 0
        """
        return self.total_steps > 0 and self.step_count >= self.total_steps

    @property
    def elapsed_time(self) -> Optional[float]:
        """
        Get elapsed time since pipeline started.

        Returns:
            Elapsed time in seconds, or None if pipeline hasn't started
        """
        if not self.start_time:
            return None
        return (datetime.now() - self.start_time).total_seconds()
