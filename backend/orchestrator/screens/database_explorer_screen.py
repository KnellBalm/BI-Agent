"""
DatabaseExplorerScreen Module
Provides a 3-pane layout for exploring database schemas, writing SQL, and viewing results.
Inspired by sqlit interaction model.
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.widgets import Label, Input, Button, Tree, DataTable, TextArea, Static
from textual.screen import Screen
from textual.binding import Binding

from ..components.vim_engine import VimEngine, VimMode
from ..services.text2sql.factory import Text2SQLServiceFactory
from ..services.text2sql.base import BaseText2SQLService
from ..config.explorer_config import get_config
from backend.agents.data_source.metadata_scanner import MetadataScanner
from backend.orchestrator.managers.connection_manager import ConnectionManager
from backend.agents.data_source.connection_manager import ConnectionManager as AgentConnectionManager

logger = logging.getLogger("tui")

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
        Binding("r", "run_query", "Run [R]"),
        Binding("ctrl+s", "save_query", "Save"),
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
    #main-panel {
        width: 1fr;
        height: 1fr;
    }
    #editor-panel {
        height: 15;
        border: tall $panel;
        background: $surface;
    }
    #results-panel {
        height: 1fr;
        border: tall $panel;
        background: $surface;
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
        self.initial_query = initial_query or "SELECT * FROM tables LIMIT 10;"

        # Load configuration
        self.config = get_config()

        # Set AI mode (use provided or default from config)
        self.ai_mode = mode or self.config.text2sql.default_mode
        self.api_provider = provider or self.config.text2sql.default_api_provider

        # Initialize Text2SQL service
        self.text2sql_service: Optional[BaseText2SQLService] = None
        self._initialize_text2sql_service()

    def compose(self) -> ComposeResult:
        # Mode indicator at the top
        yield Label(self._get_mode_indicator_text(), id="mode-indicator")

        with Horizontal(id="explorer-layout"):
            # Left Pane: Schema Tree
            with Vertical(id="tree-panel", classes="border-hint"):
                yield Label(" STRUCTURE [F1] ", classes="panel-title")
                yield Tree("Database", id="schema-tree")

            # Middle/Right Pane: Editor & Results
            with Vertical(id="main-panel"):
                with Vertical(id="editor-panel", classes="border-hint"):
                    yield Label(" SQL EDITOR [F2] ", classes="panel-title")
                    yield VimTextArea(id="sql-editor", text=self.initial_query)

                with Vertical(id="results-panel", classes="border-hint"):
                    yield Label(" RESULTS [F3] ", classes="panel-title")
                    yield DataTable(id="results-grid")

    def on_mount(self) -> None:
        self.query_one("#schema-tree").focus()

        # Set border titles as hints
        self.query_one("#tree-panel").border_title = "Explorer"
        self.query_one("#editor-panel").border_title = "Query"
        self.query_one("#results-panel").border_title = "Data Grid"

        # Load schema asynchronously with loading indicator
        asyncio.create_task(self._load_schema())

    async def _load_schema(self):
        """Loads tables/views from the connection manager asynchronously."""
        tree = self.query_one("#schema-tree")

        # Show loading indicator
        loading_node = tree.root.add("📡 Loading schema...", expand=True)
        loading_node.add_leaf("Please wait...")

        try:
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

            # TODO: Add views separately if available in metadata
            # For now, views are not separately identified by MetadataScanner

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
        query = self.query_one("#sql-editor").text
        self.notify(f"Running query: {query[:30]}...")
        # Placeholder for actual execution
        self._update_results([{"id": 1, "name": "Dummy"}])

    def _update_results(self, data: List[Dict[str, Any]]):
        grid = self.query_one("#results-grid", DataTable)
        grid.clear(columns=True)
        if not data: return
        
        cols = list(data[0].keys())
        grid.add_columns(*cols)
        for row in data:
            grid.add_row(*[row[c] for c in cols])

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
