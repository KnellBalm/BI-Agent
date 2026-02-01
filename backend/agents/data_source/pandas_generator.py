"""
Pandas Generator - SQL로 표현하기 어려운 복잡한 변환을 위한 Pandas 코드 생성 모듈

이 모듈은 Phase 4 Step 10.3 (Pandas 변환 생성기)의 구현체입니다.

주요 기능:
- LLM 기반 Pandas 변환 코드 생성
- 제한된 환경에서 안전한 코드 실행
- 복잡한 분석 연산 지원 (피벗, 롤링 윈도우 등)
"""

import json
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum

try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

from backend.orchestrator.llm_provider import LLMProvider, GeminiProvider


class TransformationType(Enum):
    """변환 작업 유형"""
    PIVOT = "pivot"
    MELT = "melt"
    ROLLING = "rolling"
    RESAMPLE = "resample"
    MERGE = "merge"
    GROUPBY = "groupby"
    CUSTOM = "custom"


@dataclass
class DataFrameInfo:
    """DataFrame 메타 정보"""
    columns: List[str]
    dtypes: Dict[str, str]
    shape: tuple
    sample_data: Optional[Dict[str, Any]] = None


@dataclass
class TransformIntent:
    """변환 의도"""
    description: str
    transform_type: TransformationType
    input_columns: List[str] = field(default_factory=list)
    output_columns: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationResult:
    """코드 생성 결과"""
    code: str
    explanation_ko: str
    required_imports: List[str]
    is_safe: bool
    warnings: List[str] = field(default_factory=list)


@dataclass
class ExecutionResult:
    """실행 결과"""
    success: bool
    result_info: Optional[DataFrameInfo] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0


class CodeSanitizer:
    """
    코드 안전성 검사기
    
    위험한 작업을 감지하고 차단합니다.
    """
    
    # 허용되지 않는 패턴
    FORBIDDEN_PATTERNS = [
        "import os",
        "import sys",
        "import subprocess",
        "import shutil",
        "__import__",
        "eval(",
        "exec(",
        "compile(",
        "open(",
        "file(",
        "input(",
        "raw_input(",
        "os.system",
        "os.popen",
        "subprocess.",
        "shutil.",
        ".read(",
        ".write(",
        ".delete(",
        "remove(",
        "unlink(",
        "rmdir(",
        "makedirs(",
        "listdir(",
        "glob(",
        "walk(",
        "getattr(",
        "setattr(",
        "delattr(",
        "__dict__",
        "__class__",
        "__bases__",
        "__subclasses__",
        "__mro__",
        "breakpoint(",
    ]
    
    # 허용된 import
    ALLOWED_IMPORTS = [
        "pandas",
        "pd",
        "numpy",
        "np",
        "datetime",
        "math",
        "re",
        "json",
    ]
    
    @classmethod
    def is_safe(cls, code: str) -> tuple[bool, List[str]]:
        """
        코드 안전성 검사
        
        Returns:
            (is_safe, warnings)
        """
        warnings = []
        code_lower = code.lower()
        
        # 위험한 패턴 검사
        for pattern in cls.FORBIDDEN_PATTERNS:
            if pattern.lower() in code_lower:
                warnings.append(f"위험한 패턴 감지: {pattern}")
        
        # 허용되지 않은 import 검사
        import re
        import_matches = re.findall(r'import\s+(\w+)', code)
        from_matches = re.findall(r'from\s+(\w+)', code)
        
        all_imports = import_matches + from_matches
        for imp in all_imports:
            if imp.lower() not in [a.lower() for a in cls.ALLOWED_IMPORTS]:
                warnings.append(f"허용되지 않은 import: {imp}")
        
        is_safe = len(warnings) == 0
        return is_safe, warnings


