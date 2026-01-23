# T6: TUI Meta Preview Panel - Implementation Spec

## Overview
Create a Rich-based TUI panel to display and save generated Meta JSON files.

## File Structure
```
backend/orchestrator/tui_meta_preview.py  # NEW
backend/orchestrator/tui_interface.py     # EXTEND (if exists)
backend/main.py                           # MODIFY (add commands)
```

## Component Design

### 1. MetaPreviewPanel Class

```python
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
import json
from typing import Dict, Any, Optional

class MetaPreviewPanel:
    """TUI component for Meta JSON preview and export"""

    def __init__(self, console: Console):
        self.console = console
        self.last_meta_json: Optional[Dict[str, Any]] = None

    def set_meta_json(self, meta_json: Dict[str, Any]):
        """Store the last generated meta JSON"""
        self.last_meta_json = meta_json

    def preview(self):
        """Display meta JSON with syntax highlighting"""
        if not self.last_meta_json:
            self.console.print("[yellow]No meta JSON generated yet.[/yellow]")
            return

        # Format JSON with indentation
        json_str = json.dumps(self.last_meta_json, indent=2, ensure_ascii=False)

        # Syntax highlighting for JSON
        syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)

        # Display in panel
        panel = Panel(
            syntax,
            title="[bold cyan]Generated Meta JSON[/bold cyan]",
            border_style="bright_blue",
            expand=False
        )
        self.console.print(panel)

        # Display summary table
        self._display_summary()

    def _display_summary(self):
        """Display quick summary of meta JSON content"""
        if not self.last_meta_json:
            return

        table = Table(title="Meta JSON Summary", show_header=True)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        # Add key metrics
        table.add_row("Tool", self.last_meta_json.get("tool", "N/A"))
        table.add_row("Version", self.last_meta_json.get("version", "N/A"))

        datasources = self.last_meta_json.get("datasources", [])
        table.add_row("Datasources", str(len(datasources)))

        worksheets = self.last_meta_json.get("worksheets", [])
        table.add_row("Worksheets", str(len(worksheets)))

        if worksheets:
            table.add_row("Visual Type", worksheets[0].get("visual_type", "N/A"))

        self.console.print(table)

    def save(self, file_path: str) -> bool:
        """Save meta JSON to file"""
        if not self.last_meta_json:
            self.console.print("[red]No meta JSON to save.[/red]")
            return False

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.last_meta_json, f, indent=2, ensure_ascii=False)

            self.console.print(f"[green]✓ Meta JSON saved to: {file_path}[/green]")
            return True
        except Exception as e:
            self.console.print(f"[red]✗ Failed to save: {e}[/red]")
            return False

    def export_twb(self, file_path: str) -> bool:
        """Export meta JSON as .twb file (optional for MVP)"""
        if not self.last_meta_json or self.last_meta_json.get("tool") != "tableau":
            self.console.print("[yellow]Only Tableau meta JSON can be exported as .twb[/yellow]")
            return False

        # This would require TableauMetadataEngine reverse operation
        # For MVP, this can be a stub
        self.console.print("[yellow]TWB export not implemented in MVP[/yellow]")
        return False
```

## Integration with main.py

### New Commands to Add

```python
# In interactive_loop() after line 96

# Add meta_preview_panel initialization
from backend.orchestrator.tui_meta_preview import MetaPreviewPanel
meta_panel = MetaPreviewPanel(console)

# Add command detection
if user_input.lower().startswith("meta preview"):
    meta_panel.preview()
    continue

if user_input.lower().startswith("meta save"):
    parts = user_input.split()
    if len(parts) >= 3:
        file_path = parts[2]
        meta_panel.save(file_path)
    else:
        console.print("[yellow]Usage: meta save <filename.json>[/yellow]")
    continue

if user_input.lower().startswith("meta export"):
    parts = user_input.split()
    if len(parts) >= 3:
        file_path = parts[2]
        meta_panel.export_twb(file_path)
    else:
        console.print("[yellow]Usage: meta export <filename.twb>[/yellow]")
    continue

# After orchestrator.run() completes
result = await orchestrator.run(user_input, context=context)

# If result contains meta_json, store it
if isinstance(result, dict) and "meta_json" in result:
    meta_panel.set_meta_json(result["meta_json"])
    console.print("[dim]Tip: Use 'meta preview' to view or 'meta save <file>' to export[/dim]")
```

## UI/UX Flow

### Scenario 1: Generate and Preview
```
User: 월별 매출 차트를 만들어줘
System: [Processes with MetaGenerator]
        Generated Tableau Meta JSON successfully!
        Tip: Use 'meta preview' to view or 'meta save <file>' to export

User: meta preview
System: [Displays syntax-highlighted JSON in panel]
        [Displays summary table]
```

### Scenario 2: Save to File
```
User: meta save output/sales_chart_meta.json
System: ✓ Meta JSON saved to: output/sales_chart_meta.json
```

### Scenario 3: No Meta Generated Yet
```
User: meta preview
System: No meta JSON generated yet.
```

## Dependencies on Other Tasks

- **T3 (RAG)**: Not directly, but context helps guide generation
- **T5 (Pipeline)**: CRITICAL - T5 must return meta_json in result dict

## Testing Checklist

- [ ] Display JSON with syntax highlighting
- [ ] Summary table shows correct counts
- [ ] Save command creates valid JSON file
- [ ] Command works with Korean filenames
- [ ] Error handling for no meta JSON
- [ ] Export TWB shows "not implemented" gracefully
- [ ] Integration with main.py loop works
- [ ] Multiple meta generations update the preview correctly

## Estimated Lines of Code
- `tui_meta_preview.py`: ~120 lines
- `main.py` modifications: ~30 lines
- Total: ~150 lines

## Rich Library Features Used
- `Panel`: For bordered display
- `Syntax`: For JSON syntax highlighting
- `Table`: For summary display
- `Console`: For output management
