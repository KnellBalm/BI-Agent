# Tableau Meta JSON Schema - Quick Reference

## Overview

The Tableau Meta JSON Schema provides a standardized JSON format for representing Tableau workbook metadata, enabling programmatic analysis, generation, and modification of BI dashboards.

---

## Quick Start

### Basic Conversion

```python
from agents.bi_tool.tableau_meta_schema import twb_to_meta_json

# Convert .twb to Meta JSON
meta = twb_to_meta_json("workbook.twb", "output.json")
print(meta.to_json())
```

### Using Existing Engine

```python
from agents.bi_tool.tableau_metadata import TableauMetadataEngine

# Load and convert
engine = TableauMetadataEngine("workbook.twb")
meta = engine.to_meta_json()
meta.save("output.json")
```

### Creating from Scratch

```python
from agents.bi_tool.tableau_meta_schema import (
    TableauMetaJSON,
    DatasourceMeta,
    ConnectionMeta,
    FieldMeta,
    WorksheetMeta
)

# Define connection
connection = ConnectionMeta(
    type="postgres",
    table="sales",
    database="analytics"
)

# Define fields
fields = [
    FieldMeta(name="OrderDate", type="date", role="dimension"),
    FieldMeta(name="Sales", type="number", role="measure", aggregation="SUM")
]

# Create datasource
datasource = DatasourceMeta(
    name="SalesData",
    connection=connection,
    fields=fields
)

# Create worksheet
worksheet = WorksheetMeta(
    name="Monthly Sales",
    visual_type="bar",
    dimensions=["OrderDate"],
    measures=["Sales"]
)

# Assemble Meta JSON
meta = TableauMetaJSON(
    version="1.0",
    tool="tableau",
    datasources=[datasource],
    worksheets=[worksheet],
    calculated_fields=[]
)

# Save
meta.save("sales_dashboard.json")
```

---

## Schema Reference

### TableauMetaJSON (Root)

