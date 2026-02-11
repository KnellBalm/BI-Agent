"""
Local Text2SQL 서비스 (Ollama 기반)
"""
import re
from typing import Dict, Any, Optional
from backend.orchestrator.providers.llm_provider import OllamaProvider
from backend.orchestrator.services.text2sql.base import BaseText2SQLService, Text2SQLResult
from backend.utils.logger_setup import setup_logger

logger = setup_logger("local_text2sql", "local_text2sql.log")


class LocalText2SQLService(BaseText2SQLService):
    """
    Ollama를 사용한 로컬 Text2SQL 서비스
    - 빠른 응답 (1-3초)
    - 무료
    - 오프라인 작동 가능
    """

    def __init__(
        self,
        model_name: str = "qwen2.5-coder:7b",
        base_url: str = "http://localhost:11434"
    ):
        """
        Args:
            model_name: Ollama 모델명 (기본: qwen2.5-coder:7b)
            base_url: Ollama 서버 URL
        """
        self.model_name = model_name
        self.provider = OllamaProvider(model_name=model_name, base_url=base_url)
        logger.info(f"LocalText2SQLService initialized with model: {model_name}")

    async def generate_sql(
        self,
        natural_query: str,
        schema_info: Dict[str, Any],
        dialect: str = "postgresql",
        include_guide: bool = True
    ) -> Text2SQLResult:
        """자연어를 SQL로 변환 (Ollama 사용)"""
        logger.info(f"Generating SQL for query: {natural_query[:50]}...")

        try:
            # 시스템 프롬프트 구성
            system_prompt = self._build_system_prompt(schema_info, dialect, include_guide)

            # 사용자 프롬프트 구성
            user_prompt = self._build_user_prompt(natural_query)

            # Ollama 호출
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            response = await self.provider.chat(messages)

            # 응답 파싱
            result = self._parse_response(response)

            logger.info(f"SQL generation successful (confidence: {result.confidence})")
            return result

        except Exception as e:
            logger.error(f"SQL generation failed: {e}")
            # Fallback 결과 반환
            return Text2SQLResult(
                sql="-- SQL 생성 실패",
                explanation=f"오류가 발생했습니다: {str(e)}",
                thinking_process="",
                warnings=["Ollama 서버 연결을 확인하세요"],
                confidence=0.0,
                provider="ollama"
            )

    def _build_system_prompt(
        self,
        schema_info: Dict[str, Any],
        dialect: str,
        include_guide: bool
    ) -> str:
        """시스템 프롬프트 생성"""
        schema_text = self._format_schema(schema_info)

        prompt = f"""당신은 숙련된 {dialect} 데이터 엔지니어입니다.

**역할**: 사용자의 자연어 질문을 실행 가능한 SQL로 변환하되, "교육적 가이드"를 제공하세요.

**규칙**:
1. **사고 과정 공개**: <think> 태그 안에 어떤 테이블과 조건을 사용할지 먼저 생각하십시오.
2. **상세한 주석**: SQL의 각 주요 절(SELECT, JOIN, WHERE)마다 왜 필요한지 한국어 주석(--)을 다십시오.
3. **주의사항 제공**: 쿼리 아래에 실무 팁(인덱스, 데이터 타입 확인 등)을 짧게 조언하십시오.
4. **논리적 스켈레톤**: 완벽한 쿼리보다 구조가 명확한 초안에 집중하십시오.

**사용 가능한 스키마**:
{schema_text}

**출력 형식**:
<think>
사용자가 원하는 것: ...
필요한 테이블: ...
조건: ...
</think>

-- [쿼리 목적 한 줄 요약]
SELECT ... -- [컬럼 설명]
FROM ... -- [테이블 선택 이유]
WHERE ... -- [필터 조건 설명]

-- 주의사항:
-- 1. ...
-- 2. ...
"""
        return prompt

    def _build_user_prompt(self, natural_query: str) -> str:
        """사용자 프롬프트 생성"""
        return f"""다음 질문을 SQL로 변환해주세요:

질문: {natural_query}

위 형식을 정확히 따라 응답해주세요."""

    def _parse_response(self, raw_response: str) -> Text2SQLResult:
        """
        AI 응답 파싱
        - <think> 블록 추출
        - SQL 추출 (주석 포함)
        - 주의사항 추출
        """
        # Thinking process 추출
        thinking_match = re.search(
            r'<think>(.*?)</think>',
            raw_response,
            re.DOTALL | re.IGNORECASE
        )
        thinking_process = thinking_match.group(1).strip() if thinking_match else ""

        # SQL 추출 (SELECT부터 세미콜론까지 또는 주의사항 전까지)
        sql_match = re.search(
            r'(SELECT.*?;)',
            raw_response,
            re.DOTALL | re.IGNORECASE
        )

        if not sql_match:
            # 세미콜론이 없는 경우 SELECT부터 주의사항 전까지
            sql_match = re.search(
                r'(SELECT.*?)(?=\n-- 주의사항|\Z)',
                raw_response,
                re.DOTALL | re.IGNORECASE
            )

        sql = sql_match.group(1).strip() if sql_match else ""

        # 주의사항 추출
        warnings = []
        warnings_section = re.search(
            r'-- 주의사항:\s*\n((?:-- .*\n?)*)',
            raw_response,
            re.MULTILINE
        )

        if warnings_section:
            warning_lines = warnings_section.group(1).strip().split('\n')
            for line in warning_lines:
                clean_line = line.strip().lstrip('--').strip()
                if clean_line and not clean_line.startswith('주의사항'):
                    # 번호 제거 (1., 2., 등)
                    clean_line = re.sub(r'^\d+\.\s*', '', clean_line)
                    warnings.append(clean_line)

        # 신뢰도 계산 (간단한 휴리스틱)
        confidence = 0.5  # 기본값
        if sql and "SELECT" in sql.upper():
            confidence = 0.7
        if thinking_process:
            confidence += 0.1
        if warnings:
            confidence += 0.1
        confidence = min(confidence, 1.0)

        # 설명 생성
        explanation = "AI가 생성한 SQL 쿼리입니다."
        if thinking_process:
            first_line = thinking_process.split('\n')[0]
            explanation = first_line[:100] + ("..." if len(first_line) > 100 else "")

        return Text2SQLResult(
            sql=sql,
            explanation=explanation,
            thinking_process=thinking_process,
            warnings=warnings,
            confidence=confidence,
            provider="ollama"
        )
