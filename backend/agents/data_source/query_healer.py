"""
Query Healer - SQL 실행 오류 자동 진단 및 수정 모듈

이 모듈은 Phase 4 Step 10.2 (자가 치유 쿼리 루프)의 구현체입니다.

주요 기능:
- SQL 실행 오류 캡처 및 분석
- LLM 기반 에러 원인 진단
- 자동 수정 및 재시도 (최대 3회)
- 치유 시도 로그 저장
"""

import json
import asyncio
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable, Awaitable
from pathlib import Path
from enum import Enum

from backend.orchestrator.llm_provider import LLMProvider, GeminiProvider


class ErrorType(Enum):
    """SQL 에러 유형"""
    COLUMN_NOT_FOUND = "column_not_found"
    TABLE_NOT_FOUND = "table_not_found"
    SYNTAX_ERROR = "syntax_error"
    AMBIGUOUS_COLUMN = "ambiguous_column"
    TYPE_MISMATCH = "type_mismatch"
    PERMISSION_DENIED = "permission_denied"
    CONNECTION_ERROR = "connection_error"
    UNKNOWN = "unknown"


@dataclass
class HealingDiagnosis:
    """에러 진단 결과"""
    error_type: ErrorType
    diagnosis_ko: str
    suggested_fix_ko: str
    corrected_sql: str
    confidence: float  # 0.0 ~ 1.0
    original_error: str


@dataclass
class HealingAttempt:
    """치유 시도 기록"""
    attempt_number: int
    timestamp: str
    original_sql: str
    error_message: str
    diagnosis: Optional[HealingDiagnosis]
    corrected_sql: Optional[str]
    result: str  # "success", "failed", "retry"
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        d = asdict(self)
        if self.diagnosis:
            d['diagnosis']['error_type'] = self.diagnosis.error_type.value
        return d


@dataclass
class ExecutionResult:
    """쿼리 실행 결과"""
    success: bool
    data: Any = None
    final_sql: str = ""
    attempts: int = 0
    healing_history: List[HealingAttempt] = field(default_factory=list)
    error: Optional[str] = None