class PandasGenerator:
    """
    Pandas 변환 코드 생성기
    
    SQL로 표현하기 어려운 복잡한 데이터 변환 작업을 위해
    Pandas 코드를 자동 생성합니다.
    
    Features:
    - 피벗 테이블
    - 롤링 윈도우 연산
    - 복잡한 그룹화 연산
    - 시계열 리샘플링
    """
    
    CODE_GENERATION_PROMPT = """당신은 Python Pandas 전문가입니다. 다음 요청에 맞는 Pandas 변환 코드를 생성하세요.

**요청:** {description}

**입력 DataFrame 정보:**
- 컬럼: {columns}
- 데이터 타입: {dtypes}
- 샘플 데이터: {sample_data}

**규칙:**
1. 오직 pandas와 numpy만 사용하세요.
2. 입력 DataFrame 변수명은 `df`입니다.
3. 결과는 반드시 `result_df` 변수에 저장하세요.
4. 코드만 반환하고 설명은 포함하지 마세요.
5. 마크다운 코드 블록을 사용하지 마세요.
6. 파일 I/O, 시스템 호출, 네트워크 요청은 절대 사용하지 마세요.

**예시:**
```
result_df = df.groupby('category').agg({{'amount': 'sum', 'count': 'mean'}})
```

Python 코드:"""

    EXPLANATION_PROMPT = """다음 Pandas 코드가 수행하는 작업을 한국어로 간단히 설명하세요.
1-2문장으로 요약해주세요.

코드:
{code}

한국어 설명:"""

    def __init__(self, llm: Optional[LLMProvider] = None):
        """
        Args:
            llm: LLM 프로바이더
        """
        self.llm = llm or GeminiProvider()
    
    async def generate_transform_code(
        self,
        intent: TransformIntent,
        df_info: DataFrameInfo
    ) -> GenerationResult:
        """
        변환 의도에 맞는 Pandas 코드 생성
        
        Args:
            intent: 변환 의도
            df_info: DataFrame 메타 정보
            
        Returns:
            GenerationResult: 생성된 코드 및 메타데이터
        """
        # 프롬프트 생성
        prompt = self.CODE_GENERATION_PROMPT.format(
            description=intent.description,
            columns=", ".join(df_info.columns),
            dtypes=json.dumps(df_info.dtypes, ensure_ascii=False),
            sample_data=json.dumps(df_info.sample_data, ensure_ascii=False) if df_info.sample_data else "없음"
        )
        
        # 코드 생성
        code = await self.llm.generate(prompt)
        code = self._clean_code(code)
        
        # 안전성 검사
        is_safe, warnings = CodeSanitizer.is_safe(code)
        
        # 필요한 import 추출
        required_imports = self._extract_imports(code)
        
        # 설명 생성
        explanation = await self._generate_explanation(code)
        
        return GenerationResult(
            code=code,
            explanation_ko=explanation,
            required_imports=required_imports,
            is_safe=is_safe,
            warnings=warnings
        )
    
    def execute_safely(
        self,
        code: str,
        dataframe: "pd.DataFrame",
        timeout_seconds: float = 30.0
    ) -> ExecutionResult:
        """
        안전한 환경에서 코드 실행
        
        Args:
            code: 실행할 Pandas 코드
            dataframe: 입력 DataFrame
            timeout_seconds: 타임아웃 (초)
            
        Returns:
            ExecutionResult: 실행 결과
        """
        if not PANDAS_AVAILABLE:
            return ExecutionResult(
                success=False,
                error="Pandas가 설치되어 있지 않습니다."
            )
        
        # 안전성 재검사
        is_safe, warnings = CodeSanitizer.is_safe(code)
        if not is_safe:
            return ExecutionResult(
                success=False,
                error=f"안전하지 않은 코드: {', '.join(warnings)}"
            )
        
        import time
        start_time = time.time()
        
        try:
            # 제한된 네임스페이스에서 실행
            namespace = {
                "df": dataframe,
                "pd": pd,
                "np": np,
                "result_df": None,
            }
            
            # 코드 실행
            exec(code, namespace)
            
            result_df = namespace.get("result_df")
            
            if result_df is None:
                return ExecutionResult(
                    success=False,
                    error="result_df 변수가 정의되지 않았습니다."
                )
            
            if not isinstance(result_df, pd.DataFrame):
                return ExecutionResult(
                    success=False,
                    error="result_df가 DataFrame이 아닙니다."
                )
            
            # 결과 정보 생성
            result_info = DataFrameInfo(
                columns=list(result_df.columns),
                dtypes={col: str(dtype) for col, dtype in result_df.dtypes.items()},
                shape=result_df.shape
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            return ExecutionResult(
                success=True,
                result_info=result_info,
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return ExecutionResult(
                success=False,
                error=str(e),
                execution_time_ms=execution_time
            )
    
    async def _generate_explanation(self, code: str) -> str:
        """코드 설명 생성"""
        prompt = self.EXPLANATION_PROMPT.format(code=code)
        
        try:
            explanation = await self.llm.generate(prompt)
            return explanation.strip()
        except Exception:
            return "코드 설명을 생성할 수 없습니다."
    
    def _clean_code(self, code: str) -> str:
        """코드 정리"""
        code = code.strip()
        
        # 마크다운 코드 블록 제거
        if code.startswith("```"):
            lines = code.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            code = "\n".join(lines)
        
        return code.strip()
    
    def _extract_imports(self, code: str) -> List[str]:
        """코드에서 import 문 추출"""
        import re
        
        imports = []
        
        # import xxx
        import_matches = re.findall(r'^import\s+(\w+)', code, re.MULTILINE)
        imports.extend(import_matches)
        
        # from xxx import yyy
        from_matches = re.findall(r'^from\s+(\w+)', code, re.MULTILINE)
        imports.extend(from_matches)
        
        return list(set(imports))


# 팩토리 함수
def create_pandas_generator(llm: Optional[LLMProvider] = None) -> PandasGenerator:
    """PandasGenerator 인스턴스 생성"""
    return PandasGenerator(llm)


if __name__ == "__main__":
    import asyncio
    
    async def main():
        if not PANDAS_AVAILABLE:
            print("Pandas가 설치되어 있지 않습니다.")
            return
        
        generator = PandasGenerator()
        
        # 테스트용 DataFrame 정보
        df_info = DataFrameInfo(
            columns=["date", "product", "category", "amount", "quantity"],
            dtypes={
                "date": "datetime64[ns]",
                "product": "object",
                "category": "object",
                "amount": "float64",
                "quantity": "int64"
            },
            shape=(1000, 5),
            sample_data={
                "date": ["2024-01-01", "2024-01-02"],
                "product": ["A", "B"],
                "category": ["Electronics", "Clothing"],
                "amount": [100.0, 200.0],
                "quantity": [5, 10]
            }
        )
        
        # 변환 의도
        intent = TransformIntent(
            description="카테고리별 월간 매출 합계를 피벗 테이블로 만들어줘",
            transform_type=TransformationType.PIVOT,
            input_columns=["date", "category", "amount"]
        )
        
        # 코드 생성
        result = await generator.generate_transform_code(intent, df_info)
        
        print(f"생성된 코드:\n{result.code}")
        print(f"\n설명: {result.explanation_ko}")
        print(f"안전: {result.is_safe}")
        if result.warnings:
            print(f"경고: {result.warnings}")
    
    asyncio.run(main())
