"""
Core Agent — 200줄짜리 Naked BI-Agent 루프.

"The Emperor Has No Clothes" 철학에 따라,
LangGraph/Langchain 없이 순수한 While 루프 + Tool Calling으로 동작한다.

사용자 질문 → LLM 판단 → 도구 호출 파싱 → 로컬 실행 → 결과 주입 → 반복
"""
import json
import re
from typing import List, Dict, Any, Tuple, Optional

from backend.core.tools import ToolRegistry, build_default_registry
from backend.core.prompts import CORE_SYSTEM_PROMPT, THINKING_SYSTEM_PROMPT

MAX_ITERATIONS = 8


# ──────────────────────────────────────────────
# Tool Call 파싱
# ──────────────────────────────────────────────

def extract_tool_invocations(text: str) -> List[Tuple[str, Dict[str, Any]]]:
    """LLM 응답에서 tool: name({json}) 형식의 호출을 추출한다."""
    invocations = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("tool:"):
            continue
        try:
            after = line[len("tool:"):].strip()
            paren_idx = after.index("(")
            name = after[:paren_idx].strip()
            rest = after[paren_idx + 1:]
            if not rest.endswith(")"):
                continue
            json_str = rest[:-1].strip()
            args = json.loads(json_str) if json_str else {}
            invocations.append((name, args))
        except Exception:
            continue
    return invocations


# ──────────────────────────────────────────────
# LLM 호출 래퍼
# ──────────────────────────────────────────────

def _call_llm_sync(messages: List[Dict[str, str]], provider=None) -> str:
    """[Legacy] 동기 호출용입니다. 실제로는 _call_llm을 사용하세요."""
    pass

async def _call_llm(messages: List[Dict[str, str]], provider=None) -> str:
    """LLM Provider를 통해 메시지를 전송하고 응답 텍스트를 반환한다."""
    if provider is None:
        provider = _get_default_provider()

    # provider의 generate 메서드 호출
    # 기존 LLMProvider 인터페이스 활용
    try:
        prompt_parts = []
        system_content = ""
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            elif msg["role"] == "user":
                prompt_parts.append(f"User: {msg['content']}")
            elif msg["role"] == "assistant":
                prompt_parts.append(f"Assistant: {msg['content']}")

        full_prompt = "\n\n".join(prompt_parts)
        if system_content:
            full_prompt = system_content + "\n\n" + full_prompt

        response = await provider.generate(full_prompt)
        return response
    except Exception as e:
        return f"[LLM 호출 오류] {e}"


def _get_default_provider():
    """기본 LLM Provider를 생성한다."""
    from backend.orchestrator.providers.llm_provider import GeminiProvider
    return GeminiProvider()


# ──────────────────────────────────────────────
# Core Agent 루프
# ──────────────────────────────────────────────

class CoreAgent:
    """미니멀리스트 에이전트. While 루프 + Tool Calling."""

    def __init__(self, registry: Optional[ToolRegistry] = None, provider=None):
        self.registry = registry or build_default_registry()
        self.provider = provider

    async def run(self, user_input: str, context: Dict[str, Any] = None) -> str:
        """사용자 입력을 받아 도구를 자율적으로 호출하고 최종 답변을 반환한다."""
        system_prompt = CORE_SYSTEM_PROMPT.format(
            tools_prompt=self.registry.get_tools_prompt()
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]

        for iteration in range(MAX_ITERATIONS):
            response = await _call_llm(messages, self.provider)

            tool_invocations = extract_tool_invocations(response)

            if not tool_invocations:
                # 도구 호출 없음 = 최종 답변
                return response

            # 도구 실행
            for name, args in tool_invocations:
                result = self.registry.execute(name, args, context=context)
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "user", "content": f"tool_result({name}): {result}"})

        return response  # 최대 반복 도달 시 마지막 응답 반환

    async def thinking(self, idea: str) -> str:
        """사용자의 짧은 아이디어를 정교한 마크다운 분석 계획서로 확장한다."""
        messages = [
            {"role": "system", "content": THINKING_SYSTEM_PROMPT},
            {"role": "user", "content": idea},
        ]
        return await _call_llm(messages, self.provider)
