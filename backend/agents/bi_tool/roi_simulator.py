# /backend/agents/bi_tool/roi_simulator.py
import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
from backend.orchestrator import LLMProvider
from backend.agents.bi_tool.analysis_intent import AnalysisIntent
from backend.utils.logger_setup import setup_logger

logger = setup_logger("roi_simulator", "roi_simulator.log")


class ConfidenceLevel(Enum):
    """ROI 평가의 신뢰도 레벨"""
    HIGH = "high"      # >= 0.7
    MEDIUM = "medium"  # 0.4-0.69
    LOW = "low"        # < 0.4


@dataclass
class ROIEstimate:
    """ROI 추정 결과 데이터 클래스"""
    value_statement_ko: str  # 한국어 비즈니스 가치 진술
    confidence_level: ConfidenceLevel
    confidence_score: float  # 0.0-1.0
    rationale_ko: str  # 한국어 근거
    similar_cases: List[str]  # 유사 사례 (존재하면)
    estimated_impact: str  # "high", "medium", "low"

    def to_dict(self):
        """딕셔너리로 변환"""
        return {
            "value_statement_ko": self.value_statement_ko,
            "confidence_level": self.confidence_level.value,
            "confidence_score": self.confidence_score,
            "rationale_ko": self.rationale_ko,
            "similar_cases": self.similar_cases,
            "estimated_impact": self.estimated_impact
        }


class ROISimulator:
    """BI 분석의 ROI와 비즈니스 가치를 추정하는 클래스"""

    ROI_ESTIMATION_PROMPT = """당신은 BI 분석 가치 평가 전문가입니다.

**분석 의도:**
- 목적: {purpose}
- 타겟 지표: {target_metrics}
- 가설: {hypothesis}
- 산업: {industry}

**과업:**
이 분석이 비즈니스에 제공할 수 있는 가치를 평가하십시오.

**평가 항목:**
1. 비즈니스 가치 진술 (한국어, 1-2문장)
2. 신뢰 점수 (0.0-1.0)
3. 신뢰 점수 근거 (한국어)
4. 예상 영향도 (high/medium/low)

JSON 형식으로만 반환하되 다른 텍스트는 포함하지 마십시오:
{{
    "value_statement_ko": "이 분석은 매출 향상에 기여할 가능성이 높습니다",
    "confidence_score": 0.85,
    "rationale_ko": "명확한 지표와 검증 가능한 가설",
    "estimated_impact": "high"
}}"""

    def __init__(self, llm: LLMProvider):
        """ROI 시뮬레이터 초기화

        Args:
            llm: LLMProvider 인스턴스
        """
        self.llm = llm
        logger.info("ROISimulator initialized")

    async def estimate_roi(
        self,
        intent: AnalysisIntent,
        industry: Optional[str] = None
    ) -> ROIEstimate:
        """분석 의도에 대한 ROI 추정

        Args:
            intent: AnalysisIntent 객체
            industry: 산업 분류 (선택사항)

        Returns:
            ROIEstimate 객체

        Raises:
            ValueError: 유효하지 않은 의도
            Exception: LLM 호출 실패
        """
        try:
            # 의도 검증
            if not intent.validate():
                logger.error(f"Invalid intent: {intent}")
                raise ValueError(f"Invalid AnalysisIntent: {intent}")

            # 프롬프트 생성
            prompt = self._build_prompt(intent, industry)
            logger.debug(f"ROI estimation prompt: {prompt[:200]}...")

            # LLM 호출
            response = await self.llm.generate(prompt)
            logger.debug(f"LLM response: {response[:200]}...")

            # 응답 파싱
            estimate = self._parse_response(response)
            logger.info(f"ROI estimate completed: confidence={estimate.confidence_level.value}")

            return estimate

        except ValueError as ve:
            logger.error(f"ValueError in estimate_roi: {ve}")
            raise
        except Exception as e:
            logger.error(f"Exception in estimate_roi: {e}", exc_info=True)
            raise

    def _build_prompt(self, intent: AnalysisIntent, industry: Optional[str] = None) -> str:
        """ROI 평가 프롬프트 구성

        Args:
            intent: AnalysisIntent 객체
            industry: 산업 분류

        Returns:
            완성된 프롬프트 문자열
        """
        target_metrics_str = ", ".join(intent.target_metrics) if intent.target_metrics else "미정"
        hypothesis_str = intent.hypothesis if intent.hypothesis else "가설 미제시"
        industry_str = industry if industry else "미분류"

        return self.ROI_ESTIMATION_PROMPT.format(
            purpose=intent.purpose,
            target_metrics=target_metrics_str,
            hypothesis=hypothesis_str,
            industry=industry_str
        )

    def _parse_response(self, response: str) -> ROIEstimate:
        """LLM 응답을 ROIEstimate로 파싱

        Args:
            response: LLM 응답 텍스트

        Returns:
            ROIEstimate 객체

        Raises:
            ValueError: 파싱 실패
        """
        try:
            # 응답에서 JSON 추출
            json_str = self._extract_json(response)
            data = json.loads(json_str)

            # 필수 필드 검증
            required_fields = ["value_statement_ko", "confidence_score", "rationale_ko", "estimated_impact"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")

            confidence_score = float(data["confidence_score"])

            # 신뢰도 레벨 결정
            confidence_level = self._determine_confidence_level(confidence_score)

            # ROIEstimate 생성
            estimate = ROIEstimate(
                value_statement_ko=str(data["value_statement_ko"]),
                confidence_level=confidence_level,
                confidence_score=confidence_score,
                rationale_ko=str(data["rationale_ko"]),
                similar_cases=[],  # LLM 응답에서 유사 사례가 없으면 빈 리스트
                estimated_impact=str(data.get("estimated_impact", "medium")).lower()
            )

            logger.debug(f"Parsed ROI estimate: {estimate}")
            return estimate

        except json.JSONDecodeError as je:
            logger.error(f"JSON parse error: {je}, response={response}")
            raise ValueError(f"Failed to parse LLM response as JSON: {je}")
        except (KeyError, TypeError) as e:
            logger.error(f"Data extraction error: {e}, response={response}")
            raise ValueError(f"Failed to extract ROI data from response: {e}")

    def _extract_json(self, response: str) -> str:
        """응답 텍스트에서 JSON 추출

        Args:
            response: LLM 응답 텍스트

        Returns:
            JSON 문자열

        Raises:
            ValueError: JSON을 찾을 수 없음
        """
        # JSON 객체 감지: { ... }
        start_idx = response.find('{')
        if start_idx == -1:
            logger.error(f"No JSON found in response: {response}")
            raise ValueError("No JSON object found in response")

        # 끝 인덱스 찾기 (뒤에서부터 검색)
        end_idx = response.rfind('}')
        if end_idx == -1 or end_idx <= start_idx:
            logger.error(f"Malformed JSON in response: {response}")
            raise ValueError("Malformed JSON in response")

        return response[start_idx:end_idx + 1]

    def _determine_confidence_level(self, score: float) -> ConfidenceLevel:
        """점수에 따른 신뢰도 레벨 결정

        Args:
            score: 신뢰도 점수 (0.0-1.0)

        Returns:
            ConfidenceLevel enum 값

        Raises:
            ValueError: 유효하지 않은 점수
        """
        if not (0.0 <= score <= 1.0):
            logger.warning(f"Score out of range: {score}, clamping to [0, 1]")
            score = max(0.0, min(1.0, score))

        if score >= 0.7:
            return ConfidenceLevel.HIGH
        elif score >= 0.4:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW
