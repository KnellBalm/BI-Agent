"""
SQL Generator - 자연어를 SQL 쿼리로 변환하는 고급 모듈

이 모듈은 Phase 4 Step 10 (최적 쿼리 생성)의 핵심 구현체입니다.

주요 기능:
- LLM 기반 자연어 → SQL 변환
- DB Dialect 검증 (SQLite, PostgreSQL, MySQL)
- 스키마 기반 컬럼 존재 여부 검증
- 쿼리 비용 추정 및 경고
- 한국어 쿼리 설명 생성
"""

import re
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from backend.orchestrator import LLMProvider, GeminiProvider


class DatabaseDialect(Enum):
    """지원하는 데이터베이스 방언"""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    BIGQUERY = "bigquery"
    SNOWFLAKE = "snowflake"


@dataclass
class ColumnInfo:
    """컬럼 정보를 담는 데이터 클래스"""
    name: str
    data_type: str
    table: str
    nullable: bool = True


@dataclass
class SchemaInfo:
    """스키마 정보를 담는 데이터 클래스"""
    tables: Dict[str, List[ColumnInfo]] = field(default_factory=dict)
    
    def get_all_columns(self) -> List[str]:
        """모든 컬럼명 반환"""
        columns = []
        for table_cols in self.tables.values():
            columns.extend([col.name for col in table_cols])
        return columns
    
    def get_table_columns(self, table_name: str) -> List[str]:
        """특정 테이블의 컬럼명 반환"""
        if table_name in self.tables:
            return [col.name for col in self.tables[table_name]]
        return []
    
    def column_exists(self, column_name: str, table_name: Optional[str] = None) -> bool:
        """컬럼 존재 여부 확인"""
        if table_name:
            return column_name in self.get_table_columns(table_name)
        return column_name in self.get_all_columns()


@dataclass
class SQLGenerationResult:
    """SQL 생성 결과"""
    sql: str
    explanation_ko: str
    dialect: DatabaseDialect
    referenced_tables: List[str]
    referenced_columns: List[str]
    estimated_cost: str  # "low", "medium", "high"
    warnings: List[str] = field(default_factory=list)
    is_valid: bool = True


@dataclass
class ValidationResult:
    """검증 결과"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


class DialectValidator:
    """
    DB Dialect별 SQL 문법 검증기
    
    각 데이터베이스의 문법 차이를 처리합니다:
    - 함수명 매핑 (STRFTIME vs DATE_FORMAT 등)
    - 예약어 이스케이프 규칙
    - 문자열 연결 연산자
    """
    
    # 방언별 함수 매핑
    FUNCTION_MAPPINGS = {
        DatabaseDialect.SQLITE: {
            "current_date": "DATE('now')",
            "current_timestamp": "DATETIME('now')",
            "date_format": "STRFTIME",
            "concat": "||",
            "ifnull": "IFNULL",
            "limit": "LIMIT",
        },
        DatabaseDialect.POSTGRESQL: {
            "current_date": "CURRENT_DATE",
            "current_timestamp": "CURRENT_TIMESTAMP",
            "date_format": "TO_CHAR",
            "concat": "CONCAT",
            "ifnull": "COALESCE",
            "limit": "LIMIT",
        },
        DatabaseDialect.MYSQL: {
            "current_date": "CURDATE()",
            "current_timestamp": "NOW()",
            "date_format": "DATE_FORMAT",
            "concat": "CONCAT",
            "ifnull": "IFNULL",
            "limit": "LIMIT",
        },
    }
    
    # 방언별 예약어 이스케이프
    QUOTE_CHARS = {
        DatabaseDialect.SQLITE: '"',
        DatabaseDialect.POSTGRESQL: '"',
        DatabaseDialect.MYSQL: '`',
        DatabaseDialect.BIGQUERY: '`',
        DatabaseDialect.SNOWFLAKE: '"',
    }
    
    @classmethod
    def validate_dialect(cls, sql: str, dialect: DatabaseDialect) -> ValidationResult:
        """
        SQL이 지정된 방언에 맞는지 검증합니다.
        """
        errors = []
        warnings = []
        suggestions = []
        
        sql_upper = sql.upper()
        
        # SQLite 특유의 문법 체크
        if dialect == DatabaseDialect.SQLITE:
            if "NOW()" in sql_upper:
                errors.append("SQLite는 NOW()를 지원하지 않습니다. DATETIME('now')를 사용하세요.")
                suggestions.append("NOW() → DATETIME('now')")
            if "CURDATE()" in sql_upper:
                errors.append("SQLite는 CURDATE()를 지원하지 않습니다. DATE('now')를 사용하세요.")
                suggestions.append("CURDATE() → DATE('now')")
        
        # PostgreSQL 특유의 문법 체크
        elif dialect == DatabaseDialect.POSTGRESQL:
            if "IFNULL" in sql_upper:
                warnings.append("PostgreSQL에서는 COALESCE를 사용하는 것이 표준입니다.")
                suggestions.append("IFNULL(a, b) → COALESCE(a, b)")
        
        # MySQL 특유의 문법 체크
        elif dialect == DatabaseDialect.MYSQL:
            if "STRFTIME" in sql_upper:
                errors.append("MySQL은 STRFTIME을 지원하지 않습니다. DATE_FORMAT을 사용하세요.")
                suggestions.append("STRFTIME → DATE_FORMAT")
        
        is_valid = len(errors) == 0
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    @classmethod
    def get_quote_char(cls, dialect: DatabaseDialect) -> str:
        """방언에 맞는 식별자 이스케이프 문자 반환"""
        return cls.QUOTE_CHARS.get(dialect, '"')


class SchemaValidator:
    """
    스키마 기반 SQL 검증기
    
    쿼리에서 참조된 테이블/컬럼이 실제 스키마에 존재하는지 확인합니다.
    """
    
    @staticmethod
    def extract_table_references(sql: str) -> List[str]:
        """SQL에서 테이블 참조 추출"""
        # FROM, JOIN 절에서 테이블명 추출
        patterns = [
            r'FROM\s+(["\`]?\w+["\`]?)',
            r'JOIN\s+(["\`]?\w+["\`]?)',
            r'INTO\s+(["\`]?\w+["\`]?)',
            r'UPDATE\s+(["\`]?\w+["\`]?)',
        ]
        
        tables = []
        for pattern in patterns:
            matches = re.findall(pattern, sql, re.IGNORECASE)
            tables.extend([m.strip('"`') for m in matches])
        
        return list(set(tables))
    
    @staticmethod
    def extract_column_references(sql: str) -> List[str]:
        """SQL에서 컬럼 참조 추출 (간략화된 버전)"""
        # SELECT, WHERE, ORDER BY 등에서 컬럼명 추출
        # 완전한 SQL 파싱을 위해서는 sqlparse 라이브러리 사용 권장
        
        # 기본적인 컬럼 패턴 매칭
        columns = []
        
        # SELECT 절에서 컬럼 추출
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql, re.IGNORECASE | re.DOTALL)
        if select_match:
            select_clause = select_match.group(1)
            # 간단한 컬럼명 추출 (별칭, 함수 등 복잡한 케이스는 생략)
            col_matches = re.findall(r'(\w+)\s*(?:,|$)', select_clause)
            columns.extend(col_matches)
        
        return list(set(columns))
    
    @classmethod
    def validate_references(cls, sql: str, schema: SchemaInfo) -> ValidationResult:
        """테이블/컬럼 참조 검증"""
        errors = []
        warnings = []
        suggestions = []
        
        # 테이블 검증
        tables = cls.extract_table_references(sql)
        for table in tables:
            if table.lower() not in [t.lower() for t in schema.tables.keys()]:
                # 유사한 테이블명 찾기
                similar = cls._find_similar(table, list(schema.tables.keys()))
                error_msg = f"테이블 '{table}'이(가) 스키마에 존재하지 않습니다."
                if similar:
                    error_msg += f" '{similar}'을(를) 의도하셨나요?"
                    suggestions.append(f"{table} → {similar}")
                errors.append(error_msg)
        
        is_valid = len(errors) == 0
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    @staticmethod
    def _find_similar(target: str, candidates: List[str], threshold: float = 0.6) -> Optional[str]:
        """유사한 문자열 찾기 (간단한 Levenshtein 기반)"""
        def levenshtein_ratio(s1: str, s2: str) -> float:
            s1, s2 = s1.lower(), s2.lower()
            if len(s1) < len(s2):
                s1, s2 = s2, s1
            
            if len(s2) == 0:
                return 0.0
            
            previous_row = range(len(s2) + 1)
            for i, c1 in enumerate(s1):
                current_row = [i + 1]
                for j, c2 in enumerate(s2):
                    insertions = previous_row[j + 1] + 1
                    deletions = current_row[j] + 1
                    substitutions = previous_row[j] + (c1 != c2)
                    current_row.append(min(insertions, deletions, substitutions))
                previous_row = current_row
            
            distance = previous_row[-1]
            max_len = max(len(s1), len(s2))
            return 1 - (distance / max_len)
        
        best_match = None
        best_ratio = 0.0
        
        for candidate in candidates:
            ratio = levenshtein_ratio(target, candidate)
            if ratio > best_ratio and ratio >= threshold:
                best_ratio = ratio
                best_match = candidate
        
        return best_match


class CostEstimator:
    """
    쿼리 비용 추정기
    
    예상 결과 행 수와 복잡도를 기반으로 쿼리 비용을 추정합니다.
    """
    
    # 경고 임계치
    ROW_THRESHOLD_HIGH = 100000  # 10만 행 이상: high
    ROW_THRESHOLD_MEDIUM = 10000  # 1만 행 이상: medium
    
    @classmethod
    def estimate_cost(
        cls, 
        sql: str, 
        table_row_counts: Dict[str, int]
    ) -> Tuple[str, List[str]]:
        """
        쿼리 비용 추정
        
        Returns:
            Tuple[cost_level, warnings]
            cost_level: "low", "medium", "high"
        """
        warnings = []
        sql_upper = sql.upper()
        
        # 전체 테이블 스캔 감지
        tables = SchemaValidator.extract_table_references(sql)
        total_rows = 0
        for table in tables:
            rows = table_row_counts.get(table, 0)
            total_rows += rows
        
        # WHERE 절 없는 큰 테이블 스캔 경고
        if "WHERE" not in sql_upper and total_rows > cls.ROW_THRESHOLD_MEDIUM:
            warnings.append(
                f"WHERE 절 없이 {total_rows:,}개 행을 스캔할 수 있습니다. "
                "필터를 추가하는 것이 좋습니다."
            )
        
        # CROSS JOIN 경고
        if "CROSS JOIN" in sql_upper:
            warnings.append("CROSS JOIN은 매우 비용이 높은 연산입니다. 의도한 것인지 확인하세요.")
        
        # SELECT * 경고
        if re.search(r'SELECT\s+\*', sql, re.IGNORECASE):
            warnings.append("SELECT *는 불필요한 컬럼까지 조회합니다. 필요한 컬럼만 명시하는 것이 좋습니다.")
        
        # 비용 추정
        if total_rows > cls.ROW_THRESHOLD_HIGH:
            return "high", warnings
        elif total_rows > cls.ROW_THRESHOLD_MEDIUM:
            return "medium", warnings
        else:
            return "low", warnings


class SQLGenerator:
    """
    자연어를 SQL 쿼리로 변환하는 고급 클래스
    
    Features:
    - LLM 기반 자연어 → SQL 변환
    - DB Dialect 검증
    - 스키마 기반 컬럼 검증
    - 쿼리 비용 추정
    - 한국어 쿼리 설명 생성
    """
    
    def __init__(self, llm: Optional[LLMProvider] = None):
        """
        Args:
            llm: LLM 프로바이더 (기본: GeminiProvider)
        """
        self.llm = llm or GeminiProvider()
    
    async def generate_sql(
        self, 
        user_query: str, 
        db_type: str, 
        schema_info: str
    ) -> str:
        """
        기본 SQL 생성 (하위 호환성 유지)
        
        Args:
            user_query: 사용자의 자연어 질문
            db_type: 데이터베이스 종류 (SQLite, PostgreSQL, MySQL 등)
            schema_info: 스키마 정보 문자열
            
        Returns:
            생성된 SQL 쿼리
        """
        prompt = f"""당신은 SQL 전문가입니다. 사용자의 자연어 질문을 바탕으로 적절한 SQL 쿼리를 작성하세요.

