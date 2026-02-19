"""
DatabaseExplorerScreen Module
Provides a 3-pane layout for exploring database schemas, writing SQL, and viewing results.
Inspired by sqlit interaction model.
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.widgets import Label, Input, Button, Tree, DataTable, TextArea, Static, OptionList
from textual.widgets.option_list import Option
from textual.screen import Screen, ModalScreen
from textual.binding import Binding

from ..components.vim_engine import VimEngine, VimMode
from ..services.text2sql.factory import Text2SQLServiceFactory
from ..services.text2sql.base import BaseText2SQLService
from ..config.explorer_config import get_config
from backend.agents.data_source.metadata_scanner import MetadataScanner
from backend.orchestrator.managers.connection_manager import ConnectionManager
from backend.agents.data_source.connection_manager import ConnectionManager as AgentConnectionManager
from backend.orchestrator.managers.query_history import get_query_history, QueryHistory, QueryHistoryEntry
from backend.orchestrator.managers.query_bookmarks import get_query_bookmarks, QueryBookmark

logger = logging.getLogger("tui")


class BookmarkModal(ModalScreen[tuple[str, List[str]]]):
    """Modal screen for creating/editing bookmarks."""

    CSS = """
    BookmarkModal {
        align: center middle;
    }
    #bookmark-dialog {
        width: 60;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    #bookmark-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    .input-label {
        color: $text-muted;
        margin-top: 1;
    }
    #bookmark-buttons {
        layout: horizontal;
        height: auto;
        margin-top: 1;
        align: center middle;
    }
    #save-btn {
        margin: 0 1;
    }
    #cancel-btn {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="bookmark-dialog"):
            yield Label("📌 Create Bookmark", id="bookmark-title")
            yield Label("Name:", classes="input-label")
            yield Input(placeholder="Enter bookmark name", id="bookmark-name")
            yield Label("Tags (comma-separated):", classes="input-label")
            yield Input(placeholder="e.g., report, daily, sales", id="bookmark-tags")
            with Horizontal(id="bookmark-buttons"):
                yield Button("Save", id="save-btn", variant="primary")
                yield Button("Cancel", id="cancel-btn", variant="default")

    def on_mount(self) -> None:
        self.query_one("#bookmark-name", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            name = self.query_one("#bookmark-name", Input).value.strip()
            tags_str = self.query_one("#bookmark-tags", Input).value.strip()

            if not name:
                self.app.notify("Please enter a bookmark name", severity="warning")
                return

            tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()]
            self.dismiss((name, tags))
        else:
            self.dismiss(None)


