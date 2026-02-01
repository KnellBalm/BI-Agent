# BI-Agent Textual Screens

Interactive modal screens for BI-Agent workflows using the Textual framework.

## Overview

This module provides reusable modal screens for complex user interactions within the BI-Agent TUI. These screens enable rich, interactive data selection and configuration workflows.

## Components

### TableSelectionScreen

Interactive modal for selecting database tables from AI-generated recommendations.

**Features:**
- Display tables with relevance scores (0-100)
- Color-coded scores (green: 90+, yellow: 70-89, gray: <70)
- Korean explanations for each recommendation
- Relevant columns display
- JOIN relationship visualization
- Multi-select with checkbox toggle
- Schema preview in side panel
- Search/filter by table name
- Keyboard navigation

**Usage:**

```python
from backend.orchestrator.screens import TableSelectionScreen
from backend.agents.data_source.table_recommender import TableRecommender

# Get recommendations from TableRecommender
recommendations = await table_recommender.recommend_tables(intent)
relationships = await table_recommender.infer_relationships(table_names)

# Launch selection screen
def on_tables_selected(selected_tables: List[str]):
    print(f"User selected: {selected_tables}")

self.push_screen(
    TableSelectionScreen(
        recommendations=recommendations,
        relationships=relationships,
        callback=on_tables_selected
    )
)

# Or use async/await pattern
result = await self.app.push_screen_wait(
    TableSelectionScreen(recommendations, relationships)
)

if not result.cancelled:
    selected_tables = result.selected_tables
    print(f"Selected: {selected_tables}")
```

**Keyboard Shortcuts:**

| Key | Action |
|-----|--------|
| `Space` | Toggle selection of highlighted table |
| `Y` | Confirm selection and close |
| `N` or `Esc` | Cancel and close |
| `/` | Focus search input |
| `↑`/`↓` | Navigate table list |

**Integration Example:**

```python
# In bi_agent_console.py or similar TUI app
from backend.orchestrator.screens import TableSelectionScreen
from backend.agents.data_source.table_recommender import TableRecommender
from backend.agents.bi_tool.analysis_intent import AnalysisIntent

async def handle_intent_command(self, user_intent: str):
    """Handle /intent command with table selection."""

    # 1. Parse intent
    intent = AnalysisIntent(
        title="User Intent",
        purpose=user_intent,
        target_metrics=["revenue", "growth"],
        hypothesis=None,
        filters={}
    )

    # 2. Get schema
    from backend.agents.data_source.metadata_scanner import MetadataScanner
    scanner = MetadataScanner(self.conn_mgr)
    schema = scanner.scan_source(conn_id)

    # 3. Get recommendations
    from backend.orchestrator.llm_provider import LLMProvider
    llm = LLMProvider()
    recommender = TableRecommender(llm, schema)

    recommendations = await recommender.recommend_tables(intent)

    # 4. Show selection screen
    def on_selected(tables: List[str]):
        self.selected_tables = tables
        self.notify(f"Selected {len(tables)} tables")

    self.push_screen(
        TableSelectionScreen(recommendations, callback=on_selected)
    )
```

## Demo

Run the interactive demo to explore the TableSelectionScreen:

```bash
# From project root
python -m backend.orchestrator.screens.table_selection_demo
```

The demo includes:
- 6 sample table recommendations with varying relevance scores
- Korean explanations
- JOIN suggestions
- Sample ERD relationships
- Full keyboard navigation

## Architecture

### Screen Lifecycle

1. **Initialization**: Receives recommendations and optional relationships
2. **Mount**: Populates table list, sets up event handlers
3. **Interaction**: User navigates, filters, selects tables
4. **Confirmation**: User presses Y or clicks Confirm
5. **Callback**: Invokes callback with selected tables
6. **Dismiss**: Returns `TableSelectionResult` to caller

### Data Flow

```
TableRecommender
    ↓
List[TableRecommendation]
    ↓
TableSelectionScreen
    ↓
User Interaction
    ↓
List[str] (selected table names)
    ↓
Callback / Async Result
```

### CSS Styling

The screen uses Textual CSS for layout and styling:

- **Color Scheme**: Dark theme matching BI-Agent console
- **Score Colors**:
  - Green (#10b981): 90-100 (highly relevant)
  - Yellow (#fbbf24): 70-89 (relevant)
  - Gray (#6b7280): 0-69 (less relevant)
- **Accent**: Purple (#7c3aed) for highlights and borders

### Event Handling

| Event | Handler | Description |
|-------|---------|-------------|
| `on_mount` | `on_mount()` | Populate table list, focus search |
| `on_input_changed` | `on_input_changed()` | Apply search filter |
| `on_option_list_option_highlighted` | Updates detail panel | Show table details |
| `on_button_pressed` | `on_button_pressed()` | Confirm or cancel |
| `action_toggle` | `action_toggle()` | Toggle table selection |
| `action_confirm` | `action_confirm()` | Confirm and dismiss |
| `action_cancel` | `action_cancel()` | Cancel and dismiss |

## Testing

### Unit Tests

```python
# tests/test_table_selection_screen.py
import pytest
from backend.orchestrator.screens import TableSelectionScreen
from backend.agents.data_source.table_recommender import TableRecommendation

@pytest.mark.asyncio
async def test_table_selection_basic():
    """Test basic table selection flow."""
    recommendations = [
        TableRecommendation(
            table_name="sales",
            relevance_score=95,
            explanation_ko="매출 테이블",
            relevant_columns=["amount", "date"],
            join_suggestions=[]
        )
    ]

    screen = TableSelectionScreen(recommendations)

    # Simulate selection
    screen.selected_tables.add("sales")

    # Verify
    assert "sales" in screen.selected_tables
    assert len(screen.selected_tables) == 1
```

### Manual Testing

1. Run the demo: `python -m backend.orchestrator.screens.table_selection_demo`
2. Test keyboard navigation: ↑, ↓, Space, Y, N
3. Test search: Press `/`, type "sales", verify filtering
4. Test selection: Select multiple tables, confirm
5. Test cancellation: Press N or Esc

## Error Handling

The screen handles errors gracefully:

- **Empty recommendations**: Shows "No tables available" message
- **Search with no results**: Shows "No matching tables" message
- **No selection on confirm**: Shows warning notification
- **Missing data**: Falls back to empty lists/default values

## Logging

All user interactions are logged to `table_selection_screen.log`:

```python
logger.info("TableSelectionScreen initialized with 5 recommendations")
logger.debug("Selected table: sales")
logger.debug("Filter applied: 'sales' - 1 results")
logger.info("User confirmed selection: ['sales', 'customers']")
logger.info("User cancelled table selection")
```

## Future Enhancements

- [ ] Export selection to file (CSV, JSON)
- [ ] Save selection presets
- [ ] Visualize JOIN graph with graphviz
- [ ] Show sample data preview
- [ ] Column-level selection (not just tables)
- [ ] Advanced filters (score threshold, keywords)
- [ ] Bulk actions (select all > 80%, deselect all)
- [ ] Integration with ERD visualization tool

## Related Modules

- `backend.agents.data_source.table_recommender`: Generates recommendations
- `backend.agents.bi_tool.analysis_intent`: Defines analysis intent
- `backend.orchestrator.bi_agent_console`: Main TUI application
- `backend.agents.data_source.metadata_scanner`: Scans database schema

## License

MIT License - BI-Agent Project
