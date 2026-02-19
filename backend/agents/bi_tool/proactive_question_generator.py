"""
ProactiveQuestionGenerator - LLM 기반 후속 질문 제안 생성기

Step 13: Draft Briefing의 보조 컴포넌트
분석 결과를 바탕으로 사용자가 궁금해할 만한 후속 질문 3-5개를 자동 생성합니다.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import json
from backend.orchestrator.providers.llm_provider import LLMProvider


class QuestionType(Enum):
    """후속 질문 유형"""
    CAUSAL_ANALYSIS = "causal"  # "왜 이런 현상이 발생했나요?"
    COMPARATIVE = "comparative"  # "다른 세그먼트와 비교하면?"
    TEMPORAL = "temporal"  # "시간에 따른 변화는?"
    SEGMENT = "segment"  # "특정 그룹에서는 어떤가요?"
    DRILL_DOWN = "drill_down"  # "더 세부적으로 보면?"


@dataclass
class ProactiveQuestion:
    """후속 질문 구조"""
    question: str  # 질문 텍스트
    question_type: QuestionType  # 질문 유형
    priority: str  # 우선순위 ("high", "medium", "low")
    context: Optional[str] = None  # 질문 생성 근거/맥락

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "question": self.question,
            "type": self.question_type.value,
            "priority": self.priority,
            "context": self.context
        }


class ProactiveQuestionGenerator:
    """
    분석 결과로부터 후속 질문을 제안하는 LLM 기반 생성기

    주요 기능:
    1. 분석 컨텍스트 기반 질문 생성 (3-5개)
    2. 다양한 유형의 질문 제안 (원인/비교/시계열/세그먼트/드릴다운)
    3. 비즈니스 의사결정에 도움이 되는 구체적 질문
    4. LLM 실패 시 규칙 기반 폴백 질문 제공
    """

    QUESTION_PROMPT_TEMPLATE = """당신은 데이터 분석 전문가입니다. 다음 분석 결과를 보고 사용자가 궁금해할 만한 후속 질문 3-5개를 제안하세요.

**분석 컨텍스트:**
- 분석 목적: {purpose}
- 주요 발견: {key_findings}
- 데이터 특성: {data_characteristics}
- 분석 범위: {scope}

**질문 생성 규칙:**
1. 구체적이고 실행 가능한 질문 (추상적 질문 금지)
2. 비즈니스 의사결정에 도움이 되는 질문
3. 현재 분석을 확장하거나 심화하는 질문
4. 다양한 유형 포함:
   - causal: 원인 분석 ("왜 ~했나요?", "무엇이 영향을 주었나요?")
   - comparative: 비교 분석 ("다른 ~와 비교하면?", "~보다 높은/낮은 이유는?")
   - temporal: 시계열 분석 ("시간에 따라 어떻게 변했나요?", "트렌드는?")
   - segment: 세그먼트 분석 ("특정 그룹에서는?", "~별로 보면?")
   - drill_down: 드릴다운 ("더 세부적으로 보면?", "상세 분석은?")

**출력 형식 (JSON):**
{{
    "questions": [
        {{
            "question": "매출이 가장 높은 상위 3개 제품의 공통점은 무엇인가요?",
            "type": "drill_down",
            "priority": "high",
            "rationale": "상위 제품의 특성 파악으로 전략 수립 가능"
        }},
        {{
            "question": "전년 동기 대비 매출 변화율은 어떤가요?",
            "type": "temporal",
            "priority": "high",
            "rationale": "장기 트렌드 이해를 위한 시계열 비교"
        }},
        {{
            "question": "지역별로 매출 패턴이 다른가요?",
            "type": "segment",
            "priority": "medium",
            "rationale": "지역별 특성 이해 및 타겟팅 전략"
        }}
    ]
}}