데이터베이스 종류: {db_type}
스키마 정보:
{schema_info}

사용자 질문: "{user_query}"

규칙:
1. 오직 SQL 쿼리만 응답하세요. 다른 텍스트나 설명은 포함하지 마세요.
2. 쿼리는 마크다운 코드 블록(```sql ... ```)으로 감싸지 말고 순수 텍스트로만 작성하세요.
3. 데이터베이스 종류({db_type})의 문법을 엄격히 준수하세요.
   - SQLite: STRFTIME, DATE('now'), || 연산자 사용
   - PostgreSQL: TO_CHAR, CURRENT_DATE, CONCAT 또는 || 사용
   - MySQL: DATE_FORMAT, NOW(), CONCAT 사용
4. 가능한 한 효율적인 쿼리를 작성하세요.

SQL:"""
        
        sql = await self.llm.generate(prompt)
        sql = self._clean_sql_response(sql)
        
        return sql
    
    async def generate_sql_with_validation(
        self,
        user_query: str,
        dialect: DatabaseDialect,
        schema: SchemaInfo,
        table_row_counts: Optional[Dict[str, int]] = None
    ) -> SQLGenerationResult:
        """
        검증 기능이 포함된 SQL 생성
        
        Args:
            user_query: 사용자의 자연어 질문
            dialect: 데이터베이스 방언
            schema: 스키마 정보 객체
            table_row_counts: 테이블별 행 수 (비용 추정용)
            
        Returns:
            SQLGenerationResult: 생성된 SQL 및 메타데이터
        """
        # 스키마 정보를 문자열로 변환
        schema_str = self._schema_to_string(schema)
        
        # SQL 생성
        sql = await self.generate_sql(user_query, dialect.value, schema_str)
        
        # 방언 검증
        dialect_result = DialectValidator.validate_dialect(sql, dialect)
        
        # 스키마 검증
        schema_result = SchemaValidator.validate_references(sql, schema)
        
        # 비용 추정
        cost_level = "low"
        cost_warnings = []
        if table_row_counts:
            cost_level, cost_warnings = CostEstimator.estimate_cost(sql, table_row_counts)
        
        # 모든 경고 합치기
        all_warnings = (
            dialect_result.warnings + 
            schema_result.warnings + 
            cost_warnings
        )
        
        # 에러가 있으면 유효하지 않음
        is_valid = dialect_result.is_valid and schema_result.is_valid
        if not is_valid:
            all_warnings.extend(dialect_result.errors + schema_result.errors)
        
        # 참조된 테이블/컬럼 추출
        referenced_tables = SchemaValidator.extract_table_references(sql)
        referenced_columns = SchemaValidator.extract_column_references(sql)
        
        # 한국어 설명 생성
        explanation = await self._generate_explanation(sql, user_query)
        
        return SQLGenerationResult(
            sql=sql,
            explanation_ko=explanation,
            dialect=dialect,
            referenced_tables=referenced_tables,
            referenced_columns=referenced_columns,
            estimated_cost=cost_level,
            warnings=all_warnings,
            is_valid=is_valid
        )
    
    async def _generate_explanation(self, sql: str, user_query: str) -> str:
        """SQL 쿼리에 대한 한국어 설명 생성"""
        prompt = f"""다음 SQL 쿼리가 수행하는 작업을 한국어로 간단히 설명하세요.
