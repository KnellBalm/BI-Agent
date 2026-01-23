import asyncio
from typing import Optional, Dict, Any
from backend.agents.bi_tool.nl_intent_parser import NLIntentParser, ChartIntent
from backend.agents.bi_tool.rag_knowledge import TableauRAGKnowledge
from backend.agents.bi_tool.tableau_meta_schema import (
    TableauMetaJSON, 
    TableauMetaSchemaEngine,
    WorksheetMeta,
    DatasourceMeta,
    ConnectionMeta,
    FieldMeta
)

class TableauMetaGenerator:
    """
    T5: Meta Generation Pipeline
    NL Intent + RAG Context -> Tableau Meta JSON 생성 엔진
    """
    def __init__(self):
        self.parser = NLIntentParser()
        self.rag = TableauRAGKnowledge()
        self.engine = TableauMetaSchemaEngine()

    async def generate_from_nl(self, user_input: str) -> TableauMetaJSON:
        """
        자연어 입력으로부터 전체 파이프라인을 실행하여 Meta JSON 객체를 반환합니다.
        """
        # 1. Intent Parsing (Claude's T2)
        intent = await self.parser.parse_intent(user_input)
        
        # 2. RAG Context Retrieval (Antigravity's Phase 1)
        # LLM이 스키마 구조를 정확히 지킬 수 있도록 RAG 컨텍스트를 활용 (향후 LLM 재호출 시 활용 가능)
        context = self.rag.get_prompt_context(user_input)
        
        # 3. Build Meta JSON using Schema (Claude's T1)
        # 현재는 Heuristic 방식으로 매핑하며, 복잡한 요청은 LLM + RAG Context로 재구성 가능
        meta = self._build_meta_from_intent(intent)
        
        return meta

    def _build_meta_from_intent(self, intent: ChartIntent) -> TableauMetaJSON:
        """
        추출된 의도를 바탕으로 TableauMetaJSON 객체를 조립합니다.
        """
        # 데이터소스 정의 (기본값 활용 가능)
        conn = ConnectionMeta(type="unknown", table=intent.datasource)
        fields = []
        for d in intent.dimensions:
            fields.append(FieldMeta(name=d, type="string", role="dimension"))
        for m in intent.measures:
            fields.append(FieldMeta(name=m, type="number", role="measure", aggregation=intent.aggregation or "SUM"))

        ds = DatasourceMeta(name=f"{intent.datasource}_datasource", connection=conn, fields=fields)

        # 워크시트 정의
        ws = WorksheetMeta(
            name=intent.title or "New Worksheet",
            visual_type=intent.visual_type,
            dimensions=intent.dimensions,
            measures=intent.measures,
            filters=intent.filters
        )

        return TableauMetaJSON(
            version="1.0",
            tool="tableau",
            datasources=[ds],
            worksheets=[ws],
            calculated_fields=[]
        )

    def generate_sync(self, user_input: str) -> TableauMetaJSON:
        """동기 래퍼"""
        return asyncio.run(self.generate_from_nl(user_input))
