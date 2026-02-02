# T1: Tableau Meta JSON Schema Design - Learnings

> Date: 2026-01-23
> Task: T1 - Tableau Meta JSON Schema Design
> Status: Completed

---

## Key Technical Decisions

### 1. Schema Structure
- **Dataclass-based Design**: Used Python `@dataclass` for clean, type-safe data structures
- **Hierarchical Organization**: Top-level `TableauMetaJSON` contains `DatasourceMeta`, `WorksheetMeta`, and `CalculatedFieldMeta`
- **Flexibility**: Optional fields using `Optional[T]` for backward compatibility

### 2. XML to JSON Conversion
- **Separation of Concerns**: Created `TableauMetaSchemaEngine` as standalone module, separate from existing `TableauMetadataEngine`
- **Integration Pattern**: Extended existing engine via composition (not inheritance) using import and delegation
- **Graceful Degradation**: Handles missing XML elements with sensible defaults

### 3. Field Type Mapping
Tableau XML datatypes mapped to simplified types:
```python
{
    'string': 'string',
    'integer': 'number',
    'real': 'number',
    'date': 'date',
    'datetime': 'date',
    'boolean': 'boolean'
}
```

### 4. Visual Type Detection
Mark class mapping for visualization types:
```python
{
    'bar': 'bar',
    'line': 'line',
    'circle': 'scatter',
    'square': 'table',
    'pie': 'pie',
    'area': 'area',
    'text': 'table',
    'automatic': 'bar'  # default
}
```

---

## Implementation Patterns

### 1. to_dict() Methods
Every dataclass implements `to_dict()` for JSON serialization:
- Excludes `None` values for cleaner output
- Recursive conversion for nested objects
- Maintains Korean caption support with `ensure_ascii=False`

### 2. Static Factory Methods
- `create_empty_meta()`: Empty template for new dashboards
- `create_sample_meta()`: Sample data for testing/demos
- Benefits: Clear API, testability, documentation by example

### 3. Helper Functions
Global utility function `twb_to_meta_json()` for one-line conversion:
```python
meta = twb_to_meta_json("input.twb", "output.json")
```

---

## Testing Strategy

### Test Coverage Areas
1. **Unit Tests**: Individual dataclass creation and validation
2. **Integration Tests**: XML parsing and conversion
3. **Schema Validation**: JSON structure compliance
4. **End-to-End**: File I/O operations
5. **Demo Scripts**: Real-world usage patterns

### Test Results
- 10/10 tests passed
- All syntax checks clean
- Successfully tested with existing `tmp/test.twb`

---

## Code Quality Patterns

### 1. Docstrings
- Module-level documentation
- Class and method docstrings with examples
- Type hints throughout

### 2. Error Handling
- Graceful fallback for missing XML elements
- Clear error messages for invalid inputs
- Validation in conversion methods

### 3. Maintainability
- Separated concerns (schema vs. conversion)
- Extensible for future BI tools (Power BI, Looker)
- Clean imports with fallback handling

---

## Reusable Components

### 1. Meta Schema Pattern
Can be adapted for other BI tools:
```python
@dataclass
class PowerBIMetaJSON:
    version: str
    tool: str = "powerbi"
    tables: List[TableMeta]
    measures: List[MeasureMeta]
    visuals: List[VisualMeta]
```

### 2. Conversion Engine Pattern
Template for other XML/JSON conversions:
1. Load source format
2. Extract structured data
3. Map to standard schema
4. Serialize to target format

---

## Performance Considerations

### Current Implementation
- In-memory XML parsing (ElementTree)
- No caching (stateless conversion)
- Single-pass extraction

### Future Optimizations
- Stream parsing for large .twb files
- Cached schema lookups
- Parallel field extraction

---

## Integration Points

### Existing Codebase
- `TableauMetadataEngine`: Extended with `to_meta_json()` method
- Backward compatible: All existing methods preserved
- Import safety: Try/except for standalone usage

### Future Integration
- `NLIntentParser` (T2): Will use schema for validation
- `MetaGenerator` (T5): Primary consumer of Meta JSON
- `TUI Preview` (T6): Display generated Meta JSON

---

## File Structure

```
backend/agents/bi_tool/
├── tableau_metadata.py          # Enhanced with to_meta_json()
├── tableau_meta_schema.py       # NEW: Core schema engine
└── (future) pbi_meta_schema.py  # Power BI variant

backend/tests/
├── test_tableau_meta_schema.py  # Comprehensive test suite
└── demo_tableau_meta_schema.py  # Usage demonstrations
```

---

## Known Limitations (MVP)

1. **Worksheet Detection**: Simple heuristic for dimensions/measures
   - Parses from rows/cols text content
   - May miss complex shelf configurations

2. **Connection Types**: Limited type detection
   - Relies on connection class name matching
   - Defaults to "unknown" for unrecognized types

3. **Calculated Fields**: Basic formula extraction
   - No validation of formula syntax
   - No dependency tracking

4. **Filters**: Simplified structure
   - Only captures field name and basic type
   - No support for complex filter expressions

---

## Success Metrics

- ✅ Meta JSON schema defined and documented
- ✅ `to_meta_json()` method implemented
- ✅ `create_empty_meta()` static method created
- ✅ Integration with existing `TableauMetadataEngine`
- ✅ Test extraction from `tmp/test.twb`
- ✅ JSON schema validation tests passing
- ✅ Comprehensive test suite (10 tests)
- ✅ Demo scripts for documentation

---

## Next Steps (Dependencies)

Task T1 is now complete and unblocks:
- **T5: Meta Generation Pipeline** - Will use this schema as output format
- **T2: NL Intent Parser** - Can reference schema structure for intent mapping

---

## Code Statistics

- **New Files**: 3 (schema engine, tests, demos)
- **Modified Files**: 1 (existing tableau_metadata.py)
- **Lines of Code**: ~900+ (including tests and demos)
- **Test Coverage**: 10 test cases
- **Documentation**: Extensive docstrings and comments
