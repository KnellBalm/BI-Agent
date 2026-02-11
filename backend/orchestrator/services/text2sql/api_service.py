"""
API-based Text2SQL 서비스 (Cloud LLM 기반)
"""
import re
from typing import Dict, Any, Optional
from backend.orchestrator.providers.llm_provider import (
    GeminiProvider,
    ClaudeProvider,
    OpenAIProvider
)
from backend.orchestrator.services.text2sql.base import BaseText2SQLService, Text2SQLResult
from backend.utils.logger_setup import setup_logger

logger = setup_logger("api_text2sql", "api_text2sql.log")


class APIText2SQLService(BaseText2SQLService):
    """
    Cloud LLM API를 사용한 Text2SQL 서비스
    - 더 정확한 SQL 생성
    - 복잡한 쿼리 지원
    - API 키 필요 (유료)
    """

    def __init__(
        self,
        provider: str = "gemini",
        model_name: Optional[str] = None
    ):
        """
        Args:
            provider: 사용할 제공자 ("gemini", "claude", "openai")
            model_name: 사용할 모델명 (None이면 각 제공자의 기본값)
        """
        self.provider_name = provider.lower()

        # 제공자별 기본 모델
        default_models = {
            "gemini": "gemini-2.0-flash",
            "claude": "claude-3-5-sonnet-20241022",
            "openai": "gpt-4o"
        }

        # Provider 인스턴스 생성
        if self.provider_name == "gemini":
            self.provider = GeminiProvider(
                model_name=model_name or default_models["gemini"]
            )
        elif self.provider_name == "claude":
            self.provider = ClaudeProvider(
                model_name=model_name or default_models["claude"]
            )
        elif self.provider_name == "openai":
            self.provider = OpenAIProvider(
                model_name=model_name or default_models["openai"]
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        logger.info(f"APIText2SQLService initialized with provider: {self.provider_name}")

    async def generate_sql(
        self,
        natural_query: str,
        schema_info: Dict[str, Any],
        dialect: str = "postgresql",
        include_guide: bool = True
    ) -> Text2SQLResult:
        """자연어를 SQL로 변환 (Cloud API 사용)"""
        logger.info(f"Generating SQL via {self.provider_name} for query: {natural_query[:50]}...")

        try:
            # 시스템 프롬프트 구성
            system_prompt = self._build_system_prompt(schema_info, dialect, include_guide)

            # 사용자 프롬프트 구성
            user_prompt = self._build_user_prompt(natural_query)

            # API 호출
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            response = await self.provider.chat(messages)

            # 응답 파싱
            result = self._parse_response(response)

            logger.info(f"SQL generation successful via {self.provider_name} (confidence: {result.confidence})")
            return result

        except Exception as e:
            logger.error(f"SQL generation failed via {self.provider_name}: {e}")
            # Fallback 결과 반환
            return Text2SQLResult(
                sql="-- SQL 생성 실패",
                explanation=f"오류가 발생했습니다: {str(e)}",
                thinking_process="",
                warnings=[f"{self.provider_name.title()} API 연결을 확인하세요"],
                confidence=0.0,
                provider=self.provider_name
            )

    def _build_system_prompt(
        self,
        schema_info: Dict[str, Any],
        dialect: str,
        include_guide: bool
    ) -> str:
        """시스템 프롬프트 생성 (Cloud API 최적화)"""
        schema_text = self._format_schema(schema_info)

        prompt = f"""당신은 전문적인 {dialect} 데이터베이스 엔지니어입니다.

**역할**: 사용자의 자연어 질문을 실행 가능하고 최적화된 SQL로 변환하며, 상세한 설명과 가이드를 제공합니다.

**핵심 원칙**:
1. **분석적 사고**: <think> 태그에서 질문 분석, 필요한 테이블/조인/조건을 논리적으로 추론
2. **명확한 주석**: 각 SQL 절(SELECT, FROM, JOIN, WHERE, GROUP BY 등)에 목적과 이유 설명
3. **실무 조언**: 성능 최적화, 인덱스 활용, 데이터 타입 검증 등 실무 팁 제공
4. **정확성 우선**: 문법적으로 올바르고 실행 가능한 쿼리 생성

**고급 기능 활용**:
- 복잡한 분석에는 CTE(WITH 절) 사용
- 집계 함수와 윈도우 함수 적절히 활용
- 날짜/시간 함수로 정확한 기간 계산
- NULL 처리 및 엣지 케이스 고려

**사용 가능한 스키마**:
{schema_text}

**출력 형식**:
<think>
[분석 전략]
1. 질문 요구사항: ...
2. 필요한 테이블: ...
3. 조인 전략: ...
4. 필터/집계 조건: ...
</think>

-- [쿼리 목적 및 전략 요약]
SELECT
  column1,              -- [컬럼 설명 및 선택 이유]
  AGG(column2) as name  -- [집계 함수 목적]
FROM table1 t1          -- [테이블 설명]
  LEFT JOIN table2 t2 ON t1.id = t2.fk_id  -- [조인 이유]
WHERE condition         -- [필터 조건 설명]
GROUP BY column1        -- [그룹화 기준]
ORDER BY name DESC      -- [정렬 기준]
LIMIT n;                -- [결과 제한 이유]

-- [성능 최적화 팁]
-- 1. 인덱스: ...
-- 2. 데이터 타입: ...
-- 3. 주의사항: ...
"""
        return prompt

    def _build_user_prompt(self, natural_query: str) -> str:
        """사용자 프롬프트 생성"""
        return f"""다음 질문을 분석하고 최적화된 SQL 쿼리를 생성해주세요:

질문: {natural_query}

위 출력 형식을 정확히 따라주세요. <think> 블록에서 전략을 설명하고, 주석이 포함된 SQL을 생성한 후, 성능 최적화 팁을 제공해주세요."""

    def _parse_response(self, raw_response: str) -> Text2SQLResult:
        """
        AI 응답 파싱
        Cloud API는 더 구조화된 응답을 제공하는 경향
        """
        # Thinking process 추출
        thinking_match = re.search(
            r'<think>(.*?)</think>',
            raw_response,
            re.DOTALL | re.IGNORECASE
        )
        thinking_process = thinking_match.group(1).strip() if thinking_match else ""

        # SQL 추출 (더 관대한 패턴)
        sql_match = re.search(
            r'((?:WITH\s+.*?\s+)?SELECT.*?;)',
            raw_response,
            re.DOTALL | re.IGNORECASE
        )

        if not sql_match:
            # 세미콜론이 없는 경우
            sql_match = re.search(
                r'((?:WITH\s+.*?\s+)?SELECT.*?)(?=\n--\s*\[|-- 성능|\Z)',
                raw_response,
                re.DOTALL | re.IGNORECASE
            )

        sql = sql_match.group(1).strip() if sql_match else ""

        # 주의사항/최적화 팁 추출 (더 유연한 패턴)
        warnings = []

        # "성능 최적화 팁", "주의사항", "최적화" 등의 섹션 찾기
        tips_pattern = r'--\s*\[?(?:성능|최적화|주의사항).*?\]?\s*\n((?:--.*\n?)*)'
        tips_matches = re.finditer(tips_pattern, raw_response, re.MULTILINE | re.IGNORECASE)

        for match in tips_matches:
            tip_lines = match.group(1).strip().split('\n')
            for line in tip_lines:
                clean_line = line.strip().lstrip('--').strip()
                if clean_line:
                    # 번호 제거
                    clean_line = re.sub(r'^\d+\.\s*', '', clean_line)
                    # 카테고리 라벨 제거 (예: "인덱스:", "데이터 타입:")
                    clean_line = re.sub(r'^[\w가-힣]+:\s*', '', clean_line)
                    if clean_line and len(clean_line) > 5:  # 너무 짧은 것 제외
                        warnings.append(clean_line)

        # 중복 제거
        warnings = list(dict.fromkeys(warnings))

        # 신뢰도 계산 (Cloud API는 더 높은 신뢰도)
        confidence = 0.8  # 기본값
        if sql and "SELECT" in sql.upper():
            confidence = 0.9
        if thinking_process:
            confidence += 0.05
        if warnings:
            confidence += 0.05
        confidence = min(confidence, 1.0)

        # 설명 생성
        explanation = f"{self.provider_name.title()} API가 생성한 SQL 쿼리입니다."
        if thinking_process:
            # 첫 번째 의미있는 줄 찾기
            lines = [l.strip() for l in thinking_process.split('\n') if l.strip()]
            for line in lines:
                if not line.startswith('[') and not line.startswith('1.'):
                    explanation = line[:150] + ("..." if len(line) > 150 else "")
                    break

        return Text2SQLResult(
            sql=sql,
            explanation=explanation,
            thinking_process=thinking_process,
            warnings=warnings[:5],  # 최대 5개까지만
            confidence=confidence,
            provider=self.provider_name
        )
