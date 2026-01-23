# T1: Tableau Meta JSON Schema Design - Architectural Decisions

> Date: 2026-01-23
> Task: T1 - Tableau Meta JSON Schema Design

---

## Decision 1: Dataclass vs Dictionary

**Context**: Need to represent structured metadata

**Options Considered**:
1. Python dictionaries (dynamic, flexible)
2. Dataclasses (type-safe, structured)
3. Pydantic models (validation, serialization)

**Decision**: Use Python `@dataclass`

**Rationale**:
- Type safety without external dependencies
- Clean syntax with automatic `__init__`
- IDE autocomplete support
- Sufficient for MVP (no complex validation needed)
- Easy to upgrade to Pydantic later if needed

**Trade-offs**:
- Less flexible than raw dicts
- No automatic validation (manual checks required)
- But: Better code readability and maintainability

---

## Decision 2: Schema Separation vs Extension

**Context**: Need to add Meta JSON conversion to existing engine

**Options Considered**:
1. Modify `TableauMetadataEngine` directly
2. Create subclass `TableauMetaSchemaEngine`
3. Create separate `TableauMetaSchemaEngine` and integrate via composition

**Decision**: Option 3 - Separate module with integration

**Rationale**:
- Preserves existing code (no breaking changes)
- Clear separation of concerns
- Easier to test independently
- Can be used standalone or integrated
- Future-proof for other BI tools

**Implementation**:
```python
# Existing engine enhanced with new method
class TableauMetadataEngine:
    def to_meta_json(self):
        schema_engine = TableauMetaSchemaEngine(self.file_path)
        return schema_engine.to_meta_json()
```

---

## Decision 3: Field Type Simplification

**Context**: Tableau uses many datatype variants

**Options Considered**:
1. Preserve all Tableau datatypes exactly
2. Map to simplified set (string, number, date, boolean)
3. Use database-style types (varchar, int, timestamp)

**Decision**: Option 2 - Simplified types

**Rationale**:
- Cross-tool compatibility (Tableau, Power BI, Looker)
- Easier for LLM to understand and generate
- Sufficient granularity for MVP use cases
- Reduces complexity in downstream processing

**Mapping**:
```python
Tableau XML        → Meta JSON
---------------------------------
string, text       → string
integer, real      → number
date, datetime     → date
boolean            → boolean
```

---

## Decision 4: Worksheet Detection Strategy

**Context**: Need to extract visualization metadata from XML

**Options Considered**:
1. Full XML schema parsing (complex, accurate)
2. Heuristic-based text parsing (simple, may miss cases)
3. Skip worksheets for MVP

**Decision**: Option 2 - Heuristic parsing with known limitations

**Rationale**:
- MVP focus: Speed over completeness
- Covers 80% of common cases
- Known limitations documented
- Can enhance later with full parser
- Simplifies initial implementation

**Known Gaps**:
- Complex shelf configurations may be missed
- Calculated fields in shelves not fully detected
- Good enough for MVP validation

---

## Decision 5: Connection Type Detection

**Context**: Need to identify datasource connection types

**Options Considered**:
1. Comprehensive connection class mapping
2. Simple keyword matching with fallback
3. Store raw XML connection class

**Decision**: Option 2 - Keyword matching with "unknown" fallback

**Rationale**:
- Most common types covered (postgres, mysql, excel)
- Graceful degradation for unknown types
- Simpler implementation
- Type can be corrected manually if needed

**Implementation**:
```python
type_mapping = {
    'postgres': 'postgres',
    'mysql': 'mysql',
    'excel': 'excel',
    'snowflake': 'snowflake',
    # ... extensible
}
# Default: 'unknown'
```

---

## Decision 6: JSON Output Format

**Context**: Need to choose JSON serialization approach

**Options Considered**:
1. Flat structure (all fields at top level)
2. Nested structure (grouped by entity type)
3. Array of heterogeneous objects

**Decision**: Option 2 - Nested hierarchical structure

**Rationale**:
- Mirrors Tableau's conceptual model
- Clear ownership (datasource → fields)
- Easy to navigate and understand
- Aligns with natural language descriptions
- Extensible for additional metadata

**Schema**:
```json
{
  "version": "1.0",
  "tool": "tableau",
  "datasources": [...],
  "worksheets": [...],
  "calculated_fields": [...]
}
```

