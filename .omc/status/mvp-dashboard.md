# MVP Development Dashboard

**Updated**: 2026-01-23 (Auto-updated by Ultrawork)
**Timeline**: 1 Week Sprint
**Mode**: Ultrawork (Maximum Parallel Execution)

---

## 🎯 Sprint Objective
**"자연어 질문 → Tableau Meta JSON 생성"** End-to-End Pipeline

---

## 📊 Overall Progress

| Phase | Tasks | Status | Progress |
|-------|-------|--------|----------|
| **Day 1-2: Foundation** | T1, T2, T3 | 🔄 In Progress | 3/3 running |
| **Day 3-4: Integration** | T5, T6 | ⏳ Blocked | 0/2 started |
| **Day 5-7: Testing** | T7, T8 | ⏳ Blocked | 0/2 started |
| **Optional** | T4 | 📋 Pending | 0/1 started |

**Overall**: 3/8 tasks active (37.5% in execution)

---

## 🚀 Active Parallel Execution (Day 1-2)

### Agent a38d292: T1 - Tableau Meta JSON Schema
- **Owner**: Claude (Backend/Logic)
- **Status**: 🔄 Running
- **Priority**: P0 (MUST HAVE)
- **Model**: Sonnet
- **Deliverable**: `backend/agents/bi_tool/tableau_meta_schema.py`
- **Blocks**: T5 (Meta Generation Pipeline)
- **Progress**: Active development

### Agent a35d5d6: T2 - Natural Language Intent Parser
- **Owner**: Claude (Backend/Logic)
- **Status**: 🔄 Running
- **Priority**: P0 (MUST HAVE)
- **Model**: Sonnet
- **Deliverable**: `backend/agents/bi_tool/nl_intent_parser.py`
- **Blocks**: T5 (Meta Generation Pipeline)
- **Progress**: Active development

### Agent a4349d1: T3 - RAG Knowledge Base
- **Owner**: Antigravity (UX/Orchestration)
- **Status**: 🔄 Running
- **Priority**: P1 (IMPORTANT)
- **Model**: Sonnet
- **Deliverables**:
  - `backend/agents/bi_tool/rag_knowledge.py`
  - `backend/data/knowledge_base/tableau/*.md` (5+ files)
- **Blocks**: T6 (TUI Meta Preview)
- **Progress**: Active development

---

## 📋 Task Dependency Graph

```
Day 1-2 (Foundation - PARALLEL):
┌─────────┐     ┌─────────┐     ┌─────────┐
│   T1    │     │   T2    │     │   T3    │
│ Schema  │     │ Intent  │     │  RAG    │
│ Design  │     │ Parser  │     │  KB     │
└────┬────┘     └────┬────┘     └────┬────┘
     │               │               │
     └───────┬───────┘               │
             │                       │
Day 3-4 (Integration):              │
             │                       │
        ┌────▼────┐             ┌────▼────┐
        │   T5    │             │   T6    │
        │Pipeline │────────────▶│   TUI   │
        │  Core   │             │ Preview │
        └────┬────┘             └────┬────┘
             │                       │
             └───────┬───────────────┘
                     │
Day 5-7 (Testing):   │
                     │
                ┌────▼────┐
                │   T7    │
                │  E2E    │
                │ Testing │
                └────┬────┘
                     │
                ┌────▼────┐
                │   T8    │
                │  Demo   │
                │  Prep   │
                └─────────┘
```

---

## ✅ Success Criteria Tracking

### MVP Complete When:

- [ ] **Functional**: TUI에서 "월별 매출 차트 만들어줘" 입력 시 유효한 Tableau Meta JSON 생성
- [ ] **Visual**: JSON이 syntax-highlighted로 표시
- [ ] **Exportable**: 생성된 JSON을 파일로 저장 가능
- [ ] **Stable**: Happy path에서 에러 없이 작동

### Current Status:
- Foundation tasks (T1, T2, T3): In progress
- Integration tasks: Not started (blocked by foundation)
- Testing: Not started (blocked by integration)

---

## 📁 Expected File Changes

### New Files (8 total)
- [ ] `backend/agents/bi_tool/tableau_meta_schema.py` (T1)
- [ ] `backend/agents/bi_tool/nl_intent_parser.py` (T2)
- [ ] `backend/agents/bi_tool/rag_knowledge.py` (T3)
- [ ] `backend/agents/bi_tool/meta_generator.py` (T5)
- [ ] `backend/orchestrator/tui_meta_preview.py` (T6)
- [ ] `backend/data/knowledge_base/tableau/*.md` (T3 - 5+ files)
- [ ] `backend/tests/test_mvp_e2e.py` (T7)
- [ ] `backend/agents/bi_tool/pbi_meta_schema.py` (T4 - Optional)

### Modified Files (3-4 total)
- [ ] `backend/orchestrator/interaction_orchestrator.py` (T5)
- [ ] `backend/agents/bi_tool/guide_assistant.py` (T3)
- [ ] `backend/main.py` (T6)
- [ ] `backend/agents/bi_tool/tableau_metadata.py` (T1 - extend)

---

## ⚠️ Risk Dashboard

| Risk | Status | Mitigation |
|------|--------|------------|
| LLM API rate limit | 🟡 Medium | Ollama fallback active |
| Tableau XML complexity | 🟢 Low | MVP scope limited to basics |
| DB schema lookup failure | 🟢 Low | Mock data fallback ready |
| Time constraint (1 week) | 🟡 Medium | P2 tasks (T4) can be skipped |
| Agent task failure | 🟢 Low | 3 agents running in parallel |

---

## 🎯 Next Actions (Auto-triggered)

**When T1, T2, T3 complete:**
1. ✅ Verify all foundation tasks passed
2. 🚀 Launch T5 (Pipeline) - depends on T1 + T2
3. 🚀 Launch T6 (TUI Preview) - depends on T3 + T5
4. 📊 Update dashboard

**Mid-Week Checkpoint (Day 3):**
- [ ] T1 (Schema) 100% complete
- [ ] T2 (Intent Parser) 100% complete
- [ ] T3 (RAG) 100% complete
- [ ] T5 (Pipeline) 80%+ complete

**If checkpoint fails:** Drop T4 (Power BI), focus all resources on P0 tasks.

---

## 📈 Metrics

### Token Usage (Estimated)
- T1, T2, T3 agents: ~40K tokens consumed
- Remaining budget: ~146K tokens
- Burn rate: Healthy ✅

### Timeline Confidence
- **Day 1-2**: 90% confidence (parallel execution active)
- **Day 3-4**: 80% confidence (depends on T1-T3 success)
- **Day 5-7**: 70% confidence (contingency time built-in)

---

## 💡 Prepared Resources

### Integration Specs Ready:
- ✅ T5 Integration Notes: `.omc/plans/t5-integration-notes.md`
- ✅ T6 TUI Preview Spec: `.omc/drafts/t6-tui-preview-spec.md`

### Master Plan:
- ✅ Full MVP Plan: `.omc/plans/mvp-bi-meta-json.md`

---

**Last Updated**: 2026-01-23 02:45 UTC
**Mode**: Ultrawork Active
**Status**: On Track ✅