JSON만 반환하고 추가 텍스트는 생략하세요."""

    def __init__(self, llm: Optional[LLMProvider] = None):
        """
        Args:
            llm: LLM 공급자 인스턴스 (None이면 자동 생성)
        """
        if llm is None:
            from backend.orchestrator.providers.langchain_adapter import BIAgentChatModel
            # BIAgentChatModel은 내부적으로 LLMProvider가 아니므로,
            # 직접 폴백 경로만 사용 (LLM 없이도 작동하도록)
            self.llm = None
        else:
            self.llm = llm

    async def generate_questions(
        self,
        analysis_context: Dict[str, Any]
    ) -> List[ProactiveQuestion]:
        """
        분석 컨텍스트로부터 후속 질문 생성

        Args:
            analysis_context: 분석 컨텍스트 딕셔너리
                - purpose: 분석 목적
                - key_findings: 주요 발견 사항 (리스트 또는 문자열)
                - data_characteristics: 데이터 특성 (컬럼, 행 수 등)
                - scope: 분석 범위

        Returns:
            ProactiveQuestion 객체 리스트 (3-5개)

        Example:
            >>> context = {
            ...     "purpose": "월별 매출 분석",
            ...     "key_findings": ["3월 매출이 전월 대비 20% 증가", "신규 고객 비율 35%"],
            ...     "data_characteristics": "10,000 rows, 5 columns",
            ...     "scope": "2024년 Q1"
            ... }
            >>> questions = await generator.generate_questions(context)
        """
        # 프롬프트 생성
        prompt = self._build_prompt(analysis_context)

        # LLM 호출
        try:
            response = await self._generate_with_llm(prompt)
            questions = self._parse_llm_response(response)

            # 유효성 검증: 3-5개 범위 확인
            if len(questions) < 3:
                # 부족하면 폴백 질문으로 보완
                fallback_questions = self._generate_fallback(analysis_context)
                questions.extend(fallback_questions[:(5 - len(questions))])
            elif len(questions) > 5:
                # 우선순위 순으로 상위 5개만 선택
                questions = self._prioritize_questions(questions)[:5]

            return questions

        except Exception as e:
            # LLM 실패 시 전체 폴백
            return self._generate_fallback(analysis_context)

    def _build_prompt(self, context: Dict[str, Any]) -> str:
        """
        분석 컨텍스트로부터 LLM 프롬프트 구성

        Args:
            context: 분석 컨텍스트

        Returns:
            포맷팅된 프롬프트 문자열
        """
        # key_findings 포맷팅 (리스트 → 문자열 변환)
        key_findings = context.get("key_findings", [])
        if isinstance(key_findings, list):
            findings_str = "\n".join([f"- {f}" for f in key_findings])
        else:
            findings_str = str(key_findings)

        # 데이터 특성 포맷팅
        data_chars = context.get("data_characteristics", {})
        if isinstance(data_chars, dict):
            chars_str = ", ".join([f"{k}: {v}" for k, v in data_chars.items()])
        else:
            chars_str = str(data_chars)

        return self.QUESTION_PROMPT_TEMPLATE.format(
            purpose=context.get("purpose", "분석"),
            key_findings=findings_str or "정보 없음",
            data_characteristics=chars_str or "정보 없음",
            scope=context.get("scope", "전체")
        )

    async def _generate_with_llm(self, prompt: str) -> str:
        """
        LLM을 사용하여 질문 생성

        Args:
            prompt: 생성 프롬프트

        Returns:
            LLM 응답 텍스트

        Raises:
            Exception: LLM 호출 실패 시
        """
        response = await self.llm.generate(prompt)
        return response

    def _parse_llm_response(self, response: str) -> List[ProactiveQuestion]:
        """
        LLM 응답 JSON 파싱

        Args:
            response: LLM 응답 텍스트

        Returns:
            파싱된 ProactiveQuestion 객체 리스트

        Raises:
            Exception: JSON 파싱 실패 시
        """
        # JSON 추출
        json_str = self._extract_json(response)
        data = json.loads(json_str)

        questions = []
        for item in data.get("questions", []):
            try:
                # QuestionType enum 변환
                q_type_str = item.get("type", "drill_down")
                q_type = self._str_to_question_type(q_type_str)

                question = ProactiveQuestion(
                    question=item.get("question", ""),
                    question_type=q_type,
                    priority=item.get("priority", "medium"),
                    context=item.get("rationale")  # rationale을 context로 사용
                )
                questions.append(question)
            except Exception as e:
                # 개별 질문 파싱 실패는 스킵
                continue

        return questions

    def _extract_json(self, text: str) -> str:
        """
        LLM 응답에서 JSON 부분만 추출

        Args:
            text: LLM 응답 전체 텍스트

        Returns:
            JSON 문자열

        Raises:
            ValueError: JSON을 찾을 수 없을 때
        """
        # ```json ... ``` 형태로 감싸진 경우 추출
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end != -1:
                return text[start:end].strip()

        # { ... } 형태 추출
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            return text[start:end]

        raise ValueError("JSON 형식을 찾을 수 없습니다.")

    def _str_to_question_type(self, type_str: str) -> QuestionType:
        """
        문자열을 QuestionType enum으로 변환

        Args:
            type_str: 질문 유형 문자열 ("causal", "comparative" 등)

        Returns:
            QuestionType enum 값
        """
        type_mapping = {
            "causal": QuestionType.CAUSAL_ANALYSIS,
            "comparative": QuestionType.COMPARATIVE,
            "temporal": QuestionType.TEMPORAL,
            "segment": QuestionType.SEGMENT,
            "drill_down": QuestionType.DRILL_DOWN
        }
        return type_mapping.get(type_str.lower(), QuestionType.DRILL_DOWN)

    def _generate_fallback(
        self,
        analysis_context: Dict[str, Any]
    ) -> List[ProactiveQuestion]:
        """
        LLM 실패 시 규칙 기반 폴백 질문 생성

        Args:
            analysis_context: 분석 컨텍스트

        Returns:
            기본 ProactiveQuestion 객체 리스트 (5개)
        """
        purpose = analysis_context.get("purpose", "분석")
        scope = analysis_context.get("scope", "전체")

        # 데이터 특성에서 컬럼 정보 추출 시도
        data_chars = analysis_context.get("data_characteristics", {})
        columns = []
        if isinstance(data_chars, dict):
            columns = data_chars.get("columns", [])

        # 시간 관련 컬럼 존재 여부 체크
        has_time_col = any("date" in str(col).lower() or "time" in str(col).lower()
                          for col in columns) if columns else False

        fallback_questions = [
            ProactiveQuestion(
                question=f"{purpose}에서 가장 주목할 만한 이상치나 패턴이 있나요?",
                question_type=QuestionType.DRILL_DOWN,
                priority="high",
                context="이상치 탐지를 통한 인사이트 발견"
            ),
            ProactiveQuestion(
                question=f"다른 기간이나 세그먼트와 비교했을 때 {scope}의 특징은 무엇인가요?",
                question_type=QuestionType.COMPARATIVE,
                priority="high",
                context="비교 분석을 통한 상대적 위치 파악"
            ),
            ProactiveQuestion(
                question=f"{purpose}의 주요 원인이나 영향 요인은 무엇인가요?",
                question_type=QuestionType.CAUSAL_ANALYSIS,
                priority="medium",
                context="인과관계 분석을 통한 근본 원인 파악"
            ),
        ]

        # 시간 컬럼이 있으면 시계열 질문 추가
        if has_time_col:
            fallback_questions.append(
                ProactiveQuestion(
                    question=f"시간에 따른 추세나 계절성 패턴이 관찰되나요?",
                    question_type=QuestionType.TEMPORAL,
                    priority="high",
                    context="시계열 트렌드 분석"
                )
            )
        else:
            fallback_questions.append(
                ProactiveQuestion(
                    question=f"특정 그룹이나 카테고리별로 {purpose} 결과가 어떻게 다른가요?",
                    question_type=QuestionType.SEGMENT,
                    priority="medium",
                    context="세그먼트별 차이 분석"
                )
            )

        # 5번째 질문: 드릴다운
        fallback_questions.append(
            ProactiveQuestion(
                question=f"더 세부적인 수준에서 {purpose}를 분석하면 어떤 새로운 인사이트가 나올까요?",
                question_type=QuestionType.DRILL_DOWN,
                priority="low",
                context="상세 레벨 드릴다운 분석"
            )
        )

        return fallback_questions

    def _prioritize_questions(
        self,
        questions: List[ProactiveQuestion]
    ) -> List[ProactiveQuestion]:
        """
        질문 우선순위 정렬

        Args:
            questions: 정렬할 질문 리스트

        Returns:
            우선순위 순으로 정렬된 질문 리스트 (high → medium → low)
        """
        priority_order = {"high": 0, "medium": 1, "low": 2}
        return sorted(
            questions,
            key=lambda q: priority_order.get(q.priority.lower(), 1)
        )

    def questions_to_text(
        self,
        questions: List[ProactiveQuestion],
        include_context: bool = False
    ) -> str:
        """
        질문 리스트를 사람이 읽기 쉬운 텍스트로 변환

        Args:
            questions: 질문 리스트
            include_context: 질문 생성 근거 포함 여부

        Returns:
            포맷팅된 텍스트 문자열

        Example:
            >>> text = generator.questions_to_text(questions)
            >>> print(text)
            1. [HIGH] 매출이 가장 높은 상위 3개 제품의 공통점은 무엇인가요?
            2. [HIGH] 전년 동기 대비 매출 변화율은 어떤가요?
            ...
        """
        lines = []
        for i, q in enumerate(questions, 1):
            priority_tag = f"[{q.priority.upper()}]"
            line = f"{i}. {priority_tag} {q.question}"
            if include_context and q.context:
                line += f"\n   → {q.context}"
            lines.append(line)

        return "\n".join(lines)
