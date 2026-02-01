"""
Table Selection Screen Module
Interactive modal for selecting recommended tables from TableRecommender.
Displays relevance scores, explanations, and JOIN relationships.
"""

from typing import List, Callable, Optional, Set
from dataclasses import dataclass

from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.widgets import Static, DataTable, OptionList, Input, Label, Button
from textual.widgets.option_list import Option
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.binding import Binding
from rich.text import Text

from backend.agents.data_source.table_recommender import TableRecommendation, ERDRelationship
from backend.utils.logger_setup import setup_logger

logger = setup_logger("table_selection_screen", "table_selection_screen.log")


@dataclass
class TableSelectionResult:
    """Result of table selection operation"""
    selected_tables: List[str]
    recommendations: List[TableRecommendation]
    cancelled: bool = False


class TableSelectionScreen(ModalScreen[TableSelectionResult]):
    """
    Modal screen for interactive table selection from recommendations.

    Features:
    - Display recommended tables with relevance scores
    - Color-coded scores (green: 90+, yellow: 70-89, gray: <70)
    - Korean explanations for each recommendation
    - Relevant columns display
    - JOIN suggestions visualization
    - Multi-select with checkbox toggle
    - Schema preview in side panel
    - Search/filter functionality

    Usage:
        result = await self.app.push_screen_wait(
            TableSelectionScreen(recommendations, relationships)
        )
        if not result.cancelled:
            selected = result.selected_tables
    """

    CSS = """
    TableSelectionScreen {
        align: center middle;
        background: rgba(0, 0, 0, 0.85);
    }

    #table-modal {
        width: 90%;
        max-width: 120;
        height: 85%;
        background: #1a1b1e;
        border: thick #7c3aed;
        padding: 1;
    }

    #modal-title {
        text-align: center;
        color: #f8fafc;
        text-style: bold;
        background: #7c3aed;
        padding: 1;
        margin-bottom: 1;
    }

    #main-layout {
        width: 100%;
        height: 1fr;
        layout: horizontal;
    }

    #left-panel {
        width: 60%;
        height: 100%;
        border-right: solid #2d2f34;
        padding-right: 1;
    }

    #right-panel {
        width: 40%;
        height: 100%;
        padding-left: 1;
    }

    #search-container {
        height: auto;
        margin-bottom: 1;
    }

    #search-input {
        width: 100%;
        background: #111214;
        border: solid #2d2f34;
        color: #f8fafc;
        margin-top: 1;
    }

    #search-input:focus {
        border: solid #7c3aed;
    }

    #table-list {
        height: 1fr;
        background: #111214;
        border: solid #2d2f34;
        margin-bottom: 1;
    }

    .table-option {
        padding: 1;
    }

    .option-list--option-highlighted {
        background: #7c3aed;
        color: #f8fafc;
    }

    #detail-panel {
        height: 1fr;
        background: #111214;
        border: solid #2d2f34;
        padding: 1;
    }

    #detail-title {
        color: #7c3aed;
        text-style: bold;
        margin-bottom: 1;
    }

    .detail-section {
        margin-bottom: 1;
    }

    .section-label {
        color: #94a3b8;
        text-style: bold;
        margin-bottom: 0;
    }

    .section-content {
        color: #f8fafc;
        margin-left: 2;
    }

    .score-high {
        color: #10b981;
        text-style: bold;
    }

    .score-medium {
        color: #fbbf24;
        text-style: bold;
    }

    .score-low {
        color: #6b7280;
    }

    #button-bar {
        height: auto;
        layout: horizontal;
        align: center middle;
        margin-top: 1;
    }

    #confirm-btn {
        background: #10b981;
        color: white;
        margin-right: 2;
        min-width: 16;
    }

    #confirm-btn:hover {
        background: #059669;
    }

    #cancel-btn {
        background: #6b7280;
        color: white;
        min-width: 16;
    }

    #cancel-btn:hover {
        background: #4b5563;
    }

    #selection-counter {
        color: #7c3aed;
        text-align: center;
        margin-top: 1;
    }

    .join-relationship {
        color: #8b5cf6;
        margin-left: 2;
    }
    """

    BINDINGS = [
        Binding("y", "confirm", "Confirm Selection", show=True),
        Binding("n,escape", "cancel", "Cancel", show=True),
        Binding("space", "toggle", "Toggle Selection", show=True),
        Binding("/", "search", "Search", show=True),
    ]

    def __init__(
        self,
        recommendations: List[TableRecommendation],
        relationships: Optional[List[ERDRelationship]] = None,
        callback: Optional[Callable[[List[str]], None]] = None
    ):
        """
        Initialize table selection screen.

        Args:
            recommendations: List of TableRecommendation objects from TableRecommender
            relationships: Optional list of ERDRelationship objects for JOIN visualization
            callback: Optional callback function(selected_tables: List[str])
        """
        super().__init__()
        self.recommendations = recommendations
        self.relationships = relationships or []
        self.callback = callback
        self.selected_tables: Set[str] = set()
        self.filtered_recommendations = recommendations.copy()
        self.current_filter = ""

        logger.info(f"TableSelectionScreen initialized with {len(recommendations)} recommendations")

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        with Container(id="table-modal"):
            yield Label("📊 Table Selection - Choose Relevant Tables", id="modal-title")

            with Horizontal(id="main-layout"):
                # Left Panel: Table List
                with Vertical(id="left-panel"):
                    with Vertical(id="search-container"):
                        yield Label("🔍 Filter tables:")
                        yield Input(
                            id="search-input",
                            placeholder="Type to filter table names...",
                        )

                    yield OptionList(id="table-list")

                    yield Label(
                        "0 tables selected",
                        id="selection-counter"
                    )

                # Right Panel: Details
                with Vertical(id="right-panel"):
                    yield VerticalScroll(
                        Static("Select a table to view details", id="detail-content"),
                        id="detail-panel"
                    )

            # Button Bar
            with Horizontal(id="button-bar"):
                yield Button("✓ Confirm (Y)", id="confirm-btn", variant="success")
                yield Button("✗ Cancel (N)", id="cancel-btn", variant="default")

            yield Label(
                "[dim]Space: Toggle | Y: Confirm | N: Cancel | /: Search[/dim]",
                id="help-text"
            )

    def on_mount(self) -> None:
        """Populate table list on mount."""
        self._populate_table_list()
        self._update_selection_counter()

        # Focus on search input initially
        search_input = self.query_one("#search-input", Input)
        search_input.focus()

        logger.info("TableSelectionScreen mounted successfully")

    def _populate_table_list(self) -> None:
        """Populate the table list with recommendations."""
        table_list = self.query_one("#table-list", OptionList)
        table_list.clear_options()

        for rec in self.filtered_recommendations:
            # Create formatted option with checkbox and score
            checkbox = "☑" if rec.table_name in self.selected_tables else "☐"
            score_color = self._get_score_color(rec.relevance_score)

            # Build option text
            option_text = f"{checkbox} {rec.table_name} "
            option_text += f"[{score_color}]({rec.relevance_score})[/{score_color}]"

            table_list.add_option(
                Option(
                    option_text,
                    id=rec.table_name
                )
            )

        # Auto-select first item if available
        if table_list.option_count > 0:
            table_list.highlighted = 0
            self._show_table_details(self.filtered_recommendations[0])

    def _get_score_color(self, score: int) -> str:
        """Get color for relevance score."""
        if score >= 90:
            return "green"
        elif score >= 70:
            return "yellow"
        else:
            return "#6b7280"

    def _show_table_details(self, recommendation: TableRecommendation) -> None:
        """Display detailed information for selected table."""
        detail_content = self.query_one("#detail-content", Static)

        # Build rich content
        content = Text()

        # Table name
        content.append(f"📋 {recommendation.table_name}\n", style="bold cyan")
        content.append("\n")

        # Relevance score
        score_style = self._get_score_color(recommendation.relevance_score)
        content.append("Relevance Score: ", style="dim")
        content.append(f"{recommendation.relevance_score}/100\n", style=score_style)
        content.append("\n")

        # Korean explanation
        content.append("💡 Explanation:\n", style="bold")
        content.append(f"{recommendation.explanation_ko}\n", style="")
        content.append("\n")

        # Relevant columns
        if recommendation.relevant_columns:
            content.append("📊 Relevant Columns:\n", style="bold")
            for col in recommendation.relevant_columns:
                content.append(f"  • {col}\n", style="#94a3b8")
            content.append("\n")

        # JOIN suggestions
        if recommendation.join_suggestions:
            content.append("🔗 JOIN Suggestions:\n", style="bold")
            for join in recommendation.join_suggestions:
                target = join.get("target_table", "?")
                join_col = join.get("join_column", "?")
                target_col = join.get("target_column", "?")

                content.append(
                    f"  {recommendation.table_name}.{join_col} ",
                    style="#8b5cf6"
                )
                content.append("→ ", style="dim")
                content.append(
                    f"{target}.{target_col}\n",
                    style="#8b5cf6"
                )
            content.append("\n")

        # Inferred relationships from ERD
        table_relationships = self._get_table_relationships(recommendation.table_name)
        if table_relationships:
            content.append("🔄 Database Relationships:\n", style="bold")
            for rel in table_relationships:
                if rel.from_table == recommendation.table_name:
                    content.append(
                        f"  {rel.from_table}.{rel.from_column} → {rel.to_table}.{rel.to_column}\n",
                        style="#a78bfa"
                    )
                else:
                    content.append(
                        f"  {rel.from_table}.{rel.from_column} → {rel.to_table}.{rel.to_column}\n",
                        style="#a78bfa"
                    )
            content.append("\n")

        # Selection status
        is_selected = recommendation.table_name in self.selected_tables
        if is_selected:
            content.append("✓ Currently Selected", style="bold green")
        else:
            content.append("Press Space to select", style="dim")

        detail_content.update(content)

    def _get_table_relationships(self, table_name: str) -> List[ERDRelationship]:
        """Get all relationships involving the given table."""
        return [
            rel for rel in self.relationships
            if rel.from_table == table_name or rel.to_table == table_name
        ]

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        """Update details panel when option is highlighted."""
        if event.option and event.option.id:
            table_name = str(event.option.id)

            # Find recommendation
            for rec in self.filtered_recommendations:
                if rec.table_name == table_name:
                    self._show_table_details(rec)
                    break

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input.id == "search-input":
            self.current_filter = event.value.lower().strip()
            self._apply_filter()

    def _apply_filter(self) -> None:
        """Apply search filter to table list."""
        if not self.current_filter:
            self.filtered_recommendations = self.recommendations.copy()
        else:
            self.filtered_recommendations = [
                rec for rec in self.recommendations
                if self.current_filter in rec.table_name.lower()
            ]

        self._populate_table_list()
        logger.debug(f"Filter applied: '{self.current_filter}' - {len(self.filtered_recommendations)} results")

    def action_toggle(self) -> None:
        """Toggle selection of highlighted table."""
        table_list = self.query_one("#table-list", OptionList)

        if table_list.highlighted is not None:
            option = table_list.get_option_at_index(table_list.highlighted)
            if option and option.id:
                table_name = str(option.id)

                if table_name in self.selected_tables:
                    self.selected_tables.remove(table_name)
                    logger.debug(f"Deselected table: {table_name}")
                else:
                    self.selected_tables.add(table_name)
                    logger.debug(f"Selected table: {table_name}")

                # Refresh display
                self._populate_table_list()
                self._update_selection_counter()

                # Keep same item highlighted
                table_list.highlighted = table_list.highlighted

                # Update detail panel to show new selection status
                for rec in self.filtered_recommendations:
                    if rec.table_name == table_name:
                        self._show_table_details(rec)
                        break

    def _update_selection_counter(self) -> None:
        """Update the selection counter label."""
        counter = self.query_one("#selection-counter", Label)
        count = len(self.selected_tables)

        if count == 0:
            counter.update("No tables selected")
        elif count == 1:
            counter.update(f"[bold]{count}[/bold] table selected")
        else:
            counter.update(f"[bold]{count}[/bold] tables selected")

    def action_confirm(self) -> None:
        """Confirm selection and dismiss screen."""
        if not self.selected_tables:
            self.app.notify(
                "⚠️ No tables selected. Please select at least one table.",
                severity="warning",
                timeout=3
            )
            return

        selected_list = sorted(list(self.selected_tables))
        logger.info(f"User confirmed selection: {selected_list}")

        result = TableSelectionResult(
            selected_tables=selected_list,
            recommendations=self.recommendations,
            cancelled=False
        )

        # Call callback if provided
        if self.callback:
            self.callback(selected_list)

        self.dismiss(result)

    def action_cancel(self) -> None:
        """Cancel and dismiss screen."""
        logger.info("User cancelled table selection")

        result = TableSelectionResult(
            selected_tables=[],
            recommendations=self.recommendations,
            cancelled=True
        )

        self.dismiss(result)

    def action_search(self) -> None:
        """Focus on search input."""
        search_input = self.query_one("#search-input", Input)
        search_input.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        if event.button.id == "confirm-btn":
            self.action_confirm()
        elif event.button.id == "cancel-btn":
            self.action_cancel()
