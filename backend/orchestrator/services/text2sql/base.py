"""
Text2SQL 서비스 기본 인터페이스 및 데이터 모델
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class Text2SQLResult:
    """SQL 생성 결과"""
    sql: str
    explanation: str
    thinking_process: str
    warnings: List[str]
    confidence: float
    provider: str  # "ollama", "gemini", "claude", "openai"


class BaseText2SQLService(ABC):
    """Text2SQL 서비스 인터페이스"""

    @abstractmethod
    async def generate_sql(
        self,
        natural_query: str,
        schema_info: Dict[str, Any],
        dialect: str = "postgresql",
        include_guide: bool = True
    ) -> Text2SQLResult:
        """
        자연어를 주석이 포함된 SQL로 변환

        Args:
            natural_query: 사용자의 한국어 질문
            schema_info: DB 스키마 정보 (MetadataScanner에서 가져옴)
            dialect: DB 방언 (postgresql, sqlite 등)
            include_guide: 주석 및 가이드 포함 여부

        Returns:
            Text2SQLResult(
                sql: str,                    # 생성된 SQL
                explanation: str,            # 한국어 설명
                thinking_process: str,       # AI의 사고 과정
                warnings: List[str],         # 주의사항
                confidence: float,           # 신뢰도 (0-1)
                provider: str                # 사용된 제공자
            )
        """
        pass

    def _format_schema(self, schema_info: Dict[str, Any]) -> str:
        """
        스키마 정보를 프롬프트용 텍스트로 포맷팅

        Args:
            schema_info: 테이블명 -> 컬럼 정보 매핑

        Returns:
            포맷팅된 스키마 텍스트
        """
        if not schema_info:
            return "스키마 정보가 제공되지 않았습니다."

        lines = []
        for table_name, columns in schema_info.items():
            lines.append(f"테이블: {table_name}")
            if isinstance(columns, list):
                for col in columns:
                    if isinstance(col, dict):
                        col_name = col.get('name', 'unknown')
                        col_type = col.get('type', 'unknown')
                        lines.append(f"  - {col_name} ({col_type})")
                    else:
                        lines.append(f"  - {col}")
            lines.append("")

        return "\n".join(lines)
