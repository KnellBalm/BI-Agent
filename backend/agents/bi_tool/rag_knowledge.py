import os
import glob
from typing import Dict, List, Optional

class TableauRAGKnowledge:
    """
    Tableau Meta JSON 생성을 위한 RAG 지식 베이스 관리 엔진.
    사용자 의도에 따라 관련 가이드 문서(Chart, Filter, Calc)를 검색하여 컨텍스트를 제공합니다.
    """
    def __init__(self, kb_path: str = "backend/data/knowledge_base/tableau"):
        self.kb_path = kb_path
        self.guides = {}
        self._load_guides()

    def _load_guides(self):
        """마운트된 모든 마크다운 가이드 문서를 로드합니다."""
        files = glob.glob(os.path.join(self.kb_path, "*.md"))
        for file_path in files:
            name = os.path.basename(file_path).replace(".md", "")
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self.guides[name] = f.read()
            except Exception as e:
                print(f"Error loading guide {name}: {e}")

    def search_context(self, query: str) -> str:
        """
        사용자 쿼리와 관련된 가이드 내용을 검색합니다.
        (단순 키워드 매칭 PoC - 향후 벡터 검색으로 확장 가능)
        """
        query_lower = query.lower()
        relevant_parts = []

        # 1. 차트 관련
        if any(kw in query_lower for kw in ["차트", "그래프", "chart", "bar", "line"]):
            relevant_parts.append(self.guides.get("chart_guide", ""))
        
        # 2. 필터 관련
        if any(kw in query_lower for kw in ["필터", "filter", "제한", "추출"]):
            relevant_parts.append(self.guides.get("filter_guide", ""))
            
        # 3. 계산 필드 관련
        if any(kw in query_lower for kw in ["계산", "수식", "calc", "lod", "fixed"]):
            relevant_parts.append(self.guides.get("calc_field_guide", ""))

        if not relevant_parts:
            # 매칭되는 게 없으면 전체 요약 제공
            return "Tableau Meta JSON 생성을 위한 일반 가이드를 제공합니다.\n" + "\n".join(self.guides.values())[:1000]

        return "\n---\n".join([p for p in relevant_parts if p])

    def get_prompt_context(self, user_intent: str) -> str:
        """
        Claude의 파이프라인(T5)에 주입할 프롬프트 컨텍스트를 생성합니다.
        """
        context = self.search_context(user_intent)
        return f"### Tableau Guide Context ###\n{context}\n"
