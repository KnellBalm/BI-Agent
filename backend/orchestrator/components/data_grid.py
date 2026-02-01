"""
Sample Data Grid Component
A Textual widget for displaying sample data rows with type indicators and clipboard support.
"""
from typing import Dict, Any, List, Optional
import pandas as pd

from textual.app import ComposeResult
from textual.widgets import DataTable, Static
from textual.containers import Container
from textual.binding import Binding
from textual.reactive import reactive

# Type indicators for column types
TYPE_INDICATORS = {
    "numerical": "📊",
    "text": "📝",
    "datetime": "📅",
    "categorical": "🏷️",
    "empty": "⚠️",
}

TYPE_COLORS = {
    "numerical": "#3b82f6",   # Blue
    "text": "#22c55e",        # Green
    "datetime": "#f59e0b",    # Amber
    "categorical": "#a855f7", # Purple
    "empty": "#6b7280",       # Gray
}


class SampleDataGrid(Container):
    """
    Textual widget for displaying sample data rows with:
    - Column type indicators
    - Value truncation for long values
    - Ctrl+C to copy selected rows as CSV
    """

    DEFAULT_CSS = """
    SampleDataGrid {
        width: 100%;
        height: auto;
        min-height: 10;
        max-height: 20;
        background: #1a1b1e;
        border: solid #2d2f34;
        padding: 0;
    }

    SampleDataGrid > #grid-header {
        width: 100%;
        height: 1;
        background: #2d2f34;
        padding: 0 1;
        color: #94a3b8;
    }

    SampleDataGrid > DataTable {
        width: 100%;
        height: auto;
    }

    SampleDataGrid > #type-legend {
        width: 100%;
        height: 1;
        background: #111214;
        padding: 0 1;
        color: #6b7280;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "copy_selection", "Copy to Clipboard", show=True),
    ]

    # Track selected rows
    selected_rows: reactive[List[int]] = reactive([])

    # Store full values for tooltip
    _full_values: Dict[str, Dict[int, Any]] = {}

    # Column type mapping
    _column_types: Dict[str, str] = {}

    # Max display length before truncation
    MAX_VALUE_LENGTH = 50

    def __init__(
        self,
        df: Optional[pd.DataFrame] = None,
        column_types: Optional[Dict[str, str]] = None,
        sample_size: int = 10,
        **kwargs
    ):
        super().__init__(**kwargs)
        self._df = df
        self._column_types = column_types or {}
        self._sample_size = sample_size
        self._full_values = {}

    def compose(self) -> ComposeResult:
        """Compose the data grid components"""
        yield Static("Sample Data Preview", id="grid-header")
        yield DataTable(id="data-table", zebra_stripes=True, cursor_type="row")
        yield Static(self._get_type_legend(), id="type-legend")

    def on_mount(self) -> None:
        """Initialize the data table when mounted"""
        if self._df is not None:
            self.load_data(self._df, self._column_types)

    def load_data(
        self,
        df: pd.DataFrame,
        column_types: Optional[Dict[str, str]] = None
    ) -> None:
        """Load DataFrame into the data grid"""
        self._df = df.head(self._sample_size)
        self._column_types = column_types or self._infer_column_types(df)
        self._full_values = {}

        table = self.query_one("#data-table", DataTable)
        table.clear(columns=True)

        # Add columns with type indicators
        for col in self._df.columns:
            col_type = self._column_types.get(col, "text")
            indicator = TYPE_INDICATORS.get(col_type, "?")
            label = f"{indicator} {col}"
            table.add_column(label, key=col)

        # Add rows with truncation
        for idx, row in self._df.iterrows():
            row_values = []
            for col in self._df.columns:
                value = row[col]
                full_value = str(value) if pd.notna(value) else ""
                truncated = self._truncate_value(full_value)

                # Store full value for tooltip
                if col not in self._full_values:
                    self._full_values[col] = {}
                self._full_values[col][idx] = full_value

                row_values.append(truncated)

            table.add_row(*row_values, key=str(idx))

        # Update legend
        legend = self.query_one("#type-legend", Static)
        legend.update(self._get_type_legend())

    def _infer_column_types(self, df: pd.DataFrame) -> Dict[str, str]:
        """Infer column types from DataFrame"""
        types = {}
        for col in df.columns:
            series = df[col]
            clean = series.dropna()

            if clean.empty:
                types[col] = "empty"
            elif pd.api.types.is_numeric_dtype(clean):
                types[col] = "numerical"
            elif pd.api.types.is_datetime64_any_dtype(clean):
                types[col] = "datetime"
            elif clean.nunique() <= 20 or (clean.nunique() / len(clean)) < 0.3:
                types[col] = "categorical"
            else:
                types[col] = "text"

        return types

    def _truncate_value(self, value: str) -> str:
        """Truncate long values with ellipsis"""
        if len(value) > self.MAX_VALUE_LENGTH:
            return value[:self.MAX_VALUE_LENGTH - 3] + "..."
        return value

    def _get_type_legend(self) -> str:
        """Get type indicator legend"""
        legend_items = []
        for type_name, indicator in TYPE_INDICATORS.items():
            legend_items.append(f"{indicator}={type_name}")
        return " ".join(legend_items)

    def action_copy_selection(self) -> None:
        """Copy selected rows as CSV to clipboard"""
        if self._df is None or not self.selected_rows:
            # Copy all if nothing selected
            rows_to_copy = list(range(len(self._df)))
        else:
            rows_to_copy = sorted(self.selected_rows)

        try:
            # Build CSV string
            csv_lines = []
            # Header
            csv_lines.append(",".join(str(col) for col in self._df.columns))
            # Data rows
            for idx in rows_to_copy:
                if idx < len(self._df):
                    row = self._df.iloc[idx]
                    csv_lines.append(",".join(str(v) if pd.notna(v) else "" for v in row))

            csv_text = "\n".join(csv_lines)

            # Try to copy to clipboard
            try:
                import pyperclip
                pyperclip.copy(csv_text)
                self.notify(f"Copied {len(rows_to_copy)} rows to clipboard")
            except ImportError:
                self.notify("pyperclip not installed. Install with: pip install pyperclip", severity="warning")
            except Exception as e:
                self.notify(f"Clipboard error: {e}", severity="error")

        except Exception as e:
            self.notify(f"Copy error: {e}", severity="error")

    def get_selected_data(self) -> pd.DataFrame:
        """Get DataFrame of selected rows"""
        if self._df is None:
            return pd.DataFrame()

        if not self.selected_rows:
            return self._df.copy()

        return self._df.iloc[sorted(self.selected_rows)].copy()


class TypeCorrectionGrid(SampleDataGrid):
    """
    Extended data grid that shows type correction suggestions.
    Displays corrections in a panel with approve/reject functionality.
    """

    DEFAULT_CSS = """
    TypeCorrectionGrid {
        width: 100%;
        height: auto;
        min-height: 20;
        background: #1a1b1e;
        border: solid #2d2f34;
        padding: 0;
    }

    TypeCorrectionGrid > #grid-header {
        width: 100%;
        height: 1;
        background: #2d2f34;
        padding: 0 1;
        color: #94a3b8;
    }

    TypeCorrectionGrid > DataTable {
        width: 100%;
        height: 10;
    }

    TypeCorrectionGrid > #corrections-panel {
        width: 100%;
        height: auto;
        min-height: 8;
        background: #111214;
        border-top: solid #2d2f34;
        padding: 1;
    }

    TypeCorrectionGrid > #corrections-panel > #corrections-header {
        width: 100%;
        height: 1;
        background: #1f2937;
        padding: 0 1;
        color: #f59e0b;
        margin-bottom: 1;
    }

    TypeCorrectionGrid > #corrections-panel > DataTable {
        width: 100%;
        height: auto;
        min-height: 5;
    }

    TypeCorrectionGrid > #corrections-panel > #corrections-help {
        width: 100%;
        height: 1;
        background: #111214;
        padding: 0 1;
        color: #6b7280;
        margin-top: 1;
    }

    TypeCorrectionGrid > #type-legend {
        width: 100%;
        height: 1;
        background: #111214;
        padding: 0 1;
        color: #6b7280;
    }

    /* Confidence color coding */
    .confidence-high {
        color: #22c55e;
    }

    .confidence-medium {
        color: #f59e0b;
    }

    .confidence-low {
        color: #ef4444;
    }

    /* Status indicators */
    .status-approved {
        color: #22c55e;
    }

    .status-rejected {
        color: #ef4444;
    }

    .status-pending {
        color: #f59e0b;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "copy_selection", "Copy to Clipboard", show=True),
        Binding("a,space", "approve_correction", "Approve", show=True),
        Binding("r,delete", "reject_correction", "Reject", show=True),
        Binding("enter", "apply_corrections", "Apply All Approved", show=True),
        Binding("up,down", "navigate", "Navigate", show=False),
    ]

    # Store corrections from TypeCorrector
    _corrections: List[Any] = []  # List[TypeCorrectionSuggestion]
    _selected_correction_index: int = 0

    def __init__(
        self,
        df: Optional[pd.DataFrame] = None,
        column_types: Optional[Dict[str, str]] = None,
        sample_size: int = 10,
        **kwargs
    ):
        super().__init__(df, column_types, sample_size, **kwargs)
        self._corrections = []
        self._selected_correction_index = 0

    def compose(self) -> ComposeResult:
        """Compose the data grid with corrections panel"""
        yield Static("Type Correction Preview", id="grid-header")
        yield DataTable(id="data-table", zebra_stripes=True, cursor_type="row")

        # Corrections panel
        corrections_panel = Container(id="corrections-panel")
        with corrections_panel:
            yield Static("Type Correction Suggestions", id="corrections-header")
            yield DataTable(
                id="corrections-table",
                zebra_stripes=True,
                cursor_type="row",
                show_cursor=True
            )
            yield Static(
                "Keys: [a/Space]=Approve [r/Delete]=Reject [Enter]=Apply All [↑/↓]=Navigate",
                id="corrections-help"
            )

        yield corrections_panel
        yield Static(self._get_type_legend(), id="type-legend")

    def on_mount(self) -> None:
        """Initialize the tables when mounted"""
        super().on_mount()
        self._setup_corrections_table()

        # Refresh corrections if they were loaded before mount
        if self._corrections:
            self._refresh_corrections_table()

    def _setup_corrections_table(self) -> None:
        """Setup the corrections table structure"""
        table = self.query_one("#corrections-table", DataTable)
        table.clear(columns=True)

        # Add columns
        table.add_column("Status", key="status", width=8)
        table.add_column("Column", key="column", width=20)
        table.add_column("Current Type", key="current", width=15)
        table.add_column("Suggested Type", key="suggested", width=15)
        table.add_column("Confidence", key="confidence", width=12)
        table.add_column("Sample Values", key="samples", width=40)

    def load_corrections(self, corrections: List[Any]) -> None:
        """
        Load type correction suggestions into the grid.

        Args:
            corrections: List of TypeCorrectionSuggestion objects
        """
        self._corrections = corrections
        self._selected_correction_index = 0

        # Only refresh if widget is mounted
        if self.is_mounted:
            self._refresh_corrections_table()

    def _refresh_corrections_table(self) -> None:
        """Refresh the corrections table display"""
        try:
            table = self.query_one("#corrections-table", DataTable)
        except Exception:
            # Widget not mounted yet
            return

        table.clear()

        if not self._corrections:
            table.add_row("", "No corrections found", "", "", "", "")
            return

        for idx, correction in enumerate(self._corrections):
            status_indicator = self._get_status_indicator(correction.status)
            confidence_str = self._format_confidence(correction.confidence)
            samples_str = self._format_samples(correction.sample_values)

            table.add_row(
                status_indicator,
                correction.column,
                correction.current_type,
                correction.suggested_type,
                confidence_str,
                samples_str,
                key=str(idx)
            )

        # Select first row if available
        if self._corrections and len(table.rows) > 0:
            table.move_cursor(row=self._selected_correction_index)

    def _get_status_indicator(self, status: str) -> str:
        """Get visual indicator for correction status"""
        indicators = {
            "pending": "⏳",
            "approved": "✓",
            "rejected": "✗"
        }
        return indicators.get(status, "?")

    def _format_confidence(self, confidence: float) -> str:
        """Format confidence score with color coding"""
        percentage = f"{confidence * 100:.0f}%"

        if confidence >= 0.8:
            return f"[green]{percentage}[/green]"
        elif confidence >= 0.5:
            return f"[yellow]{percentage}[/yellow]"
        else:
            return f"[red]{percentage}[/red]"

    def _format_samples(self, samples: List[str]) -> str:
        """Format sample values for display"""
        if not samples:
            return ""

        # Show first 3 samples, truncate if too long
        display_samples = samples[:3]
        formatted = []

        for sample in display_samples:
            if len(sample) > 15:
                formatted.append(sample[:12] + "...")
            else:
                formatted.append(sample)

        result = ", ".join(formatted)

        if len(samples) > 3:
            result += f" (+{len(samples) - 3} more)"

        return result

    def _get_current_correction_index(self) -> int:
        """Get the currently selected correction index from table cursor"""
        table = self.query_one("#corrections-table", DataTable)

        if not table.cursor_row:
            return 0

        try:
            return int(table.cursor_row)
        except (ValueError, TypeError):
            return 0

    def action_approve_correction(self) -> None:
        """Approve the currently selected correction"""
        if not self._corrections:
            self.notify("No corrections to approve", severity="warning")
            return

        idx = self._get_current_correction_index()

        if 0 <= idx < len(self._corrections):
            correction = self._corrections[idx]
            correction.status = "approved"
            self._refresh_corrections_table()
            self.notify(f"Approved: {correction.column} → {correction.suggested_type}")

            # Move to next correction if available
            if idx + 1 < len(self._corrections):
                self._selected_correction_index = idx + 1
                table = self.query_one("#corrections-table", DataTable)
                table.move_cursor(row=self._selected_correction_index)

    def action_reject_correction(self) -> None:
        """Reject the currently selected correction"""
        if not self._corrections:
            self.notify("No corrections to reject", severity="warning")
            return

        idx = self._get_current_correction_index()

        if 0 <= idx < len(self._corrections):
            correction = self._corrections[idx]
            correction.status = "rejected"
            self._refresh_corrections_table()
            self.notify(f"Rejected: {correction.column}", severity="warning")

            # Move to next correction if available
            if idx + 1 < len(self._corrections):
                self._selected_correction_index = idx + 1
                table = self.query_one("#corrections-table", DataTable)
                table.move_cursor(row=self._selected_correction_index)

    def action_apply_corrections(self) -> None:
        """Apply all approved corrections"""
        approved = self.get_approved_corrections()

        if not approved:
            self.notify("No corrections approved yet", severity="warning")
            return

        approved_count = len(approved)
        column_names = ", ".join([c.column for c in approved])

        self.notify(
            f"Ready to apply {approved_count} correction(s): {column_names}",
            title="Corrections Ready"
        )

    def on_approve(self, column: str) -> None:
        """
        Handle approval of a specific column correction.

        Args:
            column: Name of the column to approve
        """
        for correction in self._corrections:
            if correction.column == column:
                correction.status = "approved"
                self._refresh_corrections_table()
                break

    def on_reject(self, column: str) -> None:
        """
        Handle rejection of a specific column correction.

        Args:
            column: Name of the column to reject
        """
        for correction in self._corrections:
            if correction.column == column:
                correction.status = "rejected"
                self._refresh_corrections_table()
                break

    def get_approved_corrections(self) -> List[Any]:
        """
        Get list of approved corrections.

        Returns:
            List of TypeCorrectionSuggestion objects with status='approved'
        """
        return [c for c in self._corrections if c.status == "approved"]

    def get_pending_corrections(self) -> List[Any]:
        """
        Get list of pending corrections.

        Returns:
            List of TypeCorrectionSuggestion objects with status='pending'
        """
        return [c for c in self._corrections if c.status == "pending"]

    def get_rejected_corrections(self) -> List[Any]:
        """
        Get list of rejected corrections.

        Returns:
            List of TypeCorrectionSuggestion objects with status='rejected'
        """
        return [c for c in self._corrections if c.status == "rejected"]

    def get_correction_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics for all corrections.

        Returns:
            Dictionary with counts of approved, rejected, and pending corrections
        """
        return {
            "total": len(self._corrections),
            "approved": len(self.get_approved_corrections()),
            "rejected": len(self.get_rejected_corrections()),
            "pending": len(self.get_pending_corrections())
        }