```json
{
  "version": "1.0",
  "tool": "tableau",
  "datasources": [...],
  "worksheets": [...],
  "calculated_fields": [...]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Schema version (currently "1.0") |
| `tool` | string | BI tool identifier ("tableau") |
| `datasources` | array | List of datasource definitions |
| `worksheets` | array | List of worksheet/visualization definitions |
| `calculated_fields` | array | List of calculated field definitions |

---

### DatasourceMeta

```json
{
  "name": "SalesData",
  "connection": {...},
  "fields": [...]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Datasource name |
| `connection` | object | Connection configuration |
| `fields` | array | List of field definitions |

---

### ConnectionMeta

```json
{
  "type": "postgres",
  "table": "sales",
  "database": "analytics",
  "server": "localhost:5433"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | Connection type (postgres, mysql, excel, etc.) |
| `table` | string | No | Table name |
| `database` | string | No | Database name |
| `server` | string | No | Server address |

**Supported Types**:
- `postgres`, `mysql`, `sqlserver`
- `excel`, `csv`
- `snowflake`, `bigquery`
- `unknown` (fallback)

---

### FieldMeta

```json
{
  "name": "Sales",
  "type": "number",
  "role": "measure",
  "aggregation": "SUM",
  "caption": "매출액"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Field name |
| `type` | string | Yes | Data type (string, number, date, boolean) |
| `role` | string | Yes | Field role (dimension, measure) |
| `aggregation` | string | No | Aggregation function (SUM, AVG, COUNT, MIN, MAX) |
| `caption` | string | No | Display caption (supports Unicode) |

---

### WorksheetMeta

```json
{
  "name": "Monthly Sales",
  "visual_type": "bar",
  "dimensions": ["OrderDate"],
  "measures": ["Sales"],
  "filters": [...]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Worksheet name |
| `visual_type` | string | Yes | Visualization type |
| `dimensions` | array | Yes | List of dimension field names |
| `measures` | array | Yes | List of measure field names |
| `filters` | array | No | List of filter definitions |

**Visual Types**:
- `bar`, `line`, `area`, `pie`
- `scatter`, `table`, `map`

---

### CalculatedFieldMeta

```json
{
  "name": "Profit Margin",
  "formula": "SUM([Profit]) / SUM([Sales])",
  "type": "number",
  "role": "measure"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Calculated field name |
| `formula` | string | Yes | Tableau formula |
| `type` | string | Yes | Result data type |
| `role` | string | Yes | Field role |

---

## Common Patterns

### Time Series Analysis

```python
WorksheetMeta(
    name="Sales Trend",
    visual_type="line",
    dimensions=["Date"],
    measures=["Sales"],
    filters=[{"field": "Date", "type": "date_range"}]
)
```

### Category Comparison

```python
WorksheetMeta(
    name="Category Performance",
    visual_type="bar",
    dimensions=["Category"],
    measures=["Sales", "Profit"]
)
```

### Detailed Table

```python
WorksheetMeta(
    name="Sales Detail",
    visual_type="table",
    dimensions=["Region", "Category", "Product"],
    measures=["Sales", "Quantity", "Profit"]
)
```

### Scatter Plot

```python
WorksheetMeta(
    name="Price vs Quantity",
    visual_type="scatter",
    dimensions=["Product"],
    measures=["Price", "Quantity"]
)
```

---

## API Reference

### TableauMetaSchemaEngine

**Constructor**:
```python
engine = TableauMetaSchemaEngine(file_path: Optional[str])
```

**Methods**:
- `to_meta_json() -> TableauMetaJSON` - Convert loaded .twb to Meta JSON
- `create_empty_meta() -> TableauMetaJSON` (static) - Create empty template
- `create_sample_meta() -> TableauMetaJSON` (static) - Create sample data

### TableauMetaJSON

**Methods**:
- `to_dict() -> Dict[str, Any]` - Convert to dictionary
- `to_json(indent: int = 2) -> str` - Convert to JSON string
- `save(file_path: str)` - Save to JSON file

### Helper Functions

```python
# One-line conversion
meta = twb_to_meta_json(
    twb_path: str,
    output_path: Optional[str] = None
) -> TableauMetaJSON
```

---

## Testing

### Run Tests

```bash
# Comprehensive test suite
python3 backend/tests/test_tableau_meta_schema.py

# Demonstration scripts
python3 backend/tests/demo_tableau_meta_schema.py
```

### Example Test

```python
from agents.bi_tool.tableau_meta_schema import TableauMetaSchemaEngine

# Test sample creation
meta = TableauMetaSchemaEngine.create_sample_meta()
assert meta.version == "1.0"
assert len(meta.datasources) > 0

# Test conversion
engine = TableauMetaSchemaEngine("test.twb")
meta = engine.to_meta_json()
assert meta.tool == "tableau"
```

---

## File Structure

```
backend/agents/bi_tool/
├── tableau_metadata.py           # Original engine (enhanced)
├── tableau_meta_schema.py        # Meta JSON schema and conversion
└── README_META_SCHEMA.md         # This file

backend/tests/
├── test_tableau_meta_schema.py   # Test suite (10 tests)
└── demo_tableau_meta_schema.py   # Usage demonstrations
```

---

## Known Limitations (MVP)

1. **Worksheet Detection**: Heuristic-based, may miss complex configurations
2. **Connection Types**: Limited type detection, defaults to "unknown"
3. **Calculated Fields**: Basic formula extraction, no validation
4. **Filters**: Simplified structure, no complex expressions

These limitations are documented and acceptable for MVP phase.

---

## Unicode Support

Full Unicode support for multilingual captions:

```python
FieldMeta(
    name="OrderDate",
    type="date",
    role="dimension",
    caption="주문일자"  # Korean caption
)
```

---

## Error Handling

The engine uses permissive parsing with sensible defaults:

- Missing connection → `type: "unknown"`
- Missing caption → Omitted from JSON
- Missing role → `role: "dimension"` (default)
- Unknown visual type → `visual_type: "table"` (default)

---

## Examples

See comprehensive examples in:
- `backend/tests/test_tableau_meta_schema.py` - Test cases
- `backend/tests/demo_tableau_meta_schema.py` - Real-world demos

---

## Integration Points

### Current

- `TableauMetadataEngine.to_meta_json()` - Integrated method
- Standalone usage via `TableauMetaSchemaEngine`

### Future (Per MVP Plan)

- **T2 (NL Intent Parser)**: Uses schema for validation
- **T5 (Meta Generator)**: Generates Meta JSON from natural language
- **T6 (TUI Preview)**: Displays generated Meta JSON

---

## Contributing

When extending the schema:

1. Add new fields to dataclasses
2. Update `to_dict()` methods
3. Add tests to `test_tableau_meta_schema.py`
4. Update this documentation

---

## Version History

- **1.0** (2026-01-23): Initial release
  - Core schema definition
  - XML to JSON conversion
  - Integration with existing engine
  - Comprehensive test suite

---

## Support

For issues or questions:
1. Check existing tests for examples
2. Review demo scripts
3. See `.omc/notepads/mvp-bi-meta-json/learnings.md` for patterns

---

**Last Updated**: 2026-01-23
**Status**: MVP Complete ✓