class QueryHealer:
    """
    SQL 실행 오류 자동 진단 및 수정 클래스
    
    데이터베이스 실행 오류를 분석하고 LLM을 활용하여
    자동으로 수정된 쿼리를 생성합니다.
    
    Features:
    - 에러 유형 자동 분류
    - 유사 테이블/컬럼명 제안
    - 재시도 루프 (최대 3회)
    - 상세 로그 저장
    """
    
    # 에러 메시지 → 에러 유형 매핑 패턴
    ERROR_PATTERNS = {
        ErrorType.COLUMN_NOT_FOUND: [
            r"no such column",
            r"column .* does not exist",
            r"Unknown column",
            r"컬럼.*찾을 수 없",
        ],
        ErrorType.TABLE_NOT_FOUND: [
            r"no such table",
            r"relation .* does not exist",
            r"Table .* doesn't exist",
            r"테이블.*찾을 수 없",
        ],
        ErrorType.SYNTAX_ERROR: [
            r"syntax error",
            r"near \"",
            r"You have an error in your SQL syntax",
            r"구문 오류",
        ],
        ErrorType.AMBIGUOUS_COLUMN: [
            r"ambiguous column",
            r"ambiguous reference",
            r"모호한 컬럼",
        ],
        ErrorType.TYPE_MISMATCH: [
            r"type mismatch",
            r"cannot be cast",
            r"invalid input syntax for type",
            r"타입.*일치하지 않",
        ],
        ErrorType.PERMISSION_DENIED: [
            r"permission denied",
            r"access denied",
            r"권한.*거부",
        ],
    }
    
    SQL_HEALING_PROMPT = """당신은 SQL 디버깅 전문가입니다. 다음 SQL 에러를 분석하고 수정안을 제시하십시오.

**원본 SQL:**
```sql
{original_sql}
```

**에러 메시지:**
{error_message}

**데이터베이스 스키마:**
{schema_json}

**데이터베이스 타입:** {db_type}

**과업:**
1. 에러 원인 식별
2. 스키마와 컬럼명 대조 (오타인 경우 가장 유사한 컬럼 제안)
3. 해당 DB 타입의 문법에 맞는지 확인
4. 수정된 SQL 쿼리 제공

반환 형식 (JSON):
{{
    "error_type": "column_not_found|table_not_found|syntax_error|ambiguous_column|type_mismatch|unknown",
    "diagnosis_ko": "에러 원인 설명 (한국어)",
    "suggested_fix_ko": "수정 제안 (한국어)",
    "corrected_sql": "SELECT ... (수정된 SQL)",
    "confidence": 0.95
}}

JSON만 반환하십시오."""

    def __init__(
        self, 
        llm: Optional[LLMProvider] = None,
        log_path: Optional[Path] = None
    ):
        """
        Args:
            llm: LLM 프로바이더
            log_path: 로그 저장 경로 (기본: logs/query_healing.jsonl)
        """
        self.llm = llm or GeminiProvider()
        self.log_path = log_path or Path("logs/query_healing.jsonl")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def classify_error(self, error_message: str) -> ErrorType:
        """
        에러 메시지에서 에러 유형을 분류합니다.
        
        Args:
            error_message: DB에서 반환된 에러 메시지
            
        Returns:
            ErrorType: 분류된 에러 유형
        """
        import re
        
        error_lower = error_message.lower()
        
        for error_type, patterns in self.ERROR_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, error_lower, re.IGNORECASE):
                    return error_type
        
        return ErrorType.UNKNOWN
    
    async def diagnose_error(
        self,
        sql: str,
        error: str,
        schema: Dict[str, Any],
        db_type: str = "PostgreSQL"
    ) -> HealingDiagnosis:
        """
        SQL 에러를 분석하고 수정 제안을 생성합니다.
        
        Args:
            sql: 원본 SQL
            error: 에러 메시지
            schema: 스키마 정보 (딕셔너리)
            db_type: 데이터베이스 종류
            
        Returns:
            HealingDiagnosis: 진단 결과
        """
        # 에러 유형 사전 분류
        error_type = self.classify_error(error)
        
        # LLM에게 진단 요청
        prompt = self.SQL_HEALING_PROMPT.format(
            original_sql=sql,
            error_message=error,
            schema_json=json.dumps(schema, ensure_ascii=False, indent=2),
            db_type=db_type
        )
        
        try:
            response = await self.llm.generate(prompt)
            
            # JSON 파싱
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                lines = [l for l in lines if not l.startswith("```")]
                response = "\n".join(lines)
            
            result = json.loads(response)
            
            # ErrorType 매핑
            error_type_str = result.get("error_type", "unknown")
            try:
                error_type = ErrorType(error_type_str)
            except ValueError:
                error_type = ErrorType.UNKNOWN
            
            return HealingDiagnosis(
                error_type=error_type,
                diagnosis_ko=result.get("diagnosis_ko", "알 수 없는 에러"),
                suggested_fix_ko=result.get("suggested_fix_ko", ""),
                corrected_sql=result.get("corrected_sql", sql),
                confidence=float(result.get("confidence", 0.5)),
                original_error=error
            )
        
        except (json.JSONDecodeError, KeyError) as e:
            # LLM 응답 파싱 실패 시 기본 진단 반환
            return HealingDiagnosis(
                error_type=error_type,
                diagnosis_ko=f"에러 분석 중 문제 발생: {str(e)}",
                suggested_fix_ko="원본 쿼리를 확인해주세요.",
                corrected_sql=sql,
                confidence=0.0,
                original_error=error
            )
    
    async def heal_and_retry(
        self,
        sql: str,
        error: str,
        schema: Dict[str, Any],
        execute_fn: Callable[[str], Awaitable[Any]],
        db_type: str = "PostgreSQL",
        max_retries: int = 3
    ) -> ExecutionResult:
        """
        SQL 오류를 자동으로 수정하고 재시도합니다.
        
        Args:
            sql: 원본 SQL
            error: 초기 에러 메시지
            schema: 스키마 정보
            execute_fn: SQL 실행 함수 (async callable)
            db_type: 데이터베이스 종류
            max_retries: 최대 재시도 횟수
            
        Returns:
            ExecutionResult: 최종 실행 결과
        """
        current_sql = sql
        current_error = error
        healing_history: List[HealingAttempt] = []
        
        for attempt_num in range(1, max_retries + 1):
            # 진단 및 수정
            diagnosis = await self.diagnose_error(
                current_sql, current_error, schema, db_type
            )
            
            # 신뢰도가 너무 낮으면 중단
            if diagnosis.confidence < 0.3:
                attempt = HealingAttempt(
                    attempt_number=attempt_num,
                    timestamp=datetime.now().isoformat(),
                    original_sql=current_sql,
                    error_message=current_error,
                    diagnosis=diagnosis,
                    corrected_sql=None,
                    result="failed"
                )
                healing_history.append(attempt)
                self.log_healing_attempt(attempt)
                break
            
            corrected_sql = diagnosis.corrected_sql
            
            # 수정된 SQL 실행 시도
            try:
                result_data = await execute_fn(corrected_sql)
                
                # 성공
                attempt = HealingAttempt(
                    attempt_number=attempt_num,
                    timestamp=datetime.now().isoformat(),
                    original_sql=current_sql,
                    error_message=current_error,
                    diagnosis=diagnosis,
                    corrected_sql=corrected_sql,
                    result="success"
                )
                healing_history.append(attempt)
                self.log_healing_attempt(attempt)
                
                return ExecutionResult(
                    success=True,
                    data=result_data,
                    final_sql=corrected_sql,
                    attempts=attempt_num,
                    healing_history=healing_history
                )
            
            except Exception as e:
                # 새로운 에러 발생 - 다음 시도로
                current_sql = corrected_sql
                current_error = str(e)
                
                attempt = HealingAttempt(
                    attempt_number=attempt_num,
                    timestamp=datetime.now().isoformat(),
                    original_sql=sql,
                    error_message=current_error,
                    diagnosis=diagnosis,
                    corrected_sql=corrected_sql,
                    result="retry"
                )
                healing_history.append(attempt)
                self.log_healing_attempt(attempt)
        
        # 최대 재시도 횟수 초과
        return ExecutionResult(
            success=False,
            final_sql=current_sql,
            attempts=max_retries,
            healing_history=healing_history,
            error=current_error
        )
    
    def log_healing_attempt(self, attempt: HealingAttempt) -> None:
        """
        치유 시도를 로그 파일에 저장합니다.
        
        Args:
            attempt: 치유 시도 기록
        """
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                log_entry = attempt.to_dict()
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            # 로깅 실패는 무시
            pass
    
    def get_healing_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        최근 치유 시도 이력을 조회합니다.
        
        Args:
            limit: 최대 조회 개수
            
        Returns:
            치유 시도 이력 리스트
        """
        if not self.log_path.exists():
            return []
        
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()[-limit:]
                return [json.loads(line) for line in lines if line.strip()]
        except Exception:
            return []


# 팩토리 함수
def create_query_healer(
    llm: Optional[LLMProvider] = None,
    log_path: Optional[Path] = None
) -> QueryHealer:
    """QueryHealer 인스턴스 생성 팩토리 함수"""
    return QueryHealer(llm, log_path)


if __name__ == "__main__":
    import asyncio
    
    async def main():
        healer = QueryHealer()
        
        # 테스트용 스키마
        test_schema = {
            "tables": {
                "sales": {
                    "columns": ["id", "product_name", "amount", "sale_date"]
                },
                "products": {
                    "columns": ["id", "name", "category", "price"]
                }
            }
        }
        
        # 잘못된 컬럼명 테스트
        bad_sql = "SELECT produkt_name, amunt FROM salse"
        error_msg = "ERROR: relation \"salse\" does not exist"
        
        diagnosis = await healer.diagnose_error(
            sql=bad_sql,
            error=error_msg,
            schema=test_schema,
            db_type="PostgreSQL"
        )
        
        print(f"에러 유형: {diagnosis.error_type.value}")
        print(f"진단: {diagnosis.diagnosis_ko}")
        print(f"수정 제안: {diagnosis.suggested_fix_ko}")
        print(f"수정된 SQL: {diagnosis.corrected_sql}")
        print(f"신뢰도: {diagnosis.confidence}")
    
    asyncio.run(main())
