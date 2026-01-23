import os
import glob
from typing import Dict, Any, List

class GuideAssistant:
    """
    사용자에게 BI 도구 조작법을 안내하는 가이드 에이전트 (Ask Mode)
    기본 지식 베이스와 RAG(문서 검색)를 병행하여 응답합니다.
    """
    def __init__(self, kb_path: str = "backend/data/knowledge_base"):
        self.kb_path = kb_path
        # 기본 PoC용 지식 베이스
        self.static_knowledge = {
            "tableau": {
                "change_color": "1. '마크' 카드의 '색상' 아이콘을 클릭합니다.\n2. '색상 편집'을 선택하고 원하는 팔레트를 지정하세요.",
                "add_filter": "1. 필드로 사용할 차원을 '필터' 선반으로 드래그합니다.\n2. 대화 상자에서 필터링할 값을 선택한 후 '확인'을 누르세요."
            },
            "powerbi": {
                "change_color": "1. '시각화' 창에서 '서식(브러시 아이콘)' 탭을 선택합니다.\n2. '데이터 색상' 또는 '기본 색상' 항목을 찾아 변경하세요.",
                "add_filter": "1. '필터' 창의 '이 페이지의 필터' 영역으로 필드를 드래그합니다.\n2. 필터 유형을 선택하고 조건을 설정하세요."
            }
        }

    def _search_docs(self, tool_type: str, query: str) -> str:
        """
        문서 저장소에서 관련 내용을 검색합니다. (단순 키워드 매칭 PoC)
        """
        doc_path = os.path.join(self.kb_path, tool_type.lower(), "*.md")
        files = glob.glob(doc_path)
        
        relevant_content = []
        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # 단순 키워드 포함 여부 확인 (향후 임베딩 기반 검색으로 확장 가능)
                    if query.lower().replace("_", " ") in content.lower():
                        relevant_content.append(content)
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
        
        return "\n---\n".join(relevant_content) if relevant_content else ""

    def generate_ui_guide(self, tool_type: str, action_type: str, context: Dict[str, Any] = None) -> str:
        """
        특정 BI 도구와 액션에 대한 UI 가이드를 생성합니다.
        """
        tool = tool_type.lower()
        
        # 1. 정적 지식 베이스 확인
        base_guide = self.static_knowledge.get(tool, {}).get(action_type, "")
        
        # 2. 문서 기반 RAG 검색
        doc_guide = self._search_docs(tool, action_type)
        
        final_guide = ""
        if doc_guide:
            final_guide = f"[문서 검색 결과]\n{doc_guide}"
        elif base_guide:
            final_guide = f"[시스템 가이드]\n{base_guide}"
        else:
            final_guide = f"{tool_type}의 해당 조작에 대한 상세 정보를 찾을 수 없습니다."
        
        if context and "target_name" in context:
            final_guide = f"'{context['target_name']}' 요소를 기준으로 가이드를 제공합니다:\n\n" + final_guide
            
        return final_guide

    def analyze_metadata_and_suggest(self, metadata: Dict[str, Any]) -> List[str]:
        """
        메타데이터를 분석하여 사용자에게 필요한 UI 조작을 제안합니다.
        """
        suggestions = []
        if not metadata.get("visual") and metadata.get("datamodel"):
            suggestions.append("데이터 모델이 준비되었습니다. '레포트' 화면에서 차트를 추가해 보는 것은 어떨까요?")
            
        return suggestions
