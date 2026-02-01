# /backend/agents/bi_tool/base_intent.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

@dataclass
class BaseIntent(ABC):
    """BI-Agent의 모든 의도 타입에 대한 추상 베이스 클래스.

    공유 필드:
    - datasource: 대상 테이블/데이터셋 이름
    - filters: 필터 조건 리스트 [{field, operator, value}]
    - title: 선택적 설명 제목
    """
    datasource: str = ""
    filters: List[Dict[str, Any]] = None
    title: Optional[str] = None

    def __post_init__(self):
        """Initialize mutable default arguments"""
        if self.filters is None:
            self.filters = []

    @property
    @abstractmethod
    def intent_type(self) -> str:
        """의도 하위 타입을 식별하기 위해 'chart' 또는 'analysis' 반환"""
        pass

    @abstractmethod
    def validate(self) -> bool:
        """의도 구조 검증. 유효하면 True 반환"""
        pass

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 표현으로 변환"""
        return asdict(self)