---

## Decision 7: Error Handling Strategy

**Context**: XML parsing may encounter missing or malformed data

**Options Considered**:
1. Strict validation (fail on any issue)
2. Permissive parsing (use defaults, warn)
3. Hybrid (strict on critical fields, permissive on optional)

**Decision**: Option 2 - Permissive with defaults

**Rationale**:
- MVP prioritizes functionality over perfection
- Real-world .twb files may have variations
- Better user experience (partial success vs total failure)
- Warnings can be added in next iteration

**Examples**:
- Missing connection → `type: "unknown"`
- Missing caption → `caption: None` (omitted in JSON)
- Missing role → `role: "dimension"` (default)

---

## Decision 8: Helper Function API

**Context**: Need convenient API for common use case

**Options Considered**:
1. Class-only API (must instantiate engine)
2. Function API with optional class usage
3. CLI tool

**Decision**: Option 2 - Both function and class API

**Rationale**:
- Function for quick one-liners: `twb_to_meta_json(path)`
- Class for advanced usage: `engine.to_meta_json()`
- Flexibility for different user needs
- CLI can be added later if needed

**Usage**:
```python
# Quick conversion
meta = twb_to_meta_json("input.twb", "output.json")

# Advanced usage
engine = TableauMetaSchemaEngine("input.twb")
meta = engine.to_meta_json()
# ... custom processing ...
meta.save("output.json")
```

---

## Decision 9: Test Strategy

**Context**: Need to validate implementation

**Options Considered**:
1. Unit tests only (fast, limited coverage)
2. Integration tests only (realistic, slower)
3. Comprehensive suite (unit + integration + demo)

**Decision**: Option 3 - Comprehensive test suite

**Rationale**:
- Unit tests validate individual components
- Integration tests validate XML conversion
- Demo scripts serve as documentation
- Builds confidence for future changes
- Total coverage: 10 test cases

**Test Categories**:
- Dataclass creation and serialization
- XML parsing and conversion
- Schema validation
- File I/O operations
- Real-world usage patterns

---

## Decision 10: Unicode and Localization

**Context**: Need to handle Korean captions and labels

**Options Considered**:
1. ASCII-only (simple, limited)
2. Full Unicode support
3. Configurable encoding

**Decision**: Option 2 - Full Unicode with `ensure_ascii=False`

**Rationale**:
- Project uses Korean field names (주문일자, 매출액)
- Modern JSON parsers handle Unicode well
- No technical reason to restrict
- Better user experience for non-English users

**Implementation**:
```python
json.dumps(data, ensure_ascii=False, indent=2)
```

---

## Decision Summary Table

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Data Structure | Dataclass | Type safety, clean syntax |
| Code Organization | Separate module + integration | Separation of concerns |
| Type System | Simplified (4 types) | Cross-tool compatibility |
| Worksheet Detection | Heuristic parsing | MVP speed, 80% coverage |
| Connection Types | Keyword matching | Covers common cases |
| JSON Format | Nested hierarchical | Clear, extensible |
| Error Handling | Permissive with defaults | Better UX |
| API Design | Function + class | Flexibility |
| Testing | Comprehensive suite | Confidence, documentation |
| Localization | Full Unicode | Real-world requirements |

---

## Future Decision Points

These decisions may need revisiting post-MVP:

1. **Validation Layer**: Add Pydantic for schema validation?
2. **Worksheet Parser**: Implement full XML schema parser?
3. **Connection Discovery**: Auto-detect connection parameters?
4. **Calculated Fields**: Parse and validate formulas?
5. **CLI Tool**: Add command-line interface?

---

## Impact on Downstream Tasks

These decisions affect:

- **T2 (Intent Parser)**: Can rely on simplified type system
- **T5 (Meta Generator)**: Uses this schema as output format
- **T6 (TUI Preview)**: Can render JSON directly
- **Future BI Tools**: Pattern established for Power BI, Looker

---

## Lessons Learned

1. **Separation of Concerns**: Keeping schema separate from parsing pays off
2. **MVP Mindset**: Heuristics are OK when limitations are documented
3. **Test Early**: Comprehensive tests caught edge cases early
4. **Unicode Matters**: Don't assume English-only environments
5. **API Flexibility**: Both simple and advanced APIs serve different needs