class VimTextArea(TextArea, VimEngine):
    """TextArea with Vim-style modal editing."""
    
    BINDINGS = [
        Binding("escape", "escape", "Normal Mode", show=False),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # VimEngine.__init__ may not be called due to MRO,
        # so explicitly initialize vim attributes here
        self.vim_mode = VimMode.NORMAL
        self.leader_key = None

    def _on_key(self, event) -> None:
        # Route keys through VimEngine
        # Note: We need to handle this carefully to not block all input
        if self.vim_mode == VimMode.NORMAL:
            # In Normal mode, we handle movements/commands
            # We use a task for the async handler
            asyncio.create_task(self.handle_vim_key(event.key))
            event.prevent_default()
        else:
            # In Insert mode, we let TextArea handle it, except for Escape
            if event.key == "escape":
                self.set_vim_mode(VimMode.NORMAL)
                event.prevent_default()

class DatabaseExplorerScreen(Screen):
    """
    3-pane Database Explorer Screen.
    Pane 1: Schema Tree (Left)
    Pane 2: SQL Editor (Middle/Top)
    Pane 3: Results Grid (Middle/Bottom)
    """

    BINDINGS = [
        Binding("q", "dismiss", "Quit"),
        Binding("ctrl+r", "run_query", "Run Query", show=True),
        Binding("ctrl+s", "save_query", "Save"),
        Binding("ctrl+b", "bookmark_current_query", "Bookmark"),
        Binding("f4", "toggle_history_panel", "History"),
        Binding("f5", "show_bookmarks", "Bookmarks"),
        Binding("tab", "next_pane", "Next Pane"),
        Binding("shift+tab", "prev_pane", "Prev Pane"),
        Binding("alt+m", "toggle_mode", "Toggle Mode"),
    ]

    CSS = """
    DatabaseExplorerScreen {
        background: $surface;
    }
    #mode-indicator {
        height: 1;
        background: $panel;
        color: $text;
        padding: 0 1;
        text-style: bold;
    }
    #explorer-layout {
        layout: horizontal;
        height: 1fr;
    }
    #tree-panel {
        width: 30;
        border: tall $panel;
        background: $surface;
    }
    #history-panel {
        width: 30;
        border: solid $primary;
        background: $surface;
        display: none;
    }
    #history-list {
        height: 100%;
    }
    #main-panel {
        width: 1fr;
        height: 1fr;
    }
    #editor-panel {
        height: 15;
        border: tall $panel;
        background: $surface;
    }
    #editor-toolbar {
        height: 1;
        dock: bottom;
        background: $panel;
        padding: 0 1;
    }
    #run-btn {
        min-width: 12;
        height: 1;
        margin: 0 1 0 0;
    }
    #run-hint {
        height: 1;
        margin: 0;
        padding: 0;
    }
    #results-panel {
        height: 1fr;
        border: tall $panel;
        background: $surface;
    }
    #results-status {
        height: 1;
        dock: bottom;
        background: $panel;
        color: $text-muted;
        padding: 0 1;
    }
    .panel-title {
        background: $panel;
        color: $text-muted;
        padding: 0 1;
        text-style: bold;
    }
    .pane-focused {
        border: tall $primary;
    }
    """

    def __init__(
        self,
        connection_id: str,
        conn_mgr: ConnectionManager,
        agent_conn_mgr: AgentConnectionManager,
        initial_query: Optional[str] = None,
        mode: Optional[str] = None,
        provider: Optional[str] = None
    ):
        super().__init__()
        self.connection_id = connection_id
        self.conn_mgr = conn_mgr  # Orchestrator's ConnectionManager (for UI config)
        self.agent_conn_mgr = agent_conn_mgr  # Agent's ConnectionManager (for schema scanning)
        self.initial_query = initial_query or "SELECT 1 AS test;"
        self._query_running = False

        # Load configuration
        self.config = get_config()

        # Set AI mode (use provided or default from config)
        self.ai_mode = mode or self.config.text2sql.default_mode
        self.api_provider = provider or self.config.text2sql.default_api_provider

        # Initialize Text2SQL service
        self.text2sql_service: Optional[BaseText2SQLService] = None
        self._initialize_text2sql_service()

        # Initialize Query History manager
        self.query_history: QueryHistory = get_query_history(
            max_entries=self.config.history.max_entries,
            auto_cleanup_days=self.config.history.auto_cleanup_days
        )
        self._history_visible = False

        # Initialize Query Bookmarks manager
        self.query_bookmarks = get_query_bookmarks()
        self._show_bookmarks = False

    def compose(self) -> ComposeResult:
        # Mode indicator at the top
        yield Label(self._get_mode_indicator_text(), id="mode-indicator")

        with Horizontal(id="explorer-layout"):
            # Left Pane: Schema Tree
            with Vertical(id="tree-panel", classes="border-hint"):
                yield Label(" STRUCTURE [F1] ", classes="panel-title")
                yield Tree("Database", id="schema-tree")

            # History Panel (initially hidden)
            with Vertical(id="history-panel", classes="border-hint"):
                yield Label(" QUERY HISTORY [F4] ", classes="panel-title")
                yield OptionList(id="history-list")

            # Middle/Right Pane: Editor & Results
            with Vertical(id="main-panel"):
                with Vertical(id="editor-panel", classes="border-hint"):
                    yield Label(" SQL EDITOR [F2] ", classes="panel-title")
                    yield VimTextArea(id="sql-editor", text=self.initial_query)
                    with Horizontal(id="editor-toolbar"):
                        yield Button("▶ Run", id="run-btn", variant="success")
                        yield Label("[dim]Ctrl+R 실행 | Tab 패널 이동[/dim]", id="run-hint")

                with Vertical(id="results-panel", classes="border-hint"):
                    yield Label(" RESULTS [F3] ", classes="panel-title")
                    yield DataTable(id="results-grid")
                    yield Label("", id="results-status")

    def on_mount(self) -> None:
        self.query_one("#schema-tree").focus()

        # Set border titles as hints
        self.query_one("#tree-panel").border_title = "Explorer"
        self.query_one("#editor-panel").border_title = "Query"
        self.query_one("#results-panel").border_title = "Data Grid"

        # Load schema asynchronously with loading indicator
        asyncio.create_task(self._load_schema())

        # Load query history
        self._refresh_history_list()

    async def _load_schema(self):
        """Loads tables/views from the connection manager asynchronously."""
        tree = self.query_one("#schema-tree")

        # Show loading indicator
        loading_node = tree.root.add("📡 Loading schema...", expand=True)
        loading_node.add_leaf("Please wait...")

        try:
            # Verify connection exists in registry before scanning
            import json
            import os
            if not os.path.exists(self.agent_conn_mgr.registry_path):
                raise FileNotFoundError(f"Registry not found: {self.agent_conn_mgr.registry_path}")

            with open(self.agent_conn_mgr.registry_path, 'r', encoding='utf-8') as f:
                registry = json.load(f)

            if self.connection_id not in registry:
                available = list(registry.keys())
                raise ValueError(
                    f"Connection '{self.connection_id}' not found in Agent registry. "
                    f"Available: {available}"
                )

            conn_info = registry[self.connection_id]
            logger.info(
                f"Loading schema for '{self.connection_id}' "
                f"(type: {conn_info.get('type')}, config keys: {list(conn_info.get('config', {}).keys())})"
            )

            # Run the blocking operation in a thread pool to avoid blocking UI
            def _scan_metadata():
                scanner = MetadataScanner(self.agent_conn_mgr)
                return scanner.scan_source(self.connection_id, deep_scan=False)

            # Execute in thread pool
            loop = asyncio.get_event_loop()
            metadata = await loop.run_in_executor(None, _scan_metadata)

            # Remove loading indicator
            tree.root.remove_children()

            # Add tables to tree
            tables_node = tree.root.add("📊 Tables", expand=True)
            table_list = metadata.get("tables", [])

            if table_list:
                for table_info in table_list:
                    table_name = table_info.get("table_name", "unknown")
                    tables_node.add_leaf(f"  {table_name}")

                self.notify(f"✓ Loaded {len(table_list)} tables", severity="information")
            else:
                tables_node.add_leaf("  (no tables found)")
                self.notify("No tables found in database", severity="warning")

            logger.info(f"Loaded {len(table_list)} tables for connection {self.connection_id}")

        except Exception as e:
            logger.error(f"Failed to load schema for connection {self.connection_id}: {e}", exc_info=True)

            # Remove loading indicator and show error
            tree.root.remove_children()
            error_node = tree.root.add("❌ Error loading schema", expand=True)
            error_node.add_leaf(f"  {str(e)}")

            self.notify(f"Failed to load schema: {str(e)}", severity="error", timeout=10)

    def action_run_query(self) -> None:
        """Executes the query in the editor."""
        if self._query_running:
            self.notify("Query already running...", severity="warning")
            return
        asyncio.create_task(self._execute_query())

    async def _execute_query(self) -> None:
        """Run the SQL query against the actual database connection."""
        query = self.query_one("#sql-editor", VimTextArea).text.strip()
        if not query:
            self.notify("SQL 쿼리를 입력해주세요.", severity="warning")
            return

        self._query_running = True
        status_label = self.query_one("#results-status", Label)
        grid = self.query_one("#results-grid", DataTable)

        # Track execution time
        import time
        start_time = time.time()

        try:
            status_label.update("[bold yellow]⏳ 쿼리 실행 중...[/bold yellow]")
            self.notify(f"Running: {query[:50]}...", timeout=2)

            # Run blocking DB query in thread pool
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(
                None,
                lambda: self.agent_conn_mgr.run_query(self.connection_id, query)
            )

            # Calculate execution time
            execution_time_ms = (time.time() - start_time) * 1000

            # Render DataFrame to DataTable
            self._render_dataframe(df)

            row_count = len(df)
            col_count = len(df.columns)
            status_label.update(f"[bold green]✓ {row_count} rows × {col_count} columns[/bold green]")
            logger.info(f"Query executed: {row_count} rows returned")

            # Save to query history
            history_entry = QueryHistoryEntry(
                query=query,
                timestamp=datetime.now().isoformat(),
                connection_id=self.connection_id,
                execution_time_ms=execution_time_ms,
                row_count=row_count,
                status="success",
                error_message=None
            )
            self.query_history.add_entry(history_entry)
            self._refresh_history_list()

        except Exception as e:
            # Calculate execution time even for errors
            execution_time_ms = (time.time() - start_time) * 1000

            logger.error(f"Query execution failed: {e}", exc_info=True)
            grid.clear(columns=True)
            status_label.update(f"[bold red]✗ Error: {str(e)}[/bold red]")
            self.notify(f"❌ {str(e)}", severity="error", timeout=10)

            # Save error to query history
            history_entry = QueryHistoryEntry(
                query=query,
                timestamp=datetime.now().isoformat(),
                connection_id=self.connection_id,
                execution_time_ms=execution_time_ms,
                row_count=0,
                status="error",
                error_message=str(e)
            )
            self.query_history.add_entry(history_entry)
            self._refresh_history_list()

        finally:
            self._query_running = False

    def _render_dataframe(self, df) -> None:
        """Render a pandas DataFrame into the DataTable widget."""
        grid = self.query_one("#results-grid", DataTable)
        grid.clear(columns=True)

        if df is None or df.empty:
            self.notify("쿼리 결과가 비어있습니다.", severity="information")
            return

        # Add columns
        for col in df.columns:
            grid.add_column(str(col), key=str(col))

        # Add rows (convert to string for display, handle None/NaN)
        for _, row in df.iterrows():
            display_row = []
            for val in row:
                if val is None or (isinstance(val, float) and str(val) == 'nan'):
                    display_row.append("NULL")
                else:
                    display_row.append(str(val))
            grid.add_row(*display_row)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "run-btn":
            self.action_run_query()

    def action_next_pane(self) -> None:
        """Cycle focus between panels."""
        panels = ["#schema-tree", "#sql-editor", "#results-grid"]
        focused = self.app.focused

        for i, sel in enumerate(panels):
            if self.query_one(sel) == focused:
                next_idx = (i + 1) % len(panels)
                self.query_one(panels[next_idx]).focus()
                return

        self.query_one(panels[0]).focus()

    def action_prev_pane(self) -> None:
        """Cycle focus between panels in reverse order."""
        panels = ["#schema-tree", "#sql-editor", "#results-grid"]
        focused = self.app.focused

        for i, sel in enumerate(panels):
            if self.query_one(sel) == focused:
                prev_idx = (i - 1) % len(panels)
                self.query_one(panels[prev_idx]).focus()
                return

        self.query_one(panels[-1]).focus()

    def action_save_query(self) -> None:
        """Save current query (stub implementation)."""
        self.notify("Save query functionality coming soon", severity="information")

    def action_bookmark_current_query(self) -> None:
        """Show modal to bookmark the current query."""
        query = self.query_one("#sql-editor", VimTextArea).text.strip()
        if not query:
            self.notify("No query to bookmark", severity="warning")
            return

        def handle_bookmark_result(result):
            if result is not None:
                name, tags = result
                bookmark_id = self.query_bookmarks.add_bookmark(
                    name=name,
                    query=query,
                    tags=tags,
                    connection_id=self.connection_id
                )
                self.notify(f"✓ Bookmark '{name}' created", severity="information")
                logger.info(f"Created bookmark: {name} (ID: {bookmark_id})")

                # Refresh bookmarks list if visible
                if self._show_bookmarks:
                    self._refresh_history_list()

        self.app.push_screen(BookmarkModal(), handle_bookmark_result)

    def action_show_bookmarks(self) -> None:
        """Toggle bookmark panel view."""
        self._show_bookmarks = not self._show_bookmarks
        self._refresh_history_list()

        if self._show_bookmarks:
            self.notify("Showing bookmarks (F5 to toggle)", severity="information")
        else:
            self.notify("Showing history (F5 to toggle)", severity="information")

    def action_load_from_bookmark(self, bookmark_id: str) -> None:
        """Load a bookmark into the SQL editor."""
        bookmark = next(
            (b for b in self.query_bookmarks.get_all() if b.id == bookmark_id),
            None
        )

        if bookmark:
            sql_editor = self.query_one("#sql-editor", VimTextArea)
            sql_editor.text = bookmark.query
            self.notify(f"Loaded bookmark: {bookmark.name}", severity="information")
            logger.info(f"Loaded bookmark {bookmark_id} into editor")
        else:
            self.notify("Bookmark not found", severity="error")
            logger.warning(f"Bookmark {bookmark_id} not found")

    def _initialize_text2sql_service(self) -> None:
        """Initialize Text2SQL service based on current mode and provider."""
        try:
            if self.ai_mode == "local":
                self.text2sql_service = Text2SQLServiceFactory.create(
                    mode="local",
                    model_name=self.config.text2sql.local.model,
                    ollama_url=self.config.text2sql.local.ollama_host
                )
                logger.info(f"Initialized local Text2SQL service with model: {self.config.text2sql.local.model}")
            elif self.ai_mode == "api":
                self.text2sql_service = Text2SQLServiceFactory.create(
                    mode="api",
                    provider=self.api_provider
                )
                logger.info(f"Initialized API Text2SQL service with provider: {self.api_provider}")
            else:
                logger.warning(f"Invalid AI mode: {self.ai_mode}. Text2SQL service not initialized.")
                self.text2sql_service = None
        except Exception as e:
            logger.error(f"Failed to initialize Text2SQL service: {e}")
            self.text2sql_service = None
            self.notify(f"Failed to initialize Text2SQL: {str(e)}", severity="error")

    def _get_mode_indicator_text(self) -> str:
        """Get the text for the mode indicator widget."""
        if self.ai_mode == "local":
            model = self.config.text2sql.local.model
            return f"[Mode: 🏠 Local ({model})]  Press Alt+M to toggle mode"
        elif self.ai_mode == "api":
            provider_name = self.api_provider.capitalize()
            return f"[Mode: ☁️ API ({provider_name})]  Press Alt+M to toggle mode"
        else:
            return "[Mode: Unknown]"

    def _update_mode_indicator(self) -> None:
        """Update the mode indicator widget text."""
        try:
            mode_label = self.query_one("#mode-indicator", Label)
            mode_label.update(self._get_mode_indicator_text())
        except Exception as e:
            logger.error(f"Failed to update mode indicator: {e}")

    def action_toggle_mode(self) -> None:
        """Toggle between Local and API modes."""
        if self.ai_mode == "local":
            # Switch to API mode
            self.ai_mode = "api"
            self.api_provider = self.config.text2sql.default_api_provider
        else:
            # Switch to local mode
            self.ai_mode = "local"

        # Re-initialize the Text2SQL service
        self._initialize_text2sql_service()

        # Update the mode indicator
        self._update_mode_indicator()

        # Show notification
        mode_text = f"🏠 Local ({self.config.text2sql.local.model})" if self.ai_mode == "local" else f"☁️ API ({self.api_provider.capitalize()})"
        self.notify(f"Switched to {mode_text} mode", severity="information")
        logger.info(f"Toggled mode to: {self.ai_mode} (provider: {self.api_provider})")

    async def action_generate_sql_from_nl(self, natural_query: str) -> None:
        """
        Generate SQL from natural language query.

        Args:
            natural_query: User's natural language question
        """
        if not self.text2sql_service:
            self.notify("Text2SQL service not initialized. Cannot generate SQL.", severity="error")
            return

        if not natural_query.strip():
            self.notify("Please enter a natural language query.", severity="warning")
            return

        try:
            # Show loading notification
            self.notify(f"Generating SQL from: {natural_query[:50]}...", timeout=2)

            # Get real schema info from MetadataScanner
            schema_info = {}
            try:
                scanner = MetadataScanner(self.agent_conn_mgr)
                metadata = scanner.scan_source(self.connection_id, deep_scan=False)

                # Format schema_info as Dict[table_name, List[column_names]]
                for table_meta in metadata.get("tables", []):
                    table_name = table_meta.get("table_name")
                    if table_name:
                        # For shallow scan, we don't have columns yet, so empty list
                        # For deep scan, we'd extract from table_meta["columns"]
                        schema_info[table_name] = []

                logger.info(f"Retrieved schema for {len(schema_info)} tables")
            except Exception as e:
                logger.error(f"Failed to fetch schema: {e}", exc_info=True)
                self.notify(f"⚠️ Could not fetch schema: {str(e)}", severity="warning", timeout=5)
                # Fall back to empty schema
                schema_info = {}

            # Generate SQL
            result = await self.text2sql_service.generate_sql(
                natural_query=natural_query,
                schema_info=schema_info,
                dialect="postgresql",
                include_guide=True
            )

            # Insert generated SQL into editor
            sql_editor = self.query_one("#sql-editor", VimTextArea)
            sql_editor.text = result.sql

            # Show thinking process and warnings
            info_parts = []
            if result.thinking_process:
                info_parts.append(f"💭 Thinking: {result.thinking_process[:100]}...")
            if result.warnings:
                info_parts.append(f"⚠️ Warnings: {'; '.join(result.warnings[:2])}")

            if info_parts:
                self.notify("\n".join(info_parts), severity="information", timeout=10)

            # Show confidence
            confidence_pct = int(result.confidence * 100)
            self.notify(
                f"✓ SQL generated with {confidence_pct}% confidence by {result.provider}",
                severity="information"
            )

            logger.info(f"Generated SQL from NL query: {natural_query[:50]}... (confidence: {confidence_pct}%)")

        except Exception as e:
            logger.error(f"Failed to generate SQL from natural language: {e}", exc_info=True)
            self.notify(f"❌ Failed to generate SQL: {str(e)}", severity="error")

    def _refresh_history_list(self) -> None:
        """Refresh the history/bookmarks list based on current mode."""
        history_list = self.query_one("#history-list", OptionList)
        history_list.clear_options()

        if self._show_bookmarks:
            # Show bookmarks
            bookmarks = self.query_bookmarks.get_by_connection(self.connection_id)
            for bookmark in bookmarks:
                tags_str = f" [{', '.join(bookmark.tags)}]" if bookmark.tags else ""
                preview = bookmark.query[:50].replace("\n", " ")
                option_text = f"📌 {bookmark.name}{tags_str}\n   {preview}..."
                history_list.add_option(Option(option_text, id=f"bm_{bookmark.id}"))

            if not bookmarks:
                history_list.add_option(Option("(No bookmarks)", disabled=True))
        else:
            # Show history
            entries = self.query_history.get_recent(limit=50)
            for entry in entries:
                timestamp = datetime.fromisoformat(entry.timestamp).strftime("%H:%M:%S")
                preview = entry.query[:50].replace("\n", " ")
                status_icon = "✓" if entry.status == "success" else "✗"
                option_text = f"{status_icon} {timestamp} - {preview}..."
                history_list.add_option(Option(option_text, id=f"hist_{entry.id}"))

            if not entries:
                history_list.add_option(Option("(No history)", disabled=True))

    def action_toggle_history_panel(self) -> None:
        """Toggle the history/bookmarks panel visibility."""
        self._history_visible = not self._history_visible
        history_panel = self.query_one("#history-panel")

        if self._history_visible:
            history_panel.styles.display = "block"
            self._refresh_history_list()
            self.notify("History panel opened (F4 to close)", severity="information")
        else:
            history_panel.styles.display = "none"
            self.notify("History panel closed", severity="information")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle selection from history/bookmarks list."""
        option_id = str(event.option.id)

        if option_id.startswith("bm_"):
            # Bookmark selected
            bookmark_id = option_id[3:]  # Remove "bm_" prefix
            self.action_load_from_bookmark(bookmark_id)
        elif option_id.startswith("hist_"):
            # History entry selected
            entry_id = option_id[5:]  # Remove "hist_" prefix
            entries = self.query_history.get_recent(limit=200)
            entry = next((e for e in entries if e.id == entry_id), None)

            if entry:
                sql_editor = self.query_one("#sql-editor", VimTextArea)
                sql_editor.text = entry.query
                self.notify(f"Loaded query from history", severity="information")
                logger.info(f"Loaded history entry {entry_id} into editor")
