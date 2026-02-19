"""
Ralph Mode — 병렬 스웜 분석 엔진 (TASK-004)

여러 분석 가설을 동시에 실행하고 결과를 합성하는 병렬 처리 시스템.
LangGraph의 fan-out/fan-in 패턴을 활용합니다.

사용 예시:
    ralph = RalphSwarm(llm=BIAgentChatModel())
    result = await ralph.execute_parallel([
        {"hypothesis": "매출이 계절에 영향받는다", "tool": "query_database"},
        {"hypothesis": "고객 세그먼트별 성과 차이가 있다", "tool": "analyze_schema"},
    ])
"""
import asyncio
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from backend.orchestrator.providers.langchain_adapter import BIAgentChatModel
from backend.orchestrator.orchestrators.agentic_orchestrator import ToolRegistry, _build_default_registry
from backend.utils.logger_setup import setup_logger

logger = setup_logger("ralph_swarm", "ralph_swarm.log")


@dataclass
class SwarmTask:
    """스웜에서 실행할 개별 분석 작업."""
    id: str
    hypothesis: str
    tool_name: str = ""
    tool_args: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"    # pending, running, done, error
    result: str = ""
    elapsed_ms: float = 0.0


@dataclass
class SwarmResult:
    """스웜 실행 전체 결과."""
    tasks: List[SwarmTask]
    synthesis: str = ""
    total_elapsed_ms: float = 0.0
    
    @property
    def success_count(self) -> int:
        return sum(1 for t in self.tasks if t.status == "done")
    
    @property 
    def error_count(self) -> int:
        return sum(1 for t in self.tasks if t.status == "error")


class RalphSwarm:
    """
    Ralph Mode 병렬 스웜 엔진.
    
    여러 분석 가설을 동시에 실행(fan-out)하고,
    결과를 하나의 인사이트로 합성(fan-in)합니다.
    
    ┌─────────┐
    │  입력    │ (가설 목록)
    └────┬────┘
         │ fan-out
    ┌────▼────┬────────┬────────┐
    │ 가설 1  │ 가설 2 │ 가설 3 │  (병렬 실행)
    └────┬────┴────┬───┴────┬───┘
         │         │        │ fan-in
    ┌────▼─────────▼────────▼───┐
    │      결과 합성 (LLM)       │
    └────────────┬──────────────┘
                 │
    ┌────────────▼──────────────┐
    │      최종 인사이트         │
    └───────────────────────────┘
    """
    
    def __init__(self, llm: Optional[BIAgentChatModel] = None,
                 registry: Optional[ToolRegistry] = None,
                 max_concurrent: int = 5):
        self._llm = llm or BIAgentChatModel()
        self._registry = registry or _build_default_registry()
        self._max_concurrent = max_concurrent
    
    async def execute_parallel(self, tasks: List[Dict[str, Any]]) -> SwarmResult:
        """
        여러 분석 작업을 병렬로 실행하고 결과를 합성합니다.
        
        Args:
            tasks: 작업 리스트, 각 항목은:
                - hypothesis: 검증할 가설
                - tool: 사용할 도구 이름 (선택)
                - args: 도구 인자 (선택)
        
        Returns:
            SwarmResult: 전체 실행 결과 + 합성 인사이트
        """
        t0 = time.time()
        
        # 1. SwarmTask 객체로 변환
        swarm_tasks = []
        for i, t in enumerate(tasks):
            swarm_tasks.append(SwarmTask(
                id=f"swarm-{i+1}",
                hypothesis=t.get("hypothesis", t.get("query", "")),
                tool_name=t.get("tool", "query_database"),
                tool_args=t.get("args", {"query_description": t.get("hypothesis", "")}),
            ))
        
        # 2. Fan-out: 병렬 실행
        semaphore = asyncio.Semaphore(self._max_concurrent)
        
        async def run_task(task: SwarmTask) -> SwarmTask:
            async with semaphore:
                task.status = "running"
                task_t0 = time.time()
                try:
                    logger.info(f"[Ralph] {task.id} 시작: {task.hypothesis[:50]}...")
                    result = self._registry.execute(task.tool_name, task.tool_args)
                    task.result = result
                    task.status = "done"
                except Exception as e:
                    task.result = f"오류: {str(e)}"
                    task.status = "error"
                    logger.error(f"[Ralph] {task.id} 실패: {e}")
                finally:
                    task.elapsed_ms = (time.time() - task_t0) * 1000
                return task
        
        completed = await asyncio.gather(*[run_task(t) for t in swarm_tasks])
        
        # 3. Fan-in: 결과 합성
        synthesis = await self._synthesize_results(list(completed))
        
        total_elapsed = (time.time() - t0) * 1000
        logger.info(f"[Ralph] 스웜 완료: {len(completed)}개 작업, {total_elapsed:.0f}ms")
        
        return SwarmResult(
            tasks=list(completed),
            synthesis=synthesis,
            total_elapsed_ms=total_elapsed,
        )
    
    async def _synthesize_results(self, tasks: List[SwarmTask]) -> str:
        """병렬 실행 결과를 하나의 인사이트로 합성합니다."""
        # 결과 컨텍스트 구성
        context_parts = []
        for task in tasks:
            status_emoji = "✅" if task.status == "done" else "❌"
            context_parts.append(
                f"{status_emoji} 가설: {task.hypothesis}\n"
                f"   결과: {task.result[:200]}\n"
                f"   소요: {task.elapsed_ms:.0f}ms"
            )
        
        context = "\n\n".join(context_parts)
        
        prompt = f"""아래는 여러 분석 가설을 병렬로 검증한 결과입니다.
이 결과들을 종합하여 핵심 인사이트를 3~5줄로 요약하세요.

## 병렬 분석 결과
{context}

## 종합 인사이트 (한국어, 3~5줄)"""
        
        try:
            response = await self._llm.ainvoke([
                {"role": "user", "content": prompt}
            ])
            return response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            logger.error(f"[Ralph] 합성 실패: {e}")
            # LLM 실패 시 기본 합성
            success = sum(1 for t in tasks if t.status == "done")
            return f"총 {len(tasks)}개 가설 중 {success}개 검증 완료. LLM 합성 실패로 개별 결과를 참조하세요."
