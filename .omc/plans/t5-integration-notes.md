# T5: Meta Generation Pipeline - Integration Notes

## Integration Points Identified

### 1. InteractionOrchestrator Extension
**File**: `backend/orchestrator/interaction_orchestrator.py`

Current flow:
- `detect_intent()` determines "ask" vs "agent" mode
- `handle_request()` routes based on mode and tool_type

**New integration needed**:
```python
def handle_request(self, user_input: str, tool_type: str, mode: Optional[str] = None, context: Dict[str, Any] = None):
    # ... existing code ...

    if mode == "agent":
        # ADD NEW BRANCH for meta generation
        if action_type == "generate_meta":
            from backend.agents.bi_tool.meta_generator import MetaGenerator
            meta_gen = MetaGenerator(
                intent_parser=self.intent_parser,
                data_agent=context.get("data_agent"),
                tableau_engine=self.tableau_engine
            )
            meta_json = await meta_gen.generate(user_input, tool_type)
            result["response"] = meta_json
            result["meta_json"] = meta_json
```

### 2. DataSourceAgent Schema Lookup
**File**: `backend/agents/data_source/data_source_agent.py`

**Available method**:
- `query_database()` calls `list_tables` MCP tool at line 49
- Returns schema_info as text

**New method needed**:
```python
async def get_schema_info(self, connection_info: Dict[str, Any]) -> Dict[str, Any]:
    """Get structured schema information for meta generation"""
    client = await self.get_client(connection_info)
    schema_result = await client.call_tool("list_tables", config)
    # Parse and structure the schema
    return {
        "tables": [...],
        "columns": {...},
        "types": {...}
    }
```

### 3. Main TUI Loop
**File**: `backend/main.py`

Current flow (lines 88-100):
- User input via Prompt.ask()
- orchestrator.run() processes request
- Result display

**New integration**:
- Add command detection for "meta preview" and "meta save"
- Store last generated meta_json in context
- Display using Rich Panel with JSON syntax highlighting

### 4. Dependencies

**Available classes to reuse**:
- `TableauMetadataEngine` (will be extended by T1)
- `PBILogicGenerator` (stub in T4)
- `GuideAssistant` (will be extended by T3)
- `DataSourceAgent.query_database()` (schema lookup)
- `LangGraph` workflow from Orchestrator

**New classes from parallel tasks**:
- `TableauMetaSchema` (from T1)
- `NLIntentParser` (from T2)
- `RAGKnowledge` (from T3)

## Pipeline Architecture

```
┌─────────────────┐
│  User Input     │
│ "월별 매출 차트"  │
└────────┬────────┘
         │
         v
┌─────────────────────────┐
│  NLIntentParser (T2)    │
│  parse_intent()         │
└────────┬────────────────┘
         │ ChartIntent
         v
┌─────────────────────────┐
│  DataSourceAgent        │
│  get_schema_info()      │
└────────┬────────────────┘
         │ Schema Info
         v
┌─────────────────────────┐
│  MetaGenerator          │
│  - Match intent fields  │
│  - Apply business logic │
│  - Generate meta JSON   │
└────────┬────────────────┘
         │ Raw Meta JSON
         v
┌─────────────────────────┐
│  TableauMetaSchema (T1) │
│  validate & structure   │
└────────┬────────────────┘
         │ Validated Meta JSON
         v
┌─────────────────────────┐
│  Output / TUI Preview   │
└─────────────────────────┘
```

## Implementation Checklist for T5

- [ ] Create MetaGenerator class
- [ ] Implement intent-to-schema mapping
- [ ] Add field type inference (dimension vs measure)
- [ ] Add aggregation logic (SUM, AVG, COUNT)
- [ ] Implement visual type mapping (bar, line, pie, table)
- [ ] Add error handling for missing tables/columns
- [ ] Integrate with InteractionOrchestrator
- [ ] Add unit tests for pipeline flow
- [ ] Test with all 5 E2E scenarios

## Risk Mitigation

**Risk**: Schema lookup fails for invalid connection
**Mitigation**: Use mock schema fallback with common fields (id, name, date, value)

**Risk**: Intent parsing returns ambiguous results
**Mitigation**: Add confidence score, ask user for clarification if < 0.7

**Risk**: LLM fails completely
**Mitigation**: Hardcoded intent templates for common patterns