1-2문장으로 요약해주세요.

원래 질문: "{user_query}"

SQL:
{sql}

한국어 설명:"""
        
        try:
            explanation = await self.llm.generate(prompt)
            return explanation.strip()
        except Exception:
            return "쿼리 설명을 생성할 수 없습니다."
    
    def _clean_sql_response(self, sql: str) -> str:
        """LLM 응답에서 SQL만 추출"""
        sql = sql.strip()
        
        # 마크다운 코드 블록 제거
        if sql.startswith("```"):
            lines = sql.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            sql = "\n".join(lines)
        
        return sql.strip()
    
    def _schema_to_string(self, schema: SchemaInfo) -> str:
        """SchemaInfo를 문자열로 변환"""
        lines = []
        for table_name, columns in schema.tables.items():
            col_strs = [f"{col.name} ({col.data_type})" for col in columns]
            lines.append(f"Table: {table_name}")
            lines.append(f"  Columns: {', '.join(col_strs)}")
        return "\n".join(lines)


# 하위 호환성을 위한 팩토리 함수
def create_sql_generator(llm: Optional[LLMProvider] = None) -> SQLGenerator:
    """SQLGenerator 인스턴스 생성 팩토리 함수"""
    return SQLGenerator(llm)


if __name__ == "__main__":
    import asyncio
    
    async def main():
        generator = SQLGenerator()
        
        # 테스트용 스키마
        schema = SchemaInfo(
            tables={
                "sales": [
                    ColumnInfo("id", "INT", "sales"),
                    ColumnInfo("product_name", "TEXT", "sales"),
                    ColumnInfo("amount", "FLOAT", "sales"),
                    ColumnInfo("sale_date", "DATE", "sales"),
                ],
                "products": [
                    ColumnInfo("id", "INT", "products"),
                    ColumnInfo("name", "TEXT", "products"),
                    ColumnInfo("category", "TEXT", "products"),
                ]
            }
        )
        
        test_query = "올해 가장 많이 팔린 제품 5개와 그 금액을 알려줘"
        
        try:
            result = await generator.generate_sql_with_validation(
                user_query=test_query,
                dialect=DatabaseDialect.POSTGRESQL,
                schema=schema,
                table_row_counts={"sales": 50000, "products": 1000}
            )
            
            print(f"Generated SQL:\n{result.sql}")
            print(f"\n설명: {result.explanation_ko}")
            print(f"비용: {result.estimated_cost}")
            if result.warnings:
                print(f"경고: {result.warnings}")
        except Exception as e:
            print(f"Error: {e}")
    
    asyncio.run(main())
